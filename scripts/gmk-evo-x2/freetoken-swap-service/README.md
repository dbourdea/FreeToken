# GMKtek EVO-X2 native swap user service

These reviewed templates mirror the qualified one-owner production layout without publishing credentials or host identity.

1. Replace `/home/USER` in `models.toml.example` with the deployment account home directory.
2. Replace `REPLACE_WITH_A_GENERATED_SECRET` with a fresh high-entropy API key and install the catalog as mode 600 at `~/.config/freetoken-swap/models.toml`.
3. Install `freetoken-power-profile.sh` as mode 700 at `~/.local/bin/freetoken-power-profile.sh`; review the PCI address and validated firmware limits for the target machine.
4. Install `freetoken-swap.service` as mode 600 at `~/.config/systemd/user/freetoken-swap.service` after placing the reviewed source and runtime at the paths encoded by the unit.
5. Run `systemd-analyze --user verify`, enable user lingering, then enable the unit under `default.target`.
6. Prove startup with a real reboot, authenticated health, exact resident identity, positive owned-process AMD memory, and a deterministic completion. A bound port or active process is not sufficient.

The unit intentionally requests the generic thermal watchdog without ordering itself after that watchdog. Ordering after a watchdog that itself starts after `default.target` creates a boot cycle and can delete the model-service start job.
