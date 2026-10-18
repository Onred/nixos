# Remote access and streaming

Last reviewed: 2026-10-14. Automatic Plasma login is working after removing the
custom KWin startup override. Locking uses the normal Plasma lock timer.

- [ ] Confirm Ethernet wake-on-LAN is enabled after applying the configuration,
  check firmware wake settings, and test waking the PC from suspend.
- [ ] Reserve the PC's LAN address (`10.44.15.86`) in UniFi.
- [ ] Finish UpSnap's initial account and PC device setup if not already done.
  PC MAC: `34:5a:60:c2:aa:61`. Wake page: `http://100.83.111.120:8090`.
- [ ] Configure and test iPhone Tailscale access over Wi-Fi and cellular, with
  automatic connection and no exit node. Verify ordinary internet access.
- [ ] Test Moonlight pairing and Sunshine streaming after reboot before any
  local login, and after waking from sleep.
- [ ] Test the KWin virtual monitor, NVIDIA encoding, physical OLED switching
  off during streaming, and restoration when quitting the streamed app.
  The virtual monitor currently supports SDR.
- [ ] Verify remote Open WebUI access at `http://10.44.15.86:8080` and that
  connected sessions inhibit sleep and release the inhibitor on disconnect.
- [ ] Choose access permissions before sharing services with family. Open
  WebUI currently has no sign-in for trusted LAN/VPN access.
- [ ] Investigate a packaged solution for waking automatically when opening a
  service. Currently the user must press Wake in UpSnap first.
- [ ] Decide whether to add Jellyfin, including media locations and sleep
  behavior during playback.
- [ ] Run `sync git` when ready to checkpoint and archive the configuration.

The Pi (`relay`) already runs Tailscale and UpSnap. Its `10.44.0.0/16` subnet
route is approved and Tailscale key expiry is disabled. Its Tailscale address
is stable while it remains registered. A move to a different subnet needs a
route and wake-packet review. Local PC use does not depend on the Pi; remote
access through this route and remote waking do.
