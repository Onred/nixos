{ pkgs, ... }:

{
  services.pipewire.wireplumber.extraConfig."50-evo4-stereo-profile" = {
    "monitor.alsa.rules" = [
      {
        matches = [
          {
            "device.name" = "~alsa_card.usb-Audient_EVO4.*";
          }
        ];
        actions = {
          update-props = {
            "device.profile-set" = "simple-headphones-mic.conf";
            "device.profile" = "output:analog-stereo+input:analog-stereo";
            "device.nick" = "Audient EVO 4";
          };
        };
      }
    ];
  };

  services.udev.extraRules = ''
    SUBSYSTEM=="sound", KERNEL=="card*", ATTRS{manufacturer}=="Audient", ATTRS{product}=="EVO4", ENV{ACP_PROFILE_SET}="simple-headphones-mic.conf"
    SUBSYSTEM=="sound", KERNEL=="card*", ATTRS{manufacturer}=="Audient", ATTRS{product}=="EVO 4", ENV{ACP_PROFILE_SET}="simple-headphones-mic.conf"
  '';

  environment.systemPackages = with pkgs; [
    alsa-utils
    pulseaudio # pactl/pacmd tools for PipeWire's PulseAudio-compatible server
  ];
}
