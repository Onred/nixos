{ pkgs, unstable, username, ... }:

{
  users.users.${username}.packages = with pkgs; [
    btop
    unstable.codex
    fastfetch
    nodejs
    neovim
  ];

  environment.systemPackages = with pkgs; [
    acpica-tools
    binutils
    bubblewrap
    git
    jq
    nh
    pciutils
    python3
    sbctl
    sqlite
    tree
    usbutils
    wget
    vim
  ];
}
