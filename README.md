# router
VPN on router. See https://awgm.hoaxisr.ru/install/

## prerequisites
pip install paramiko

## option 1. passing creds via env
export ROUTER_HOST="192.168.1.1"
export ROUTER_USER="root"
export ROUTER_PASS="YourRouterPassword"
export ROUTER_PORT="22"

python3 deploy_awgm_remote.py

## option 2. passing creds via CLI
python3 deploy_awgm_remote.py --host 192.168.1.1 --user root --password YourRouterPassword --port 22