{
  config,
  lib,
  pkgs,
  username,
  ...
}:

let
  # Backport the web-only upstream adapter without changing the pinned nixpkgs.
  googleCseEngine = pkgs.fetchurl {
    url = "https://raw.githubusercontent.com/searxng/searxng/1cdf01a71916e67352eb7e6d60ddfdeb62f5f1a2/searx/engines/google_cse.py";
    hash = "sha256-/6G1Hj7VsP8HvCfldOGV+sx7PtFF4fCEgceoZxCDdYo=";
  };
  searchPackage = pkgs.searxng.overrideAttrs (old: {
    postPatch = (old.postPatch or "") + ''
      cp ${googleCseEngine} searx/engines/google_cse.py
      ${pkgs.python3.interpreter} - <<'PYTHON'
      import json
      from pathlib import Path
      path = Path("searx/data/engine_traits.json")
      traits = json.loads(path.read_text())
      traits["google cse"] = traits["google"]
      path.write_text(json.dumps(traits))
      PYTHON
    '';
  });
  python = pkgs.python3.withPackages (p: [
    p.httpx
    p.mcp
    p.playwright
    p.tomlkit
    p.trafilatura
  ]);
  localModelTools = pkgs.writeShellApplication {
    name = "local-model-tools";
    runtimeInputs = [ python pkgs.ripgrep ];
    text = ''
      export LOCAL_GEMMA_BROWSER=${pkgs.chromium}/bin/chromium
      exec python ${../../scripts/local-ai/runtime}/server.py "''$@"
    '';
  };
  runReport = pkgs.writeShellApplication {
    name = "local-run-report";
    runtimeInputs = [ python ];
    text = ''
      exec python ${../../scripts/local-ai/runtime}/run_report.py "''$@"
    '';
  };
  codexConfig = (pkgs.formats.toml { }).generate "local-gemma-codex.toml" {
    mcp_servers.local_gemma = {
      command = "${localModelTools}/bin/local-model-tools";
      args = [
        "--allow-root"
        "/home/${username}/nixos"
        "--allow-root"
        "/home/${username}/Projects"
      ];
      startup_timeout_sec = 20;
      tool_timeout_sec = 180;
      enabled_tools = [
        "search_web"
        "read_web"
        "extract_evidence"
        "inspect_run"
        "validation_report"
        "filter_log"
        "search_repository"
        "compare_reports"
        "read_artifact"
      ];
    };
  };
in
{
  environment.systemPackages = [ localModelTools runReport ];

  services.searx = {
    enable = true;
    package = searchPackage;
    settings = {
      use_default_settings.engines.keep_only = [
        "mwmbl"
        "wikipedia"
      ];
      general.debug = false;
      engines = [
        {
          name = "google cse";
          engine = "google_cse";
          shortcut = "gc";
          disabled = false;
        }
        {
          name = "mwmbl";
          disabled = true;
        }
        {
          name = "wikipedia";
          disabled = true;
          display_type = [ "list" ];
        }
      ];
      server = {
        bind_address = "127.0.0.1";
        port = 8888;
        secret_key = "$SEARX_SECRET_KEY";
        limiter = false;
        image_proxy = false;
      };
      search.formats = [
        "json"
        "html"
      ];
      outgoing.request_timeout = 8.0;
    };
  };

  # The local-only search service needs no persistent cookie secret.
  systemd.services.searx-init.script = lib.mkBefore ''
    export SEARX_SECRET_KEY="''$(${pkgs.openssl}/bin/openssl rand -hex 32)"
  '';
  systemd.services.searx = {
    restartTriggers = [
      (pkgs.writeText "local-gemma-search-settings" (builtins.toJSON config.services.searx.settings))
    ];
    serviceConfig.Restart = "on-failure";
  };

  systemd.services.local-gemma-codex-setup = {
    description = "Register Gemma evidence tools and guidance with Codex";
    wantedBy = [ "multi-user.target" ];
    after = [ "local-fs.target" ];
    unitConfig.RequiresMountsFor = "/home/${username}";
    restartTriggers = [
      codexConfig
      ../../scripts/local-ai/codex-guidance.md
      ../../scripts/local-ai/register_codex.py
    ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      User = username;
      UMask = "0077";
      ExecStart = "${python}/bin/python ${../../scripts/local-ai/register_codex.py} --directory /home/${username}/.codex --config ${codexConfig} --guidance ${../../scripts/local-ai/codex-guidance.md}";
    };
  };
}
