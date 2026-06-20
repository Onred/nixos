{ ... }:

{
  services.xserver.videoDrivers = [ "nvidia" ];

  hardware.nvidia = {
    open = true;
    nvidiaSettings = false;
    powerManagement.enable = true;
  };
}
