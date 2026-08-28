#!/usr/bin/env node

import {
  existsSync,
  mkdirSync,
  readFileSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";

const desktopAppId = 413080;
const xboxEliteType = 46;
const emptyLayout = "local://controller_base/empty.vdf";
const defaultLayout = "local://controller_base/desktop_xboxone.vdf";
const port = Number.parseInt(
  process.env.STEAM_CONTROLLER_CDP_PORT ?? "8080",
  10,
);
const stateDirectory = join(
  process.env.XDG_STATE_HOME ?? join(process.env.HOME, ".local", "state"),
  "steam-desktop-input",
);
const stateFile = join(stateDirectory, "desktop-layout.json");

function usage(exitCode = 0) {
  const output = exitCode === 0 ? process.stdout : process.stderr;
  output.write("Usage: steam-desktop-input {off|on|toggle|status}\n");
  process.exit(exitCode);
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

class SteamCdp {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();

    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      const pending = this.pending.get(message.id);
      if (!pending) return;

      clearTimeout(pending.timer);
      this.pending.delete(message.id);
      if (message.error) pending.reject(new Error(message.error.message));
      else pending.resolve(message.result);
    });
  }

  static async connect() {
    let pages;
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json`, {
        signal: AbortSignal.timeout(3000),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      pages = await response.json();
    } catch (error) {
      throw new Error(
        `Cannot reach Steam's local controller API on port ${port}: ${error.message}. ` +
          "Apply the NixOS configuration, then fully restart Steam.",
      );
    }

    const page = Array.isArray(pages)
      ? pages.find((candidate) => candidate.title === "SharedJSContext")
      : null;
    if (!page?.webSocketDebuggerUrl) {
      throw new Error("Steam's SharedJSContext debugging page was not found");
    }

    const socket = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error("Timed out connecting to Steam's controller API")),
        5000,
      );
      socket.addEventListener(
        "open",
        () => {
          clearTimeout(timer);
          resolve();
        },
        { once: true },
      );
      socket.addEventListener(
        "error",
        () => {
          clearTimeout(timer);
          reject(new Error("Failed to connect to Steam's controller API"));
        },
        { once: true },
      );
    });
    return new SteamCdp(socket);
  }

  request(method, params) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Steam API request timed out: ${method}`));
      }, 7000);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const response = await this.request("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
      userGesture: true,
    });
    if (response.exceptionDetails) {
      const detail =
        response.exceptionDetails.exception?.description ??
        response.exceptionDetails.text;
      throw new Error(`Steam controller API failed: ${detail}`);
    }
    return response.result?.value;
  }

  close() {
    this.socket.close();
  }
}

async function getControllers(client) {
  const expression = `Promise.all(Array.from({ length: 16 }, async (_, index) => {
    try {
      const config = await SteamClient.Input.GetConfigForAppAndController(
        ${desktopAppId}, index
      );
      if (!config?.bConfigurationEnabled) return null;
      return {
        index: config.unControllerIndex,
        type: config.nControllerType,
        url: config.URL || "",
        title: config.Title || "",
        usesGamepad: Boolean(config.bUsesGamepad),
        usesKeyboard: Boolean(config.bUsesKeyboard),
        usesMouse: Boolean(config.bUsesMouse),
      };
    } catch (_) {
      return null;
    }
  }))`;
  const controllers = (await client.evaluate(expression)) ?? [];
  return controllers.filter((controller) => controller?.type === xboxEliteType);
}

async function selectLayout(client, controller, url, controllerCount) {
  const saveAsTypeDefault = controllerCount === 1;
  await client.evaluate(`Promise.resolve(
    SteamClient.Input.SetSelectedConfigForApp(
      ${desktopAppId},
      ${Number(controller.index)},
      ${JSON.stringify(url)},
      false,
      ${saveAsTypeDefault}
    )
  ).then(() => true)`);
}

function readState() {
  if (!existsSync(stateFile)) return null;
  const state = JSON.parse(readFileSync(stateFile, "utf8"));
  if (state.version !== 1 || !Array.isArray(state.controllers)) {
    throw new Error(`Unsupported state in ${stateFile}`);
  }
  return state;
}

function saveState(controllers) {
  mkdirSync(stateDirectory, { recursive: true, mode: 0o700 });
  writeFileSync(
    stateFile,
    `${JSON.stringify({ version: 1, controllers }, null, 2)}\n`,
    { encoding: "utf8", flag: "wx", mode: 0o600 },
  );
}

function requireController(controllers) {
  if (controllers.length === 0) {
    throw new Error(
      "No connected Xbox Elite controller (Steam controller type 46) was found",
    );
  }
}

async function turnOff(client) {
  const controllers = await getControllers(client);
  requireController(controllers);
  if (controllers.every((controller) => controller.url === emptyLayout)) {
    process.stdout.write("Steam desktop input is already off.\n");
    return;
  }

  if (!existsSync(stateFile)) {
    saveState(
      controllers.map(({ index, type, url }) => ({
        index,
        type,
        url: url || defaultLayout,
      })),
    );
  }
  for (const controller of controllers) {
    await selectLayout(client, controller, emptyLayout, controllers.length);
  }
  await sleep(400);
  const updated = await getControllers(client);
  const failed = updated.filter((controller) => controller.url !== emptyLayout);
  if (failed.length > 0 || updated.length !== controllers.length) {
    throw new Error("Steam did not activate the empty desktop layout");
  }
  process.stdout.write("Steam desktop input is off.\n");
}

async function turnOn(client) {
  const controllers = await getControllers(client);
  requireController(controllers);
  const state = readState();
  if (
    !state &&
    controllers.every((controller) => controller.url !== emptyLayout)
  ) {
    process.stdout.write("Steam desktop input is already on.\n");
    return;
  }
  const expected = new Map();

  for (const [position, controller] of controllers.entries()) {
    const saved =
      state?.controllers.find((entry) => entry.index === controller.index) ??
      state?.controllers[position];
    const target = saved?.url || defaultLayout;
    if (controller.url === emptyLayout || state) {
      await selectLayout(client, controller, target, controllers.length);
      expected.set(controller.index, target);
    }
  }
  await sleep(400);
  const updated = await getControllers(client);
  const failed = updated.filter(
    (controller) =>
      expected.has(controller.index) &&
      controller.url !== expected.get(controller.index),
  );
  if (failed.length > 0 || updated.length !== controllers.length) {
    const recovery = state ? `; recovery state remains at ${stateFile}` : "";
    throw new Error(`Steam did not restore the desktop layout${recovery}`);
  }
  if (state) unlinkSync(stateFile);
  process.stdout.write("Steam desktop input is on.\n");
}

async function status(client) {
  const controllers = await getControllers(client);
  requireController(controllers);
  process.stdout.write(`Saved layout: ${existsSync(stateFile) ? stateFile : "none"}\n`);
  for (const controller of controllers) {
    process.stdout.write(
      `Controller slot ${controller.index}: ${controller.title || "Xbox Elite"}\n` +
        `  desktop config: ${controller.url || "(none)"}\n` +
        `  outputs: gamepad=${controller.usesGamepad} ` +
        `keyboard=${controller.usesKeyboard} mouse=${controller.usesMouse}\n`,
    );
  }
}

const command = process.argv[2];
if (!["off", "on", "toggle", "status"].includes(command)) usage(1);

let client;
try {
  client = await SteamCdp.connect();
  if (command === "off") await turnOff(client);
  else if (command === "on") await turnOn(client);
  else if (command === "status") await status(client);
  else {
    const controllers = await getControllers(client);
    requireController(controllers);
    if (controllers.every((controller) => controller.url === emptyLayout)) {
      await turnOn(client);
    } else {
      await turnOff(client);
    }
  }
} catch (error) {
  process.stderr.write(`steam-desktop-input: ${error.message}\n`);
  process.exitCode = 1;
} finally {
  client?.close();
}
