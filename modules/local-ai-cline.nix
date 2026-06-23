{ pkgs, username, ... }:

let
  clineMcpSettings = pkgs.writeText "cline_mcp_settings.json" (builtins.toJSON {
    mcpServers.local-web-search = {
      command = "/run/current-system/sw/bin/local-web-search";
      args = [ ];
      disabled = false;
      autoApprove = [
        "local_web_search"
        "fetch_web_page"
      ];
    };
  });

  clineRules = pkgs.writeText "local-ai.md" ''
    # Local AI

    - Prefer local/free tools over cloud APIs.
    - For current or version-specific facts, use local_web_search first, then fetch_web_page. Prefer official docs and cite URLs.
    - If fetch_web_page returns little useful text, do not retry the same URL; try another result.
    - Never include branch names in Git commit messages.
  '';
in
{
  environment.etc."local-ai/cline-mcp-settings.json".source = clineMcpSettings;
  environment.etc."local-ai/cline-rules/local-ai.md".source = clineRules;

  systemd.tmpfiles.rules = [
    "d /home/${username}/.cline 0700 ${username} users -"
    "d /home/${username}/.cline/data 0700 ${username} users -"
    "d /home/${username}/.cline/data/settings 0700 ${username} users -"
    "d /home/${username}/.cline/rules 0700 ${username} users -"
    "L+ /home/${username}/.cline/data/settings/cline_mcp_settings.json - ${username} users - /run/current-system/etc/local-ai/cline-mcp-settings.json"
    "L+ /home/${username}/.cline/rules/local-ai.md - ${username} users - /run/current-system/etc/local-ai/cline-rules/local-ai.md"
    "d /home/${username}/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings 0700 ${username} users -"
    "L+ /home/${username}/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json - ${username} users - /run/current-system/etc/local-ai/cline-mcp-settings.json"
  ];
}
