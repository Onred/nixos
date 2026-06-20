{ pkgs, username, ... }:

{
  imports = [
    ./modules/hardware-configuration.nix # Detected hardware facts
    ./modules/disk-config.nix # Disko partition and filesystem layout
    ./modules/extra-disks.nix # Optional additional disks
    ./modules/impermanence.nix # Ephemeral root and persistent state
    ./modules/nvidia.nix # NVIDIA graphics driver
    ./modules/packages.nix # System and user packages
  ];

  # Nix
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  nixpkgs.config.allowUnfree = true;

  # Boot
  boot.loader.limine = {
    enable = true;
    secureBoot.enable = true;
    resolution = "2560x1440";
    style = {
      graphicalTerminal.background = "ff000000";
      wallpapers = [ ./wallpapers/limine.png ];
    };
  };

  boot.loader.efi.canTouchEfiVariables = true;
  boot.kernelPackages = pkgs.linuxPackages_latest;

  # Networking
  networking.hostName = "nixos";
  networking.networkmanager.enable = true;

  # Locale
  time.timeZone = "Asia/Tokyo";
  i18n.defaultLocale = "en_US.UTF-8";

  # Graphics and desktop
  hardware.bluetooth.enable = true;
  hardware.graphics.enable = true;

  services.displayManager.sddm.enable = true;
  services.desktopManager.plasma6.enable = true;

  fonts.packages = with pkgs; [
    nerd-fonts.jetbrains-mono
  ];

  # Audio
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };

  # Printing
  services.printing.enable = true;

  # Users
  users.mutableUsers = false;
  users.users.${username} = {
    isNormalUser = true;
    description = "Onred";
    hashedPasswordFile = "/persist/secrets/${username}-password-hash";
    extraGroups = [ "networkmanager" "wheel" ];
  };

  # Compatibility
  system.stateVersion = "26.05";
}
