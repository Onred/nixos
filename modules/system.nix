{
  fullName,
  hostName,
  lib,
  unstable,
  username,
  ...
}:

{
  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];
  nixpkgs.config.allowUnfree = true;

  networking.hostName = hostName;
  networking.networkmanager.enable = true;

  hardware.bluetooth.enable = true;
  hardware.graphics.enable = true;

  time.timeZone = "Asia/Tokyo";
  i18n.defaultLocale = "en_US.UTF-8";

  users.mutableUsers = false;
  users.users.${username} = {
    isNormalUser = true;
    description = fullName;
    hashedPasswordFile = lib.mkDefault "/persist/secrets/${username}-password-hash";
    extraGroups = [
      "networkmanager"
      "wheel"
    ];
  };

  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };

  services.printing.enable = true;

  environment.persistence."/persist".directories = [
    "/var/lib/AccountsService"
    "/var/lib/fwupd"
  ];

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

  system.stateVersion = "26.05";
}
