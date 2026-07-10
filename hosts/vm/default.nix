{ lib, modulesPath, ... }:

{
  imports = [
    ./hardware-configuration.nix
    (modulesPath + "/profiles/qemu-guest.nix")
    ../../modules/base.nix
    ../../modules/boot.nix
    ../../modules/disko.nix
    ../../modules/impermanence.nix
    ../../modules/desktop-environment.nix
    ../../modules/desktop-apps.nix
    ../../modules/development.nix
  ];

  boot.loader.limine.resolution = lib.mkForce null;
  boot.loader.limine.style.wallpapers = lib.mkForce [ ];
}
