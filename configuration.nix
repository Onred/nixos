{ pkgs, unstable, username, ... }:

{
  imports = [
    ./modules/hardware-configuration.nix # Detected hardware facts
    ./modules/drives/drive-config.nix # Disko partition and filesystem layout
    ./modules/drives/extra-drives.nix # Optional additional drives
    ./modules/drives/impermanence.nix # Ephemeral root and persistent state
    ./modules/local-ai # Local coding models and shared web search
    ./modules/local-ai/cline.nix # Optional Cline editor integration
    ./modules/nvidia.nix # NVIDIA graphics driver
    ./modules/packages.nix # System and user packages
    ./modules/sunshine # Sunshine game streaming server
    ./modules/update-check.nix # Update notification service
    ./modules/flake-update.nix # Flake update and rebuild script
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
  boot.kernelModules = [ "uinput" ];

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

  services.udev.extraRules = ''
    KERNEL=="uinput", MODE="0660", GROUP="input", SYMLINK+="uinput"
  '';

  # Users
  users.mutableUsers = false;
  users.users.${username} = {
    isNormalUser = true;
    description = "Onred";
    hashedPasswordFile = "/persist/secrets/${username}-password-hash";
    extraGroups = [
      "input"
      "networkmanager"
      "wheel"
    ];
  };

  # Compatibility
  system.stateVersion = "26.05";
}
