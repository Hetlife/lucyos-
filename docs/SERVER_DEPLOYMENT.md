# Server deployment

AION is designed to live on one permanent machine — the "Ubuntu PC" in the
architecture diagram. This document covers running that machine as a cloud
server rather than hardware on a desk.

The generic install is in `OPERATIONS.md`. This file covers only what is
different about a public-internet host.

## The machine

| | |
|---|---|
| Host | DigitalOcean droplet, Ubuntu 24.04 LTS, 4 GB RAM |
| User | `aion` — passwordless sudo, SSH key auth only |
| Shared brain | `~/openclaw/shared_brain` (default `AION_HOME`) |
| Repo | `~/lucyos`, branch `claude/aion-whatsapp-control-1seild` |

Python 3.9+ is the only runtime requirement. `aion_core/` is standard library
only, so there is nothing to install and nothing to keep patched beyond the OS
itself.

## Provisioning a fresh host

```bash
# as root, once
id -u aion >/dev/null 2>&1 || adduser aion --disabled-password --gecos ""
usermod -aG sudo aion
echo "aion ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/aion && chmod 440 /etc/sudoers.d/aion
mkdir -p /home/aion/.ssh
echo "<your public key>" >> /home/aion/.ssh/authorized_keys
chmod 700 /home/aion/.ssh && chmod 600 /home/aion/.ssh/authorized_keys
chown -R aion:aion /home/aion/.ssh
loginctl enable-linger aion
```

`enable-linger` is not optional: without it every `systemd --user` unit dies
when the last session closes, so the bridge and the timers stop the moment you
disconnect.

Then the install itself, as `aion`:

```bash
git clone -b claude/aion-whatsapp-control-1seild https://github.com/Hetlife/lucyos-.git ~/lucyos
cd ~/lucyos
scripts/install.sh
scripts/install_hooks.sh
python3 -m unittest discover -s tests -t . -q    # must pass before going further
aion secrets set PHONE_API_TOKEN
scripts/install_services.sh
systemctl --user enable --now aion-bridge.service
```

Generate tokens on the machine, never in a chat window or an editor on another
device:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(32))"
```

## Hardening

A public IP is scanned within minutes of existing. Both of these are worth
doing before the host has anything on it worth reaching.

```bash
ufw allow 22/tcp && ufw --force enable
systemctl enable --now fail2ban
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart ssh
```

Disable password authentication only after a key is confirmed working, or the
provider's web console becomes the only way back in.

## Reaching the phone interface

The bridge binds to `127.0.0.1:8765` and the firewall exposes only port 22.
This is deliberate. The phone API carries a bearer token and has no TLS of its
own, so it must not sit on the open internet.

Reach it by tunnelling:

```bash
ssh -L 8765:127.0.0.1:8765 aion@<host>
# then open http://localhost:8765/app on that device
```

Mobile SSH clients (Termius, Blink) express the same thing as a port-forwarding
rule on the host entry: local `8765` to `127.0.0.1:8765`.

Do not `ufw allow 8765`, and do not rebind the bridge to `0.0.0.0`. If the
interface genuinely needs to be public later, the answer is a domain, a reverse
proxy and a real certificate — with the token still required — not an open port.

## Note on SSH over port 443

Some restricted networks block outbound port 22. `sshd` can listen on 443 as
well, but on Ubuntu 24.04 the `Port` directive in `sshd_config` is **ignored**
when SSH is socket-activated, which it is by default. The socket unit binds the
port, not the daemon. To make extra ports work:

```bash
systemctl disable --now ssh.socket
systemctl enable --now ssh.service
```

Only then does a second `Port 443` line in `sshd_config` take effect. Verify
with `ss -tlnp | grep -E ':22|:443'` — trust that output, not the config file.

## What runs continuously

| Unit | Schedule | What it does |
|---|---|---|
| `aion-bridge.service` | always | webhook + phone API on 127.0.0.1:8765 |
| `aion-work.timer` | every 10 min | the build loop; pauses itself on a major milestone |
| `aion-maintenance.timer` | nightly 03:15 | boot loop, notebook sync, backup with a real restore test, doc regeneration, secret scan, deep health check |

The build loop stopping at a major milestone is intended behaviour, not a
failure. A major milestone is an owner decision point.

## Verifying, not assuming

A unit reporting `active` proves the process started, not that it works. Prove
the real path:

```bash
curl -s http://127.0.0.1:8765/ | head
curl -s http://127.0.0.1:8765/api/status                     # expect 401
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8765/api/status | head -c 400
```

The third must return JSON containing `money`, `feed` and `needs_you`. If the
second does not return 401, the token check is not doing its job and the bridge
should be stopped until it is.
