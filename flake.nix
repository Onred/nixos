{
  description = "Onred's NixOS configuration";

  inputs = {
    # Main system packages. Switch to the line below once 26.11 is released.
    nixpkgs.url = "nixpkgs/nixos-unstable";
    # nixpkgs.url = "nixpkgs/nixos-26.11";

    # Selected newer packages, even after the main input moves to a release.
    nixpkgs-unstable.url = "nixpkgs/nixos-unstable";

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

  outputs = inputs: {
    nixosConfigurations.nixos = inputs.nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";

      # Additional arguments available to every configuration module.
      specialArgs = {
        inherit inputs;
        username = "onred";
        fullName = "Onred";
        hostName = "nixos";

        unstable = import inputs.nixpkgs-unstable {
          system = "x86_64-linux";
          config.allowUnfree = true;
        };
      };

      modules = [ ./configuration.nix ];
    };
  };
}
