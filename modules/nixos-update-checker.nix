{
  programs.nixos-update-checker = {
    enable = true;
    repository = "/home/onred/nixos";
  };

  environment.persistence."/persist".directories = [
    "/var/lib/nixos-update-checker"
  ];
}
