{ pkgs, ... }:

{
  services.pipewire.extraConfig.pipewire."50-evo4-stereo-sink" = {
    "context.modules" = [
      {
        name = "libpipewire-module-loopback";
        args = {
          "node.description" = "Audient EVO 4";
          "capture.props" = {
            "node.name" = "evo4_stereo";
            "media.class" = "Audio/Sink";
            "audio.position" = [ "FL" "FR" ];
            "priority.session" = 2000;
          };
          "playback.props" = {
            "node.name" = "playback.evo4_stereo";
            "audio.position" = [ "AUX0" "AUX1" ];
            "target.object" = "alsa_output.usb-Audient_EVO4-00.pro-output-0";
            "stream.dont-remix" = true;
            "node.passive" = true;
          };
        };
      }
    ];
  };

  services.pipewire.wireplumber.extraConfig."50-evo4-pro-audio" = {
    "monitor.alsa.rules" = [
      {
        matches = [
          {
            "device.name" = "~alsa_card.usb-Audient_EVO4.*";
          }
        ];
        actions = {
          update-props = {
            "device.profile" = "pro-audio";
            "device.nick" = "Audient EVO 4";
          };
        };
      }
    ];
  };

  environment.systemPackages = with pkgs; [
    alsa-utils
    pulseaudio # pactl/pacmd tools for PipeWire's PulseAudio-compatible server
  ];
}
