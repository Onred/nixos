{ pkgs, unstable, username, ... }:

{
  users.users.${username}.packages = with pkgs; [
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
    pciutils
    python3
    sbctl
    sqlite
    tree
    usbutils
    wget
  ];
}
