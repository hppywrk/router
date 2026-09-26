# router
VPN on router. See https://awgm.hoaxisr.ru/install/

This repo runs the [AWG Manager](https://github.com/hoaxisr/awg-manager) installer on a Keenetic router over SSH (Entware `opkg` required).

## prerequisites

- Router with Entware and network access to GitHub
- Python 3 on the machine you run the deploy script from

```bash
pip install -r requirements.txt
```

Treat router passwords and key files as secrets. Prefer SSH keys over passwords; avoid putting passwords on the command line (they show up in shell history and process lists).

## SSH host keys

By default the script uses your system `known_hosts` and **rejects** unknown router keys. On first connect, either add the router key to `known_hosts`, or pass `--accept-unknown-host-keys` once (less secure).

## option 1. passing creds via env

```bash
export ROUTER_HOST="192.168.1.1"
export ROUTER_USER="root"
export ROUTER_PASS="YourRouterPassword"
export ROUTER_PORT="22"

python3 deploy_awgm_remote.py
```

SSH key instead of password:

```bash
export ROUTER_KEY_FILE="$HOME/.ssh/id_ed25519"
python3 deploy_awgm_remote.py
```

## option 2. passing creds via CLI

```bash
python3 deploy_awgm_remote.py --host 192.168.1.1 --user root --password YourRouterPassword --port 22
```

## installer pin

The deploy script downloads `scripts/install.sh` from `hoaxisr/awg-manager` at a **pinned commit** (see `DEFAULT_INSTALLER_REF` in `deploy_awgm_remote.py`). To use another tag, branch, or commit:

```bash
export ROUTER_INSTALLER_REF="develop"
python3 deploy_awgm_remote.py
```

Using `develop` or a moving branch runs whatever the upstream publishes at deploy time (higher trust requirement).

## options

| Flag / env | Purpose |
|------------|---------|
| `--remote-timeout` / `ROUTER_REMOTE_TIMEOUT` | Max seconds for remote install (default 900) |
| `--accept-unknown-host-keys` / `ROUTER_ACCEPT_UNKNOWN_HOST_KEYS` | Auto-accept new SSH host keys |
| `--known-hosts` / `ROUTER_KNOWN_HOSTS` | Path to known_hosts file |

Non-zero exit codes are returned on SSH failures, timeouts, or a failed remote install (for use in scripts and CI).
