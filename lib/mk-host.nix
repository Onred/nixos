{ externalModules ? [ ], fullName, localConfig, nixpkgs, system, unstable, username }:

{
  hostName,
  modules,
  specialArgs ? { },
}:

nixpkgs.lib.nixosSystem {
  inherit system;
  specialArgs = {
    inherit fullName hostName localConfig unstable username;
  } // specialArgs;
  modules = externalModules ++ modules;
}
