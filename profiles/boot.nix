{ lib, unstable, ... }:

{
  boot.loader.limine = {
    enable = true;
    secureBoot.enable = true;
    resolution = lib.mkDefault "2560x1440";
    style = {
      graphicalTerminal.background = lib.mkDefault "ff000000";
      wallpapers = lib.mkOverride 900 [ ../wallpapers/limine.png ];
    };
  };

  boot.loader.efi.canTouchEfiVariables = true;
  boot.kernelPackages = unstable.linuxPackages_latest;
}
