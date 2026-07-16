{ pkgs, unstable, username, ... }:

{
  boot.kernelModules = [ "uinput" ];

  hardware.bluetooth.enable = true;
  hardware.graphics.enable = true;

  nixpkgs.overlays = [
    (_final: _prev: {
      kdePackages = unstable.kdePackages;
    })
  ];

  services.desktopManager.plasma6.enable = true;
  services.displayManager.plasma-login-manager.enable = true;

  fonts.packages = with pkgs; [
    nerd-fonts.jetbrains-mono
  ];

  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };

  services.printing.enable = true;

  services.udev.extraRules = ''
    KERNEL=="uinput", MODE="0660", GROUP="input", SYMLINK+="uinput"
  '';

  users.users.${username}.extraGroups = [ "input" ];
}
