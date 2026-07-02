{ config, pkgs, lib, username, ... }: {
  systemd.services.nixos-update-check = {
    description = "Check for NixOS flake updates";
    path = [ pkgs.nix pkgs.libnotify pkgs.git ];
    environment.NIX_CONFIG = "experimental-features = nix-command flakes";
    script = ''
      exec 2>&1
      flake=/home/${username}/nixos
      cd "$flake" || { echo "FAIL: cd /home/${username}/nixos"; exit 1; }
      if ! git diff --quiet flake.lock; then
        echo "flake.lock is dirty, skipping "
        exit 0
      fi
      echo "running nix flake update..."
      nix flake update 2>&1 || echo "FAIL: nix flake update (exit $?)"
      if ! git diff --quiet flake.lock; then
        echo "updates found, sending notification"
          DISPLAY=:0 \
          DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
          ${pkgs.libnotify}/bin/notify-send -u normal "NixOS Updates" "flake-update -- Updates available" \
          || echo "FAIL: notify-send failed (exit $?)"
      else
        echo "no updates found"
      fi
      git restore flake.lock
      echo "done"
    '';
    serviceConfig.Type = "oneshot";
    serviceConfig.User = username;
    serviceConfig.Group = "users";
  };

  systemd.timers.nixos-update-check = {
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "hourly";
      Persistent = true;
    };
  };
}
