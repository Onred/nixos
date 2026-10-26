{ pkgs, username, ... }:

let
  models = import ./models.nix;
  whisperModel = pkgs.fetchurl models.whisper;

  dictationConfig = (pkgs.formats.toml { }).generate "voxtype.toml" {
    hotkey.enabled = false;
    audio.device = "default";
    whisper = {
      model = "${whisperModel}";
      language = "auto";
      threads = 4;
      on_demand_loading = true;
    };
    output = {
      mode = "type";
      driver_order = [ "ydotool" "clipboard" ];
      fallback_to_clipboard = true;
    };
  };
in
{
  programs.ydotool.enable = true;
  users.users.${username} = {
    extraGroups = [ "ydotool" ];
    packages = [
      pkgs.voxtype
      (pkgs.makeDesktopItem {
        name = "dictation";
        desktopName = "Dictation";
        comment = "Start or stop local voice dictation";
        exec = "${pkgs.voxtype}/bin/voxtype record toggle";
        icon = "audio-input-microphone";
        categories = [ "Utility" "Accessibility" ];
        terminal = false;
      })
    ];
  };

  systemd.user.services.voxtype = {
    description = "Local Whisper dictation";
    wantedBy = [ "graphical-session.target" ];
    partOf = [ "graphical-session.target" ];
    after = [ "graphical-session.target" "pipewire.service" ];
    unitConfig.ConditionUser = username;
    path = [ pkgs.ydotool pkgs.wl-clipboard ];
    environment.YDOTOOL_SOCKET = "/run/ydotoold/socket";
    serviceConfig = {
      ExecStart = "${pkgs.voxtype}/bin/voxtype --config ${dictationConfig}";
      Restart = "on-failure";
      RestartSec = "3s";
    };
  };
}
