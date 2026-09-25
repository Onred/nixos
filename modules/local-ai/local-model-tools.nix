{
  config,
  lib,
  pkgs,
  username,
  ...
}:

let
  python = pkgs.python3.withPackages (p: [
    p.httpx
    p.mcp
    p.playwright
    p.tomlkit
    p.trafilatura
  ]);
  localModelTools = pkgs.writeShellApplication {
    name = "local-model-tools";
    runtimeInputs = [ python ];
    text = ''
      export LOCAL_GEMMA_BROWSER=${pkgs.chromium}/bin/chromium
      exec python ${../../scripts/local-ai/model_tools.py} "''$@"
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
      ];
    };
  };
in
{
  environment.systemPackages = [ localModelTools ];

  services.searx = {
    enable = true;
    settings = {
      use_default_settings.engines.keep_only = [
        "duckduckgo"
        "bing"
        "brave"
        "wikipedia"
      ];
      general.debug = false;
      engines = [
        {
          name = "bing";
          disabled = false;
        }
        {
          name = "wikipedia";
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
