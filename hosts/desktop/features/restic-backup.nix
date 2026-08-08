{ username, ... }:

{
  services.restic.backups.desktop = {
    repository = "/mnt/data/backups/restic";
    passwordFile = "/var/lib/restic/password";
    initialize = true;
    inhibitsSleep = true;

    paths = [
      "/home/${username}"
      "/persist"
    ];

    exclude = [
      "/home/${username}/.cache"
      "/home/${username}/.local/share/Steam/steamapps/common"
      "/home/${username}/.local/share/Steam/steamapps/downloading"
      "/home/${username}/.local/share/Steam/steamapps/shadercache"
      "/home/${username}/.local/share/Steam/steamapps/temp"
      "/home/${username}/.local/share/Trash"
      "/persist/var/lib/restic/password"
      "/persist/var/lib/libvirt/images"
      "/persist/var/lib/private/ollama"
    ];

    pruneOpts = [
      "--keep-daily 7"
      "--keep-weekly 5"
      "--keep-monthly 12"
      "--keep-yearly 3"
    ];

    timerConfig = {
      OnCalendar = "daily";
      Persistent = true;
      RandomizedDelaySec = "1h";
    };
  };

  environment.persistence."/persist".files = [
    {
      file = "/var/lib/restic/password";
      parentDirectory.mode = "0700";
    }
  ];

  systemd.services.restic-backups-desktop.unitConfig = {
    ConditionPathExists = "/var/lib/restic/password";
    RequiresMountsFor = "/mnt/data";
  };
}
