{ pkgs, username, ... }:

let
  physicalOutput = "HDMI-A-1";
  virtualOutput = "Virtual-Sunshine";
  kscreen = "${pkgs.kdePackages.libkscreen}/bin/kscreen-doctor";
  systemctl = "${pkgs.systemd}/bin/systemctl";
  sunshinePackage = pkgs.sunshine.override {
    cudaSupport = true;
  };

  steamBigPictureCommand = "${pkgs.steam}/bin/steam steam://open/bigpicture";

  mkDisplayPrep = mode: [
    {
      do = "${systemctl} --user start sunshine-virtual-monitor.service";
      undo = "${systemctl} --user stop sunshine-virtual-monitor.service";
    }
    {
      do = "${kscreen} output.${virtualOutput}.mode.${mode} output.${virtualOutput}.position.0,0 output.${virtualOutput}.priority.1 output.${physicalOutput}.disable";
    }
  ];

  mkSteamApp =
    {
      name,
      mode,
    }:
    {
      inherit name;
      command = steamBigPictureCommand;
      preload-timeout = "15";
      wait-command-timeout = "20";
      prep-cmd = mkDisplayPrep mode;
    };
in
{
  environment.systemPackages = [ pkgs.kdePackages.krfb ];

  systemd.user.services.sunshine-virtual-monitor = {
    description = "KWin virtual monitor for Sunshine";
    partOf = [
      "graphical-session.target"
      "sunshine.service"
    ];
    after = [ "graphical-session.target" ];
    unitConfig.ConditionUser = username;
    path = [
      pkgs.coreutils
      pkgs.gnugrep
      pkgs.kdePackages.libkscreen
    ];
    serviceConfig = {
      ExecStart = "${pkgs.systemd}/bin/systemd-inhibit --what=idle:sleep --who=Sunshine --why=Streaming ${pkgs.kdePackages.krfb}/bin/krfb-virtualmonitor --desktopfile org.kde.krfb.virtualmonitor --name Sunshine --resolution 2560x1440";
      ExecStopPost = "-${kscreen} output.${physicalOutput}.enable output.${physicalOutput}.priority.1";
    };
    # KRFB creates its output asynchronously; wait before running display hooks.
    postStart = ''
      for attempt in {1..50}; do
        if kscreen-doctor --outputs | grep -Fq '${virtualOutput}'; then
          if ! kscreen-doctor output.${virtualOutput}.mode.2560x1440@120 >/dev/null 2>&1; then
            kscreen-doctor output.${virtualOutput}.addCustomMode.2560.1440.120000.reduced
          fi
          if ! kscreen-doctor output.${virtualOutput}.mode.1920x1080@60 >/dev/null 2>&1; then
            kscreen-doctor output.${virtualOutput}.addCustomMode.1920.1080.60000.reduced
          fi
          exit 0
        fi
        sleep 0.1
      done
      echo 'KWin virtual monitor did not appear' >&2
      exit 1
    '';
  };

  services.sunshine = {
    enable = true;
    package = sunshinePackage;
    openFirewall = true;

    settings = {
      sunshine_name = "nixos";
      encoder = "nvenc";

      nvenc_preset = 6;
      nvenc_twopass = "disabled";
      nvenc_spatial_aq = true;

      capture = "kwin";

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
          mode = "2560x1440@120";
        })

        (mkSteamApp {
          name = "Steam Deck";
          mode = "1920x1080@60";
        })
      ];
    };
  };
}
