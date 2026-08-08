{ pkgs, username, ... }:

{
  programs.gamemode.enable = true;

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

  users.users.${username}.packages = with pkgs; [
    protonplus
    lutris
    faugus-launcher
    mangohud
  ];
}
