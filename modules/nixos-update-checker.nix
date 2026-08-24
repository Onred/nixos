{
  hostName,
  inputs,
  username,
  ...
}:

{
  imports = [ inputs.nixos-update-checker.nixosModules.default ];

  programs.nixos-update-checker = {
    enable = true;
    repository = "/home/${username}/${hostName}";
  };

  environment.persistence."/persist".directories = [
    "/var/lib/nixos-update-checker"
  ];
}
