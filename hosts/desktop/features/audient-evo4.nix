{ ... }:

{
  services.pipewire.extraConfig.pipewire."50-evo4-stereo-sink" = {
    "context.modules" = [
      {
        name = "libpipewire-module-combine-stream";
        args = {
          "combine.mode" = "sink";
          "node.name" = "evo4_stereo";
          "node.description" = "Audient EVO 4";
          "combine.latency-compensate" = false;
          "combine.props" = {
            "audio.position" = [ "FL" "FR" ];
            "priority.session" = 2000;
          };
          "stream.props" = {
            "stream.dont-remix" = true;
          };
          "stream.rules" = [
            {
              matches = [
                {
                  "media.class" = "Audio/Sink";
                  "node.name" = "alsa_output.usb-Audient_EVO4-00.pro-output-0";
                }
              ];
              actions = {
                "create-stream" = {
                  "combine.audio.position" = [ "FL" "FR" ];
                  "audio.position" = [ "AUX0" "AUX1" ];
                };
              };
            }
          ];
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
}
