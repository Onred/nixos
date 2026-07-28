{ pkgs, unstable, username, ... }:

{
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

    extraPackages = with pkgs; [ kdePackages.breeze ];
  };

  users.users.${username}.packages = with pkgs; [
    protonplus
    lutris
    unstable.faugus-launcher
    mangohud
  ];
}
