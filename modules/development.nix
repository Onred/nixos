{ pkgs, unstable, username, ... }:

{
  users.users.${username}.packages = with pkgs; [
    btop
    unstable.codex
    fastfetch
    nodejs
    unstable.fetch
    neovim
  ];

  environment.systemPackages = with pkgs; [
    acpica-tools
    binutils
    bubblewrap
    git
    gh
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
