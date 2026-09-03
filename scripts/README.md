# scripts/

| Script | What it does | When to run |
|---|---|---|
| `install.sh` | Symlinks `aion` into `~/.local/bin`, creates the shared brain, the secret store and a first backup, then prints health | Once, on the Ubuntu PC |
| `install_services.sh` | Installs the systemd `--user` units for the bridge and the nightly timer | After `install.sh` |
| `maintenance.sh` | Boot loop, notebook sync, backup with restore test, doc regeneration, secret scan, deep health — all inside one logged session | Nightly, via the timer |
| `pre-commit` | Blocks a commit carrying credential-shaped content or failing tests | Automatically, once installed |
| `install_hooks.sh` | Installs the pre-commit hook | Once, after cloning |

All scripts are idempotent and safe to re-run. `maintenance.sh` exits non-zero
only when health actually fails, so the timer surfaces real problems and stays
quiet otherwise.
