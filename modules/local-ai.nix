{ pkgs, username, ... }:

let
  localWebSearch =
    let
      python = pkgs.python3.withPackages (pythonPackages: [ pythonPackages.mcp ]);
      server = ./local-ai-web-search.py;
    in
    pkgs.writeShellScriptBin "local-web-search" ''
      exec ${python}/bin/python ${server}
    '';
in
{
  services.searx = {
    enable = true;
    settings = {
      server = {
        bind_address = "127.0.0.1";
        port = 8080;
        secret_key = "local-only";
      };
      search.formats = [
        "html"
        "json"
      ];
    };
  };

  services.ollama = {
    enable = true;
    package = pkgs.ollama-cuda;
    loadModels = [
      "qwen3.6:27b"
      "qwen3.5:27b"
      "qwen2.5-coder:1.5b-base"
    ];
    syncModels = true;
    environmentVariables = {
      OLLAMA_CONTEXT_LENGTH = "65536";
      OLLAMA_FLASH_ATTENTION = "1";
      OLLAMA_KV_CACHE_TYPE = "q8_0";
      OLLAMA_MAX_LOADED_MODELS = "3";
      OLLAMA_NUM_PARALLEL = "1";
    };
  };

  users.users.${username}.packages = [ pkgs.qwen-code ];

  environment.systemPackages = [ localWebSearch ];

  environment.sessionVariables.OLLAMA_API_KEY = "ollama";

  environment.etc."local-ai/qwen-settings.json".text = builtins.toJSON {
    modelProviders.openai = [
      {
        id = "qwen3.6:27b";
        name = "Qwen3.6 27B (local)";
        baseUrl = "http://127.0.0.1:11434/v1";
        envKey = "OLLAMA_API_KEY";
        generationConfig = {
          contextWindowSize = 65536;
          samplingParams = {
            temperature = 0.6;
            top_p = 0.95;
            presence_penalty = 0.0;
          };
        };
      }
    ];
    privacy.usageStatisticsEnabled = false;
    telemetry.enabled = false;
    security.auth.selectedType = "openai";
    model.name = "qwen3.6:27b";
  };

  systemd.tmpfiles.rules = [
    "d /home/${username}/.qwen 0700 ${username} users -"
    "L+ /home/${username}/.qwen/settings.json - ${username} users - /etc/local-ai/qwen-settings.json"
  ];
}
