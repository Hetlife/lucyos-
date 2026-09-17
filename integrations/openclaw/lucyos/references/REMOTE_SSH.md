# LucyOS remote bridge over SSH

Purpose: let an OpenClaw node call the Mark-2 LucyOS control plane without a
new public HTTP listener, duplicate database, queue, scheduler, or secret store.

## Security model

- Reuse Mark-2's existing SSH transport; do not expose a new port.
- Use a dedicated SSH key/identity when the SCS.ADMIN01 node is available.
- Configure that key with a forced command pointing to `lucyos-remote-dispatch`.
- Disable PTY, agent forwarding, X11 forwarding, and port forwarding for the key.
- The dispatcher never invokes a shell and accepts only the bounded allowlist.
- Architecture proposals are sent on stdin with a 16 KiB limit.
- Output is bounded and every command has a 30 second timeout.
- Mark-2 remains the only canonical LucyOS state holder.

## Client mode

Set `LUCYOS_REMOTE_SSH_TARGET` on the OpenClaw node. Optional settings are
`LUCYOS_REMOTE_SSH_PORT`, `LUCYOS_REMOTE_SSH_KEY`, and
`LUCYOS_REMOTE_CONNECT_TIMEOUT`. `lucyosctl` then uses BatchMode SSH and clears
all forwarding requests.

Activation of the dedicated key/account is intentionally deferred until the
SCS.ADMIN01 node is reachable. Do not copy a private key from Mark-2 to SCS.
