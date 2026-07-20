{ pkgs, unstable, username, ... }:

{
  programs.firefox.enable = true;

  users.users.${username}.packages = with pkgs; [
    alacritty
    discord
    pavucontrol
    (vscode.fhsWithPackages (packages: [ packages.stdenv.cc.cc ]))
    zed-editor
    libreoffice-qt6-fresh
    # unstable.bitwarden-desktop
  ];
}
