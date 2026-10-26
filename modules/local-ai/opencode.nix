{ pkgs, username, ... }:

let
  models = import ./models.nix;
in
{
  users.users.${username}.packages = [
    pkgs.opencode
    pkgs.nodejs
  ];

  environment.sessionVariables.OPENCODE_CONFIG = "/etc/opencode/local.json";

  environment.etc."opencode/local.json".text = builtins.toJSON {
    "$schema" = "https://opencode.ai/config.json";
    model = "strata/qwen-flash";
    small_model = "strata/qwen-flash";
    autoupdate = false;
    share = "disabled";
    provider.strata = {
      npm = "@ai-sdk/openai-compatible";
      name = "Strata (local)";
      options = {
        baseURL = "http://127.0.0.1:8082/v1";
        apiKey = "strata-local-only";
        timeout = 7300000;
      };
      models.qwen-flash = {
        name = models.qwen.displayName;
        tool_call = true;
        reasoning = true;
        limit = {
          context = models.qwen.context;
          input = models.qwen.context - models.qwen.output;
          output = models.qwen.output;
        };
      };
    };
    mcp.brave = {
      type = "local";
      command = [
        "${pkgs.nodejs}/bin/npx"
        "--yes"
        "@brave/brave-search-mcp-server@latest"
        "--transport"
        "stdio"
      ];
      environment.BRAVE_API_KEY_FILE = "/home/${username}/.config/opencode/brave-api-key";
      timeout = 120000;
      enabled = true;
    };
  };
}
