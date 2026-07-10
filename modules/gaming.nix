{ pkgs, username, ... }:

{
  programs.steam.enable = true;
  programs.steam.extraPackages = with pkgs; [ kdePackages.breeze ];

  users.users.${username}.packages = with pkgs; [
    protonplus
  ];
}
