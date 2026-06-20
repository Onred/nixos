{
  description = "Onred's NixOS configuration";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-26.05";

    disko = {
      url = "github:nix-community/disko/latest";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    impermanence = {
      url = "github:nix-community/impermanence";
      inputs.nixpkgs.follows = "";
      inputs.home-manager.follows = "";
    };
  };

  outputs = { self, nixpkgs, disko, impermanence, ... }:
    let
      system = "x86_64-linux";
      username = "onred";
      pkgs = nixpkgs.legacyPackages.${system};
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
        specialArgs = { inherit username; };
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./configuration.nix
        ];
      };
    };
}
