{ pkgs, username, ... }:

{
  programs.firefox.enable = true;
  programs.steam.enable = true;

  users.users.${username}.packages = with pkgs; [
    # Desktop
    alacritty
    discord
    neovim
    pavucontrol
    protonup-qt
    vscode

    # Command line
    btop
    fastfetch
  ];

  environment.systemPackages = with pkgs; [
    git
    nh
    sbctl
    tree
    wget
  ];
}
