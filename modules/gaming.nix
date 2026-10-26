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
}
