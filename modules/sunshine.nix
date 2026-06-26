{ pkgs, username, ... }:

let
  sunshineModeSwitch = pkgs.writeShellApplication {
    name = "sunshine-mode-switch";
    runtimeInputs = [
      pkgs.coreutils
      pkgs.gnugrep
      pkgs.kdePackages.libkscreen
    ];
    text = ''
      OUTPUT="DP-1"
      STREAMING_MODE="2560x1440@59.95"
      SAVE_FILE="''${XDG_RUNTIME_DIR:-/tmp}/sunshine_saved_mode"

      set_mode() {
        kscreen-doctor "output.$OUTPUT.mode.$1"
      }

      case "''${1:-}" in
        start)
          active_mode=$(kscreen-doctor --outputs 2>/dev/null \
            | grep -oP '\d+x\d+@\d+(?:\.\d+)?\*' \
            | head -1 \
            | tr -d '*')

          if [[ -n "$active_mode" ]]; then
            echo "$active_mode" > "$SAVE_FILE"
            set_mode "$STREAMING_MODE"
          else
            echo "Warning: could not detect active mode" >&2
            exit 1
          fi
          ;;
        stop)
          if [[ -f "$SAVE_FILE" ]]; then
            saved=$(cat "$SAVE_FILE")
            rm -f "$SAVE_FILE"
            set_mode "$saved"
          else
            echo "No saved mode found, skipping restore" >&2
          fi
          ;;
        *)
          echo "Usage: $0 {start|stop}" >&2
          exit 1
          ;;
      esac
    '';
  };
in
{
  services.sunshine = {
    enable = true;
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
      nvenc_twopass = false;
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
        {
          name = "Desktop";
          command = "";
          exclude-global-prep-cmd = "false";
          auto-detach = "true";
          prep-cmd = [
            {
              do = "${sunshineModeSwitch}/bin/sunshine-mode-switch start";
              undo = "${sunshineModeSwitch}/bin/sunshine-mode-switch stop";
            }
          ];
        }

        {
          name = "Steam";
          command = "${pkgs.util-linux}/bin/setsid ${pkgs.steam}/bin/steam -bigpicture";
          exclude-global-prep-cmd = "false";
          auto-detach = "true";
          preload-timeout = "15";
          wait-command-timeout = "20";
          prep-cmd = [
            {
              do = "${sunshineModeSwitch}/bin/sunshine-mode-switch start";
              undo = "${sunshineModeSwitch}/bin/sunshine-mode-switch stop";
            }
          ];
        }
      ];
    };
  };
}
