{ pkgs, unstable, username, ... }:

{
  programs.nix-ld.enable = true;

  users.users.${username}.packages = with pkgs; [
    btop
    unstable.codex
    fastfetch
    neovim
  ];

  environment.systemPackages = with pkgs; [
    git
    gh
    jq
    nh
    pciutils
    sbctl
    tree
    usbutils
    wget
    vim
  ];
}
