{ lib, modulesPath, ... }:

{
  imports = [
    ./hardware-configuration.nix
    (modulesPath + "/profiles/qemu-guest.nix")
    ../../profiles/base.nix
    ../../profiles/boot.nix
    ../../profiles/desktop-environment.nix
    ../../profiles/desktop-apps.nix
    ../../profiles/development.nix
    ../../modules/storage
  ];

  boot.loader.limine.resolution = lib.mkForce null;
  boot.loader.limine.style.wallpapers = lib.mkForce [ ];
}
