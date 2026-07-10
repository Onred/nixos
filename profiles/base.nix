{ fullName, hostName, lib, username, ... }:

{
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  nixpkgs.config.allowUnfree = true;

  networking.hostName = hostName;
  networking.networkmanager.enable = true;

  time.timeZone = "Asia/Tokyo";
  i18n.defaultLocale = "en_US.UTF-8";

  users.mutableUsers = false;
  users.users.${username} = {
    isNormalUser = true;
    description = fullName;
    hashedPasswordFile = lib.mkDefault "/persist/secrets/${username}-password-hash";
    extraGroups = [
      "networkmanager"
      "wheel"
    ];
  };

  system.stateVersion = "26.05";
}
