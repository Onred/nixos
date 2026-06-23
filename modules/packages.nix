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
    (vscode.fhsWithPackages (packages: [ packages.stdenv.cc.cc ]))

    # Command line
    btop
    fastfetch
  ];

  environment.systemPackages = with pkgs; [
    git
    jq
    nh
    python3
    sbctl
    tree
    wget
  ];
}
