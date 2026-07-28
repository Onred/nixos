{ pkgs, unstable, username, ... }:

{
  programs.firefox.enable = true;

  # Firefox 153 corrupts browser chrome on NVIDIA/Wayland.
  environment.sessionVariables.MOZ_ENABLE_WAYLAND = "0";

  users.users.${username}.packages = with pkgs; [
    alacritty
    discord
    pavucontrol
    (vscode.fhsWithPackages (packages: [ packages.stdenv.cc.cc ]))
    zed-editor
    libreoffice-qt6
    # unstable.bitwarden-desktop
  ];
}
