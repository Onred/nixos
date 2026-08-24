{
  config,
  lib,
  pkgs,
  username,
  ...
}:

let
  privatePort = 8189;

  comfyUiDesktop = pkgs.makeDesktopItem {
    name = "comfyui";
    desktopName = "ComfyUI";
    genericName = "Local AI Image Generator";
    comment = "Create images with local diffusion models";
    exec = "${pkgs.xdg-utils}/bin/xdg-open http://127.0.0.1:8188";
    icon = "applications-graphics";
    categories = [ "Graphics" ];
  };

  comfyUiPrivateLauncher = pkgs.writeShellApplication {
    name = "comfyui-private";
    runtimeInputs = with pkgs; [
      coreutils
      curl
      firefox
      systemd
    ];
    text = ''
      url=http://127.0.0.1:${toString privatePort}
      profile_dir="''$(mktemp --directory --tmpdir="''${XDG_RUNTIME_DIR:?}" comfyui-private-firefox.XXXXXX)"

      cleanup() {
        systemctl stop comfyui-private.service >/dev/null 2>&1 || true
        chmod --recursive u+w -- "''$profile_dir" 2>/dev/null || true
        rm --recursive --force --one-file-system -- "''$profile_dir"
      }
      trap cleanup EXIT HUP INT TERM

      systemctl start comfyui-private.service

      ready=
      for _ in {1..120}; do
        if curl --fail --silent --output /dev/null "''$url"; then
          ready=1
          break
        fi

        if ! systemctl is-active --quiet comfyui-private.service; then
          echo "ComfyUI Private failed to start" >&2
          exit 1
        fi

        sleep 0.25
      done

      if [[ -z "''$ready" ]]; then
        echo "Timed out waiting for ComfyUI Private" >&2
        exit 1
      fi

      firefox \
        --new-instance \
        --no-remote \
        --profile "''$profile_dir" \
        --private-window "''$url"
    '';
  };

  comfyUiPrivateDesktop = pkgs.makeDesktopItem {
    name = "comfyui-private";
    desktopName = "ComfyUI Private";
    genericName = "Private Local AI Image Generator";
    comment = "Use ComfyUI without retaining session history";
    exec = lib.getExe comfyUiPrivateLauncher;
    icon = "view-private";
    categories = [ "Graphics" ];
  };
in

{
  services.comfyui = {
    enable = true;
    gpuSupport = "cuda";
    enableManager = true;
    extraArgs = [
      "--disable-api-nodes"
      "--enable-assets"
    ];
  };

  environment.persistence."/persist".directories = [
    {
      directory = "/var/lib/comfyui";
      user = "comfyui";
      group = "comfyui";
      mode = "0750";
    }
  ];

  systemd = {
    tmpfiles.rules = [
      "d /var/lib/comfyui/models 0750 comfyui comfyui -"
    ];

    services.comfyui-private = {
      description = "Ephemeral private ComfyUI session";
      wants = [ "network-online.target" ];
      after = [ "network-online.target" ];
      unitConfig.RequiresMountsFor = "/var/lib/comfyui/models";

      serviceConfig = {
        Type = "simple";
        User = "comfyui";
        Group = "comfyui";
        SupplementaryGroups = [
          "video"
          "render"
        ];
        ExecStart = lib.escapeShellArgs [
          (lib.getExe config.services.comfyui.package)
          "--listen"
          "127.0.0.1"
          "--port"
          (toString privatePort)
          "--base-directory"
          "/run/comfyui-private"
          "--models-directory"
          "/var/lib/comfyui/models"
          "--database-url"
          "sqlite:///:memory:"
          "--disable-metadata"
          "--disable-api-nodes"
        ];
        RuntimeDirectory = "comfyui-private";
        RuntimeDirectoryMode = "0700";
        WorkingDirectory = "/run/comfyui-private";
        UMask = "0077";
        Restart = "no";
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectControlGroups = true;
        ProtectHome = true;
        ProtectKernelModules = true;
        ProtectKernelTunables = true;
        ProtectSystem = "strict";
        ReadOnlyPaths = [ "/var/lib/comfyui/models" ];
        ReadWritePaths = [ "/run/comfyui-private" ];
        RestrictNamespaces = true;
        RestrictRealtime = true;
        RestrictSUIDSGID = true;
      };
    };
  };

  security.polkit.extraConfig = ''
    polkit.addRule(function(action, subject) {
      var verb = action.lookup("verb");
      if (subject.user == "${username}"
          && action.id == "org.freedesktop.systemd1.manage-units"
          && action.lookup("unit") == "comfyui-private.service"
          && (verb == "start" || verb == "stop")) {
        return polkit.Result.YES;
      }
    });
  '';

  users.users.${username}.packages = [
    comfyUiDesktop
    comfyUiPrivateDesktop
  ];

  nix.settings = {
    extra-substituters = [
      "https://comfyui.cachix.org"
      "https://nix-community.cachix.org"
    ];
    extra-trusted-public-keys = [
      "comfyui.cachix.org-1:33mf9VzoIjzVbp0zwj+fT51HG0y31ZTK3nzYZAX0rec="
      "nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs="
    ];
  };
}
