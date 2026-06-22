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

  continueConfig = pkgs.writeText "continue.yaml" ''
    name: Local coding
    version: 1.0.0
    schema: v1

    rules:
      - Use only the tools provided in the current request and follow each tool's JSON schema exactly.
      - The read_file tool requires the argument named filepath, never path. Never invent an exec tool.
      - For current or version-specific information, use local_web_search, then use fetch_web_page to read the most relevant results. Prefer official documentation and include source URLs. Do not use the credit-based search_web tool.

    mcpServers:
      - name: Local web search
        command: ${localWebSearch}/bin/local-web-search

    models:
      - name: Qwen3.6 27B
        provider: openai
        model: qwen3.6:27b
        apiBase: http://127.0.0.1:11434/v1
        apiKey: ollama
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
          presencePenalty: 0.0
          frequencyPenalty: 0.0
          reasoning: true
          keepAlive: 1800

      # - name: Qwen2.5 Coder 1.5B
      #   provider: ollama
      #   model: qwen2.5-coder:1.5b-base
      #   roles:
      #     - autocomplete
      #   defaultCompletionOptions:
      #     contextLength: 4096
      #     maxTokens: 256
      #     temperature: 0.1
      #     keepAlive: 1800
      #   autocompleteOptions:
      #     debounceDelay: 250
      #     maxPromptTokens: 2048
      #     onlyMyCode: true
      #     useCache: true
      #     useImports: true
      #     useRecentlyEdited: true
      #     useRecentlyOpened: true
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

  environment.etc."local-ai/continue.yaml".source = continueConfig;

  systemd.tmpfiles.rules = [
    "d /home/${username}/.continue 0755 ${username} users -"
    "L+ /home/${username}/.continue/config.yaml - ${username} users - ${continueConfig}"
    "d /home/${username}/.qwen 0700 ${username} users -"
    "L+ /home/${username}/.qwen/settings.json - ${username} users - /etc/local-ai/qwen-settings.json"
  ];
}
