{ pkgs, username, ... }:

let
  continueConfig = pkgs.writeText "continue.yaml" ''
    name: Local coding
    version: 1.0.0
    schema: v1

    rules:
      - Use only available tools, with exact JSON schemas. Do not invent tools.
      - For read_file, use filepath, not path.
      - For current or version-specific facts, use local_web_search first, then fetch_web_page. Prefer official docs and cite URLs.
      - Do not use search_web; use local_web_search instead.
      - Never include branch names in Git commit messages.
      - Prefer local/free solutions over cloud APIs.

    mcpServers:
      - name: Local web search
        command: /run/current-system/sw/bin/local-web-search

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
in
{
  environment.etc."local-ai/continue.yaml".source = continueConfig;

  systemd.tmpfiles.rules = [
    "d /home/${username}/.continue 0755 ${username} users -"
    "L+ /home/${username}/.continue/config.yaml - ${username} users - ${continueConfig}"
  ];
}
