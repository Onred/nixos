{ pkgs, ... }:

{
  services.desktopManager.plasma6.enable = true;
  services.displayManager.plasma-login-manager.enable = true;
  programs.kdeconnect.enable = true;

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
