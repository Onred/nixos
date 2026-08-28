#!/usr/bin/env python3

import asyncio
import re
import signal
from pathlib import Path

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from dbus_next.service import ServiceInterface, method


BUS_NAME = "org.onred.SteamDesktopInput"
OBJECT_PATH = "/org/onred/SteamDesktopInput"
INTERFACE_NAME = "org.onred.SteamDesktopInput"
DESKTOP_APP_IDS = {0, 413080}
STEAM_DESKTOP_FILE = re.compile(r"steam_app_(\d+)")


def process_environment(pid):
    try:
        entries = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    except OSError:
        return {}

    environment = {}
    for entry in entries:
        key, separator, value = entry.partition(b"=")
        if separator:
            environment[key.decode(errors="replace")] = value.decode(
                errors="replace"
            )
    return environment


def parent_pid(pid):
    try:
        status = Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return 0

    for line in status.splitlines():
        if line.startswith("PPid:"):
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                return 0
    return 0


def steam_app_id(pid, desktop_file_name):
    desktop_file_name = desktop_file_name.rsplit("/", 1)[-1].removesuffix(".desktop")
    match = STEAM_DESKTOP_FILE.fullmatch(desktop_file_name)
    if match:
        app_id = int(match.group(1))
        if app_id not in DESKTOP_APP_IDS:
            return app_id

    seen = set()
    while pid > 1 and pid not in seen:
        seen.add(pid)
        environment = process_environment(pid)
        for name in ("SteamAppId", "SteamGameId"):
            value = environment.get(name, "")
            if value.isdecimal():
                app_id = int(value)
                if app_id not in DESKTOP_APP_IDS:
                    return app_id
        pid = parent_pid(pid)
    return None


class FocusWatcher:
    def __init__(self):
        self._changed = asyncio.Event()
        self._generation = 0
        self._pid = 0
        self._desktop_file_name = ""

    def set_focused_window(self, pid, desktop_file_name):
        self._pid = max(pid, 0)
        self._desktop_file_name = desktop_file_name
        self._generation += 1
        self._changed.set()

    async def apply(self, mode, pid, app_id):
        identity = f"Steam app {app_id}" if app_id is not None else "desktop"
        print(f"focus pid {pid}: {identity}; setting desktop input {mode}", flush=True)
        process = await asyncio.create_subprocess_exec("steam-desktop-input", mode)
        try:
            return_code = await asyncio.wait_for(process.wait(), timeout=20)
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise
        except TimeoutError:
            process.kill()
            await process.wait()
            print(f"steam-desktop-input {mode} timed out", flush=True)
            return
        if return_code != 0:
            print(
                f"steam-desktop-input {mode} exited with status {return_code}",
                flush=True,
            )

    async def run(self):
        while True:
            await self._changed.wait()

            while True:
                self._changed.clear()
                generation = self._generation
                pid = self._pid
                desktop_file_name = self._desktop_file_name
                app_id = steam_app_id(pid, desktop_file_name)
                mode = "off" if app_id is not None else "on"

                # Avoid profile flapping when a game briefly focuses a helper
                # window. Entering a game remains immediate.
                if mode == "on":
                    try:
                        await asyncio.wait_for(self._changed.wait(), timeout=0.1)
                        continue
                    except TimeoutError:
                        pass

                if generation != self._generation:
                    continue

                await self.apply(mode, pid, app_id)
                if generation == self._generation:
                    break


class FocusInterface(ServiceInterface):
    def __init__(self, watcher):
        super().__init__(INTERFACE_NAME)
        self._watcher = watcher

    @method()
    def SetFocusedWindow(self, pid: "i", desktop_file_name: "s"):
        self._watcher.set_focused_window(pid, desktop_file_name)


async def main():
    watcher = FocusWatcher()
    interface = FocusInterface(watcher)
    bus = await MessageBus(bus_type=BusType.SESSION).connect()
    bus.export(OBJECT_PATH, interface)
    await bus.request_name(BUS_NAME)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for watched_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(watched_signal, stop.set)

    worker = asyncio.create_task(watcher.run())
    stopped = asyncio.create_task(stop.wait())
    try:
        done, _ = await asyncio.wait(
            (worker, stopped), return_when=asyncio.FIRST_COMPLETED
        )
        if worker in done:
            worker.result()
    finally:
        worker.cancel()
        stopped.cancel()
        await asyncio.gather(worker, stopped, return_exceptions=True)
        bus.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
