{ pkgs, username, ... }:

{
  programs.steam = {
    enable = true;
    remotePlay.openFirewall = true;
    package = pkgs.steam.override {
      extraArgs = "-pipewire";
    };
  };

  programs.gamescope.enable = true;
  programs.gamemode.enable = true;

  users.users.${username} = {
    extraGroups = [ "gamemode" ];
    packages = with pkgs; [
      mangohud
      protonplus
    ];
  };

  services.restic.backups.desktop.exclude = [
    "/home/${username}/.local/share/Steam/steamapps/common"
    "/home/${username}/.local/share/Steam/steamapps/downloading"
    "/home/${username}/.local/share/Steam/steamapps/shadercache"
    "/home/${username}/.local/share/Steam/steamapps/temp"
  ];
}
