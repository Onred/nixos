{ pkgs, username, ... }:

{
  programs.firefox.enable = true;

  users.users.${username}.packages = with pkgs; [
    alacritty
    discord
    neovim
    pavucontrol
    (vscode.fhsWithPackages (packages: [ packages.stdenv.cc.cc ]))
    zed-editor
  ];
}
