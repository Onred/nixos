{ pkgs, username, ... }:

{
  boot.kernelModules = [ "uinput" ];

  hardware.bluetooth.enable = true;
  hardware.graphics.enable = true;

  services.desktopManager.plasma6.enable = true;
  services.displayManager.plasma-login-manager.enable = true;

  fonts.packages = with pkgs; [
    nerd-fonts.jetbrains-mono
    inter
  ];

  fonts.fontconfig.defaultFonts.sansSerif = [
    "Inter"
    "Noto Sans"
  ];

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

  services.udev.extraRules = ''
    KERNEL=="uinput", MODE="0660", GROUP="input", SYMLINK+="uinput"
  '';

  users.users.${username}.extraGroups = [ "input" ];
}
