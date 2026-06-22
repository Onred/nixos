{ pkgs, username, ... }:

{
  services.ollama = {
    enable = true;
    package = pkgs.ollama-cuda;
    loadModels = [
      "qwen3.6:27b"
      "qwen2.5-coder:1.5b-base"
    ];
    syncModels = true;
    environmentVariables = {
      OLLAMA_CONTEXT_LENGTH = "65536";
      OLLAMA_FLASH_ATTENTION = "1";
      OLLAMA_KV_CACHE_TYPE = "q8_0";
      OLLAMA_MAX_LOADED_MODELS = "2";
      OLLAMA_NUM_PARALLEL = "1";
    };
  };

  users.users.${username}.packages = [ pkgs.qwen-code ];

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

  environment.etc."local-ai/continue.yaml".text = ''
    name: Local coding
    version: 1.0.0
    schema: v1

    models:
      - name: Qwen3.6 27B
        provider: ollama
        model: qwen3.6:27b
        roles:
          - chat
          - edit
          - apply
        capabilities:
          - tool_use
          - image_input
        defaultCompletionOptions:
          contextLength: 65536
          maxTokens: 8192
          temperature: 0.6
          topP: 0.95
          topK: 20
          reasoning: true
          keepAlive: 1800

      - name: Qwen2.5 Coder 1.5B
        provider: ollama
        model: qwen2.5-coder:1.5b-base
        roles:
          - autocomplete
        defaultCompletionOptions:
          contextLength: 4096
          maxTokens: 256
          temperature: 0.1
          keepAlive: 1800
        autocompleteOptions:
          debounceDelay: 250
          maxPromptTokens: 2048
          onlyMyCode: true
          useCache: true
          useImports: true
          useRecentlyEdited: true
          useRecentlyOpened: true
  '';

  systemd.tmpfiles.rules = [
    "d /home/${username}/.continue 0755 ${username} users -"
    "L+ /home/${username}/.continue/config.yaml - ${username} users - /etc/local-ai/continue.yaml"
    "d /home/${username}/.qwen 0700 ${username} users -"
    "L+ /home/${username}/.qwen/settings.json - ${username} users - /etc/local-ai/qwen-settings.json"
  ];
}
