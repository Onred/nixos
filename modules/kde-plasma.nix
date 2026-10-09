{ pkgs, ... }:

{
  services.desktopManager.plasma6.enable = true;
  services.displayManager.plasma-login-manager.enable = true;
  programs.kdeconnect.enable = true;

  systemd.user.services.plasma-login-powerdevil = {
    description = "PowerDevil for the login screen";
    wantedBy = [ "plasma-login-wayland.target" ];
    partOf = [ "plasma-login-wayland.target" ];
    after = [ "plasma-login-kwin_wayland.service" ];
    unitConfig.ConditionUser = "plasmalogin";
    serviceConfig = {
      ExecStart = "${pkgs.kdePackages.powerdevil}/libexec/org_kde_powerdevil";
      Type = "dbus";
      BusName = "org.kde.Solid.PowerManagement";
      TimeoutStopSec = "5s";
      Restart = "on-failure";
    };
  };

  environment.systemPackages = with pkgs; [
    kdePackages.plasma-vault
  ];

  environment.persistence."/persist".directories = [
    {
      directory = "/var/lib/plasmalogin";
      user = "plasmalogin";
      group = "plasmalogin";
      mode = "0750";
    }
  ];
}
