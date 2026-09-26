set -e
echo '[1/4] Checking Entware (opkg)...'
if ! command -v opkg >/dev/null 2>&1; then echo '[ERROR] opkg not found!'; exit 1; fi
echo '[2/4] Updating package manager...'
opkg update
echo '[3/4] Downloading AWG Manager installer...'
INSTALLER_TMP="$(mktemp)"
trap 'rm -f "$INSTALLER_TMP"' EXIT
curl -fsSL -o "$INSTALLER_TMP" '__INSTALLER_URL__'
echo '[4/4] Running AWG Manager installer...'
sh "$INSTALLER_TMP"
