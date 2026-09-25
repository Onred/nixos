{
  pkgs,
  username,
  unstable,
  ...
}:

let
  steamDesktopInput = pkgs.writeShellApplication {
    name = "steam-desktop-input";
    runtimeInputs = [ pkgs.nodejs ];
    text = ''
      exec node ${../scripts/steam/desktop-input.mjs} "$@"
    '';
  };

  watcherPython = pkgs.python3.withPackages (pythonPackages: [ pythonPackages.dbus-next ]);

  steamDesktopInputWatcher = pkgs.writeShellApplication {
    name = "steam-desktop-input-watcher";
    runtimeInputs = [ steamDesktopInput ];
    text = ''
      exec ${watcherPython}/bin/python ${../scripts/steam/desktop-input-watcher.py}
    '';
  };

  steamDesktopInputFocus = pkgs.stdenvNoCC.mkDerivation {
    pname = "steam-desktop-input-focus";
    version = "1.0";
    src = ../scripts/steam/desktop-input-focus;
    installPhase = ''
      runHook preInstall
      mkdir -p $out/share/kwin/scripts/steam-desktop-input-focus
      cp -r . $out/share/kwin/scripts/steam-desktop-input-focus
      runHook postInstall
    '';
  };

  steamDesktopInputDbus = pkgs.writeTextDir "share/dbus-1/services/org.onred.SteamDesktopInput.service" ''
    [D-BUS Service]
    Name=org.onred.SteamDesktopInput
    Exec=${steamDesktopInputWatcher}/bin/steam-desktop-input-watcher
    SystemdService=steam-desktop-input-watcher.service
  '';
in

{
  # Plasma 6.6 cannot restrict this input-emulation permission by application.
  environment.etc."xdg/kwinrc".text = ''
    [Plugins]
    steam-desktop-input-focusEnabled=true

    [Xwayland]
    XwaylandEisNoPrompt=true
  '';

  services.dbus.packages = [ steamDesktopInputDbus ];

  programs.steam = {
    enable = true;

    package = pkgs.steam.override {
      extraEnv = {
        MANGOHUD = "1";
        PROTON_ENABLE_WAYLAND = "1";
        PROTON_DXVK_LOWLATENCY = "1";
        DXVK_FRAME_PACE = "low-latency-vrr-240";
      };
    };
  };

  programs.gamescope.enable = true;
  programs.gamemode.enable = true;

  users.users.${username} = {
    extraGroups = [ "gamemode" ];
    packages = with pkgs; [
      unstable.faugus-launcher
      lutris
      mangohud
      protonplus
      steamDesktopInput
      steamDesktopInputFocus
    ];
  };

  systemd.user.services.steam-desktop-input-watcher = {
    description = "Follow KWin focus for Steam desktop input";
    wantedBy = [ "graphical-session.target" ];
    partOf = [ "graphical-session.target" ];
    serviceConfig = {
      Type = "dbus";
      BusName = "org.onred.SteamDesktopInput";
      ExecStart = "${steamDesktopInputWatcher}/bin/steam-desktop-input-watcher";
      ExecStopPost = "-${steamDesktopInput}/bin/steam-desktop-input on";
      Restart = "on-failure";
      RestartSec = "1s";
    };
  };

  systemd.tmpfiles.rules = [
    "f /home/${username}/.local/share/Steam/.cef-enable-remote-debugging 0600 ${username} users -"
  ];
}
