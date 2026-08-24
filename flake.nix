{
  description = "Onred's NixOS configuration";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-26.05";
    nixpkgs-unstable.url = "nixpkgs/nixos-unstable";

    nixos-update-checker = {
      url = "github:Onred/nixos-update-checker";
      inputs.nixpkgs.follows = "nixpkgs";
    };

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

  outputs =
    inputs@{
      self,
      nixpkgs,
      nixpkgs-unstable,
      disko,
      ...
    }:
    let
      # Local system settings
      system = "x86_64-linux";
      hostName = "nixos";
      username = "onred";
      fullName = "Onred";

      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
      unstable = import nixpkgs-unstable {
        inherit system;
        config.allowUnfree = true;
      };
      installer = import ./lib/installer.nix {
        inherit hostName pkgs username;
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

      nixosConfigurations.${hostName} = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = {
          inherit inputs unstable;
          inherit fullName hostName username;
        };
        modules = [ ./configuration.nix ];
      };
    };
}
