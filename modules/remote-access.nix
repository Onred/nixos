{ ... }:

{
  services.openssh = {
    enable = true;
    openFirewall = false;
  };

  networking.firewall.interfaces.enp6s0.allowedTCPPorts = [ 22 ];

  environment.persistence."/persist".files = [
    "/etc/ssh/ssh_host_ed25519_key"
    "/etc/ssh/ssh_host_ed25519_key.pub"
    "/etc/ssh/ssh_host_rsa_key"
    "/etc/ssh/ssh_host_rsa_key.pub"
  ];
}
