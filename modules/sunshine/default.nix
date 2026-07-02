{ pkgs, username, ... }:

let
  outputName = "DP-1";
  sunshinePackage = pkgs.sunshine.override {
    cudaSupport = true;
  };

  displayProfiles = {
    tv = [ "2560x1440@120" ];
    steamDeck = [ "1920x1080@60" ];
  };

  sunshineModeSwitch = pkgs.writeShellApplication {
    name = "sunshine-mode-switch";
    runtimeInputs = [
      pkgs.gawk
      pkgs.coreutils
      pkgs.kdePackages.libkscreen
    ];
    text = ''
      OUTPUT_NAME="${outputName}"
    ''
    + builtins.readFile ./mode-switch.sh;
  };

  steamBigPictureCommand = "${pkgs.steam}/bin/steam steam://open/bigpicture";

  mkDisplayPrep = modes: [
    {
      do = "${sunshineModeSwitch}/bin/sunshine-mode-switch start ${builtins.concatStringsSep " " modes}";
      undo = "${sunshineModeSwitch}/bin/sunshine-mode-switch stop";
    }
  ];

  mkSteamApp =
    {
      name,
      modes,
    }:
    {
      inherit name;
      command = steamBigPictureCommand;
      exclude-global-prep-cmd = "false";
      auto-detach = "true";
      preload-timeout = "15";
      wait-command-timeout = "20";
      prep-cmd = mkDisplayPrep modes;
    };
in
{
  services.sunshine = {
    enable = true;
    package = sunshinePackage;
    autoStart = true;
    openFirewall = true;
    capSysAdmin = true;

    settings = {
      sunshine_name = "nixos";
      locale = "en";
      min_log_level = "info";
      adapter_name = "/dev/dri/renderD129";
      encoder = "nvenc";

      nvenc_preset = "p6";
      nvenc_twopass = "disabled";
      nvenc_spatial_aq = true;
      nvenc_latency_over_power = true;

      capture = "kms";

      max_bitrate = 0;
      minimum_fps_target = 0;
      min_threads = 2;

      hevc_mode = 0;
      av1_mode = 0;

      stream_audio = true;

      lan_encryption_mode = 1;
      wan_encryption_mode = 2;
    };

    applications = {
      env = {
        PATH = "$(PATH):/home/${username}/.local/bin";
      };

      apps = [
        (mkSteamApp {
          name = "Steam TV";
          modes = displayProfiles.tv;
        })

        (mkSteamApp {
          name = "Steam Deck";
          modes = displayProfiles.steamDeck;
        })
      ];
    };
  };
}
