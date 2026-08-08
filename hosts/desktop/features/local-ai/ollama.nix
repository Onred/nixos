{ pkgs, username, ... }:

let
  openWebUiDesktop = pkgs.makeDesktopItem {
    name = "open-webui";
    desktopName = "Open WebUI";
    genericName = "Local AI Chat";
    comment = "Chat with local Ollama models";
    exec = "${pkgs.xdg-utils}/bin/xdg-open http://127.0.0.1:8080";
    icon = "${pkgs.open-webui}/${pkgs.python3.sitePackages}/open_webui/static/favicon.svg";
    categories = [ "Network" "Utility" ];
  };
in

{
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

  services.open-webui = {
    enable = true;
    host = "127.0.0.1";
    port = 8080;
    environment = {
      ENABLE_OPENAI_API = "False";
      OLLAMA_BASE_URL = "http://127.0.0.1:11434";
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
    "L+ /home/${username}/.qwen/settings.json - ${username} users - /run/current-system/etc/local-ai/qwen-settings.json"
  ];
}
