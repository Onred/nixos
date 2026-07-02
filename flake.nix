{
  description = "Onred's NixOS configuration";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-26.05";
    # nixpkgs-unstable.url = "nixpkgs/nixos-unstable";

    disko = {
      url = "github:nix-community/disko/latest";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    impermanence = {
      url = "github:nix-community/impermanence";
      inputs.nixpkgs.follows = ""; # Remove unneeded dev dependency
      inputs.home-manager.follows = ""; # Remove unneeded dev dependency
    };
  };

  outputs = { self, nixpkgs, /*nixpkgs-unstable,*/ disko, impermanence, ... }:
    let
      system = "x86_64-linux";
      username = "onred";
      pkgs = import nixpkgs { inherit system; config.allowUnfree = true; };
      # unstable = import nixpkgs-unstable { inherit system; config.allowUnfree = true; };
      installer = import ./lib/installer.nix {
        inherit pkgs username;
        configSource = self;
        diskoPackage = disko.packages.${system}.disko;
      };
    in
    {
      apps.${system}.install = {
        type = "app";
        program = "${installer}/bin/install-nixos";
        meta.description = "Install this NixOS configuration onto an explicitly selected disk";
      };

      nixosConfigurations.nixos = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit username /*unstable*/; };
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./configuration.nix
        ];
      };
    };
}
