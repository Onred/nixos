{ pkgs, unstable, username, ... }:

{
  programs.firefox.enable = true;
  programs.steam.enable = true;
  programs.steam.extraPackages = with pkgs; [ kdePackages.breeze ];

  users.users.${username}.packages = with pkgs; [
    # Desktop
    alacritty
    discord
    neovim
    pavucontrol
    protonplus
    (vscode.fhsWithPackages (packages: [ packages.stdenv.cc.cc ]))
    zed-editor

    # Command line
    btop
    unstable.codex
    fastfetch
    nodejs
  ];

  environment.systemPackages = with pkgs; [
    acpica-tools
    binutils
    git
    jq
    nh
    python3
    sbctl
    sqlite
    tree
    pciutils
    usbutils
    wget
  ];
}
