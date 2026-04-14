#!/bin/bash

set -e

# Renew k3s server (control plane) certificates using `k3s certificate rotate`.
# Ensures CATTLE_NEW_SIGNED_CERT_EXPIRATION_DAYS is set so new certs are valid for 10 years.
#
# Usage:
#   ./renew-k3s-server-certs.sh <server_host> [ssh_user] [ssh_port]
#
# Examples:
#   ./renew-k3s-server-certs.sh 10.0.0.1
#   ./renew-k3s-server-certs.sh 10.0.0.1 root 22
#   ./renew-k3s-server-certs.sh "10.0.0.1 10.0.0.2 10.0.0.3"

SERVER_HOSTS="${1:?Usage: $0 <server_host(s)> [ssh_user] [ssh_port]}"
SSH_USER="${2:-root}"
SSH_PORT="${3:-22}"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -p ${SSH_PORT}"

renew_server_certs() {
    local host="$1"
    echo "=========================================="
    echo "Processing k3s server on: ${host}"
    echo "=========================================="

    ssh ${SSH_OPTS} "${SSH_USER}@${host}" bash <<'REMOTE_SCRIPT'
set -e

K3S_SERVICE_ENV="/etc/systemd/system/k3s.service.env"

echo "[1/5] Checking k3s service status..."
if ! systemctl is-enabled k3s &>/dev/null; then
    echo "ERROR: k3s service not found on this host, skipping."
    exit 1
fi

echo "[2/5] Ensuring CATTLE_NEW_SIGNED_CERT_EXPIRATION_DAYS=3650 in ${K3S_SERVICE_ENV}..."
if [ -f "${K3S_SERVICE_ENV}" ]; then
    if grep -q "^CATTLE_NEW_SIGNED_CERT_EXPIRATION_DAYS=" "${K3S_SERVICE_ENV}"; then
        sed -i 's/^CATTLE_NEW_SIGNED_CERT_EXPIRATION_DAYS=.*/CATTLE_NEW_SIGNED_CERT_EXPIRATION_DAYS=3650/' "${K3S_SERVICE_ENV}"
    else
        echo "CATTLE_NEW_SIGNED_CERT_EXPIRATION_DAYS=3650" >> "${K3S_SERVICE_ENV}"
    fi
else
    echo "CATTLE_NEW_SIGNED_CERT_EXPIRATION_DAYS=3650" > "${K3S_SERVICE_ENV}"
fi
echo "  $(grep CATTLE_NEW_SIGNED_CERT_EXPIRATION_DAYS ${K3S_SERVICE_ENV})"

echo "[3/5] Stopping k3s..."
systemctl stop k3s

echo "[4/5] Rotating k3s server certificates..."
k3s certificate rotate

echo "[5/5] Starting k3s..."
systemctl daemon-reload
systemctl start k3s

sleep 5
if systemctl is-active k3s &>/dev/null; then
    echo "SUCCESS: k3s server is running on $(hostname)"
else
    echo "ERROR: k3s failed to start. Check: journalctl -u k3s -n 50"
    exit 1
fi
REMOTE_SCRIPT

    echo ""
}

# Process each host
for host in ${SERVER_HOSTS}; do
    renew_server_certs "${host}"
done

echo "All done."
