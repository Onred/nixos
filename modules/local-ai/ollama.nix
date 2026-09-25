{
  config,
  lib,
  pkgs,
  username,
  ...
}:

let
  gemmaModelfile = pkgs.writeText "gemma4-modelfile" ''
    FROM gemma4:12b-it-qat
    PARAMETER num_ctx 16384
  '';
  qwenModelfile = pkgs.writeText "qwen3.8-modelfile" ''
    FROM qwen3.8:27b
    PARAMETER num_ctx 65536
  '';

  openWebUiDesktop = pkgs.makeDesktopItem {
    name = "open-webui";
    desktopName = "Open WebUI";
    genericName = "Local AI Chat";
    comment = "Chat with local Ollama models";
    exec = "${pkgs.xdg-utils}/bin/xdg-open http://127.0.0.1:8081";
    icon = "${pkgs.open-webui}/${pkgs.python3.sitePackages}/open_webui/static/favicon.svg";
    categories = [
      "Network"
      "Utility"
    ];
  };
in

{
  services.ollama = {
    enable = true;
    package = pkgs.ollama-cuda;
    loadModels = [
      "gemma4:12b-it-qat"
      "qwen3.8:27b"
    ];
    syncModels = true;
    environmentVariables = {
      OLLAMA_CONTEXT_LENGTH = "16384";
      OLLAMA_FLASH_ATTENTION = "1";
      OLLAMA_KV_CACHE_TYPE = "q8_0";
      OLLAMA_MAX_LOADED_MODELS = "1";
      OLLAMA_NUM_PARALLEL = "1";
    };
  };

  # OpenAI-compatible clients cannot set Ollama's context size. Reapply it after pulls.
  systemd.services.ollama-model-loader.script = lib.mkAfter ''
    ${lib.getExe config.services.ollama.package} create gemma4:12b-it-qat -f ${gemmaModelfile}
    ${lib.getExe config.services.ollama.package} create qwen3.8:27b -f ${qwenModelfile}
  '';

  services.open-webui = {
    enable = true;
    host = "127.0.0.1";
    port = 8081;
    environment = {
      ENABLE_OPENAI_API = "False";
      OLLAMA_BASE_URL = "http://127.0.0.1:11434";
      DEFAULT_MODELS = "gemma4:12b-it-qat";
    };
  };

  systemd.services.open-webui = {
    wants = [ "ollama.service" ];
    after = [ "ollama.service" ];
  };

  users.users.${username}.packages = [
    openWebUiDesktop
    pkgs.qwen-code
  ];

  environment.sessionVariables.OLLAMA_API_KEY = "ollama";

  environment.persistence."/persist".directories = [
    "/var/lib/private/ollama"
    "/var/lib/private/open-webui"
  ];

  environment.etc."local-ai/qwen-settings.json".text = builtins.toJSON {
    modelProviders.openai = [
      {
        id = "gemma4:12b-it-qat";
        name = "Gemma 4 12B QAT (local, 16K)";
        baseUrl = "http://127.0.0.1:11434/v1";
        envKey = "OLLAMA_API_KEY";
        generationConfig.contextWindowSize = 16384;
      }
      {
        id = "qwen3.8:27b";
        name = "Qwen3.8 27B (local, 64K)";
        baseUrl = "http://127.0.0.1:11434/v1";
        envKey = "OLLAMA_API_KEY";
        generationConfig.contextWindowSize = 65536;
      }
    ];
    privacy.usageStatisticsEnabled = false;
    telemetry.enabled = false;
    security.auth.selectedType = "openai";
    model.name = "gemma4:12b-it-qat";
  };

  systemd.tmpfiles.rules = [
    "d /home/${username}/.qwen 0700 ${username} users -"
    "L+ /home/${username}/.qwen/settings.json - ${username} users - /run/current-system/etc/local-ai/qwen-settings.json"
  ];
}
