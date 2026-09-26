#!/usr/bin/env python3
import argparse
import os
import sys
import paramiko

def main():
    parser = argparse.ArgumentParser(
        description="Remote deployment script for AWG Manager on Keenetic router."
    )
    parser.add_argument("--host", default=os.getenv("ROUTER_HOST"), help="Router IP address (or set ROUTER_HOST env var)")
    parser.add_argument("--port", type=int, default=int(os.getenv("ROUTER_PORT", "22")), help="Router SSH port (or set ROUTER_PORT env var, default: 22)")
    parser.add_argument("--user", default=os.getenv("ROUTER_USER", "root"), help="Router SSH user (or set ROUTER_USER env var, default: root)")
    parser.add_argument("--password", default=os.getenv("ROUTER_PASS"), help="Router SSH password (or set ROUTER_PASS env var)")

    args = parser.parse_args()

    # Fallback/validation checks
    if not args.host:
        sys.exit("[ERROR] Missing router IP/host. Pass --host or set ROUTER_HOST environment variable.")
    if not args.password:
        sys.exit("[ERROR] Missing router SSH password. Pass --password or set ROUTER_PASS environment variable.")

    # Shell commands to run on the router
    remote_command = (
        "set -e\n"
        "echo '[1/3] Checking Entware (opkg)...'\n"
        "if ! command -v opkg >/dev/null 2>&1; then echo '[ERROR] opkg not found!'; exit 1; fi\n"
        "echo '[2/3] Updating package manager...'\n"
        "opkg update\n"
        "echo '[3/3] Fetching and executing AWG Manager installer...'\n"
        "curl -sL https://raw.githubusercontent.com/hoaxisr/awg-manager/develop/scripts/install.sh | sh\n"
    )

    print(f"--> Connecting to router at {args.user}@{args.host}:{args.port}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=args.host,
            port=args.port,
            username=args.user,
            password=args.password,
            timeout=10
        )
        print("[SUCCESS] Connected to router. Executing deployment remote pipeline...\n")

        # Open an interactive SSH channel to run the pipeline
        session = ssh.get_transport().open_session()
        session.exec_command(remote_command)

        # Stream stdout and stderr in real-time
        while True:
            if session.recv_ready():
                print(session.recv(1024).decode('utf-8', errors='ignore'), end="")
            if session.recv_stderr_ready():
                print(session.recv_stderr(1024).decode('utf-8', errors='ignore'), file=sys.stderr, end="")
            if session.exit_status_ready():
                break

        exit_code = session.recv_exit_status()
        if exit_code == 0:
            print("\n[SUCCESS] AWG Manager remote installation completed successfully!")
        else:
            print(f"\n[ERROR] Remote script failed with exit code: {exit_code}")

    except Exception as e:
        print(f"[ERROR] SSH connection failed: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    main()