#!/usr/bin/env python3
import argparse
import os
import socket
import sys
import time

import paramiko

# Pinned awg-manager commit for scripts/install.sh (override with --installer-ref).
DEFAULT_INSTALLER_REF = "8fb8e36cac4a6758df96c997f3aea6953bd896de"
INSTALLER_REPO = "hoaxisr/awg-manager"
REMOTE_DEPLOY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "remote_deploy.sh")
INSTALLER_URL_PLACEHOLDER = "__INSTALLER_URL__"


def installer_url(ref: str) -> str:
    return f"https://raw.githubusercontent.com/{INSTALLER_REPO}/{ref}/scripts/install.sh"


def build_remote_command(installer_ref: str) -> str:
    try:
        with open(REMOTE_DEPLOY_SCRIPT, encoding="utf-8") as script_file:
            template = script_file.read()
    except OSError as e:
        print(f"[ERROR] Cannot read remote deploy script at {REMOTE_DEPLOY_SCRIPT}: {e}", file=sys.stderr)
        sys.exit(1)
    if INSTALLER_URL_PLACEHOLDER not in template:
        print(
            f"[ERROR] Remote deploy script missing placeholder {INSTALLER_URL_PLACEHOLDER!r}.",
            file=sys.stderr,
        )
        sys.exit(1)
    return template.replace(INSTALLER_URL_PLACEHOLDER, installer_url(installer_ref))


def configure_ssh_client(accept_unknown_host_keys: bool, known_hosts: str | None) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    if known_hosts:
        ssh.load_host_keys(os.path.expanduser(known_hosts))
    else:
        ssh.load_system_host_keys()
    policy = (
        paramiko.AutoAddPolicy()
        if accept_unknown_host_keys
        else paramiko.RejectPolicy()
    )
    ssh.set_missing_host_key_policy(policy)
    return ssh


def run_remote_command(session: paramiko.Channel, timeout_sec: int) -> int:
    deadline = time.monotonic() + timeout_sec
    while True:
        if session.recv_ready():
            print(session.recv(4096).decode("utf-8", errors="replace"), end="")
        if session.recv_stderr_ready():
            print(
                session.recv_stderr(4096).decode("utf-8", errors="replace"),
                file=sys.stderr,
                end="",
            )
        if session.exit_status_ready():
            return session.recv_exit_status()
        if time.monotonic() > deadline:
            session.close()
            print(
                f"\n[ERROR] Remote command timed out after {timeout_sec} seconds.",
                file=sys.stderr,
            )
            return 124
        time.sleep(0.05)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remote deployment script for AWG Manager on Keenetic router."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("ROUTER_HOST"),
        help="Router IP address (or set ROUTER_HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ROUTER_PORT", "22")),
        help="Router SSH port (or set ROUTER_PORT env var, default: 22)",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("ROUTER_USER", "root"),
        help="Router SSH user (or set ROUTER_USER env var, default: root)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ROUTER_PASS"),
        help="Router SSH password (or set ROUTER_PASS env var)",
    )
    parser.add_argument(
        "--key-file",
        default=os.getenv("ROUTER_KEY_FILE"),
        help="Path to SSH private key (or set ROUTER_KEY_FILE env var)",
    )
    parser.add_argument(
        "--known-hosts",
        default=os.getenv("ROUTER_KNOWN_HOSTS"),
        help="SSH known_hosts file (default: system known_hosts)",
    )
    parser.add_argument(
        "--accept-unknown-host-keys",
        action="store_true",
        default=os.getenv("ROUTER_ACCEPT_UNKNOWN_HOST_KEYS", "").lower()
        in ("1", "true", "yes"),
        help="Trust and remember new host keys (less secure; useful on first connect)",
    )
    parser.add_argument(
        "--installer-ref",
        default=os.getenv("ROUTER_INSTALLER_REF", DEFAULT_INSTALLER_REF),
        help=f"Git ref (commit/tag/branch) for install.sh (default: pinned {DEFAULT_INSTALLER_REF[:12]}…)",
    )
    parser.add_argument(
        "--remote-timeout",
        type=int,
        default=int(os.getenv("ROUTER_REMOTE_TIMEOUT", "900")),
        help="Max seconds for remote install pipeline (default: 900)",
    )

    args = parser.parse_args()

    if not args.host:
        print(
            "[ERROR] Missing router IP/host. Pass --host or set ROUTER_HOST environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not args.password and not args.key_file:
        print(
            "[ERROR] Missing credentials. Pass --password / ROUTER_PASS or --key-file / ROUTER_KEY_FILE.",
            file=sys.stderr,
        )
        sys.exit(1)

    remote_command = build_remote_command(args.installer_ref)
    print(f"--> Connecting to router at {args.user}@{args.host}:{args.port}...", flush=True)
    print(f"--> Installer: {installer_url(args.installer_ref)}", flush=True)

    ssh = configure_ssh_client(args.accept_unknown_host_keys, args.known_hosts)

    try:
        connect_kwargs = {
            "hostname": args.host,
            "port": args.port,
            "username": args.user,
            "timeout": 10,
            "allow_agent": bool(not args.key_file),
            "look_for_keys": False,
        }
        if args.password:
            connect_kwargs["password"] = args.password
        if args.key_file:
            connect_kwargs["key_filename"] = os.path.expanduser(args.key_file)

        ssh.connect(**connect_kwargs)
        print("[SUCCESS] Connected to router. Executing deployment remote pipeline...\n")

        session = ssh.get_transport().open_session()
        session.exec_command(remote_command)
        exit_code = run_remote_command(session, args.remote_timeout)

        if exit_code == 0:
            print("\n[SUCCESS] AWG Manager remote installation completed successfully!")
        else:
            print(
                f"\n[ERROR] Remote script failed with exit code: {exit_code}",
                file=sys.stderr,
            )
            sys.exit(exit_code if exit_code != 0 else 1)

    except (paramiko.SSHException, socket.error, OSError) as e:
        print(f"[ERROR] SSH connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
