#!/bin/bash

set -e

# Renew k3s agent certificates using `k3s certificate rotate` and restart k3s-agent.
#
# Usage:
#   ./renew-k3s-agent-certs.sh <agent_host> [ssh_user] [ssh_port]
#
# Examples:
#   ./renew-k3s-agent-certs.sh 10.0.0.10
#   ./renew-k3s-agent-certs.sh 10.0.0.10 root 22
#   ./renew-k3s-agent-certs.sh "10.0.0.10 10.0.0.11 10.0.0.12"

AGENT_HOSTS="${1:?Usage: $0 <agent_host(s)> [ssh_user] [ssh_port]}"
SSH_USER="${2:-root}"
SSH_PORT="${3:-22}"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -p ${SSH_PORT}"

renew_agent_certs() {
    local host="$1"
    echo "=========================================="
    echo "Processing k3s-agent on: ${host}"
    echo "=========================================="

    ssh ${SSH_OPTS} "${SSH_USER}@${host}" bash <<'REMOTE_SCRIPT'
set -e

echo "[1/3] Checking k3s-agent status..."
if ! systemctl is-enabled k3s-agent &>/dev/null; then
    echo "ERROR: k3s-agent service not found on this host, skipping."
    exit 1
fi

echo "[2/4] Stopping k3s-agent..."
systemctl stop k3s-agent

echo "[3/4] Rotating k3s agent certificates..."
k3s certificate rotate

echo "[4/4] Starting k3s-agent..."
systemctl start k3s-agent

sleep 5
if systemctl is-active k3s-agent &>/dev/null; then
    echo "SUCCESS: k3s-agent is running on $(hostname)"
else
    echo "ERROR: k3s-agent failed to start. Check: journalctl -u k3s-agent -n 50"
    exit 1
fi
REMOTE_SCRIPT

    echo ""
}

# Process each host
for host in ${AGENT_HOSTS}; do
    renew_agent_certs "${host}"
done

echo "All done."
