{ ... }:

{
  services.pipewire.wireplumber.extraConfig."50-evo4-stereo" = {
    "monitor.alsa.rules" = [
      {
        matches = [
          {
            "device.name" = "~alsa_card.usb-Audient_EVO4.*";
          }
        ];
        actions = {
          update-props = {
            "api.acp.disable-pro-audio" = true;
            "device.profile" = "output:analog-stereo+input:analog-stereo";
            "device.nick" = "Audient EVO 4";
          };
        };
      }
    ];
  };

  services.udev.extraRules = ''
    SUBSYSTEM=="sound", KERNEL=="card*", ATTRS{idVendor}=="2708", ATTRS{idProduct}=="0006", ENV{ACP_PROFILE_SET}="simple-headphones-mic.conf"
  '';
}
