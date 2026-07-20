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

  outputs = { self, nixpkgs, nixpkgs-unstable, disko, impermanence, nixos-update-checker, ... }:
    let
      system = "x86_64-linux";
      localConfig = import ./config.nix;
      username = localConfig.user.name;
      fullName = localConfig.user.fullName;
      pkgs = import nixpkgs { inherit system; config.allowUnfree = true; };
      unstable = import nixpkgs-unstable { inherit system; config.allowUnfree = true; };
      installTargets = {
        nixos = {
          flakeTarget = "nixos";
          hostDir = "hosts/desktop";
          hardwareConfig = "hosts/desktop/hardware-configuration.nix";
        };
        vm = {
          flakeTarget = "vm";
          hostDir = "hosts/vm";
          hardwareConfig = "hosts/vm/hardware-configuration.nix";
        };
      };
      installer = import ./lib/installer.nix {
        inherit installTargets pkgs username;
        configSource = self;
        diskoPackage = disko.packages.${system}.disko;
      };
      mkHost = import ./lib/mk-host.nix {
        inherit fullName localConfig nixpkgs system unstable username;
        externalModules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
        ];
      };
    in
    {
      apps.${system}.install = {
        type = "app";
        program = "${installer}/bin/install-nixos";
        meta.description = "Install this NixOS configuration onto an explicitly selected disk";
      };

      nixosConfigurations = {
        nixos = mkHost {
          hostName = localConfig.hosts.nixos.hostName;
          modules = [
            nixos-update-checker.nixosModules.default
            ./hosts/desktop 
          ];
        };

        vm = mkHost {
          hostName = localConfig.hosts.vm.hostName;
          modules = [ ./hosts/vm ];
        };
      };
    };
}
