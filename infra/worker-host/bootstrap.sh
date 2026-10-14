#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 VPS as the 148AI build worker host.
#
#   sudo bash bootstrap.sh <GITHUB_RUNNER_REGISTRATION_TOKEN>
#   or, as Hetzner "Cloud config / user data": set RUNNER_TOKEN=... above this script.
#
# Installs Docker, a firewall that only allows SSH in, a self-hosted GitHub
# Actions runner (label: omni-worker) that deploys this repository, and a
# host-generated sandbox secret. No inbound port other than SSH is opened:
# the runner and the worker only make outbound connections.
set -euo pipefail

REPO_URL="https://github.com/Shayfly/desktop-tutorial"
TOKEN="${1:-${RUNNER_TOKEN:-}}"
[ -n "$TOKEN" ] || { echo "usage: bootstrap.sh <runner registration token>"; exit 1; }
RUNNER_USER=omni

export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q ca-certificates curl jq ufw unattended-upgrades docker.io docker-compose-v2
systemctl enable --now docker

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable

id "$RUNNER_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$RUNNER_USER"
usermod -aG docker "$RUNNER_USER"

install -d -m 700 -o "$RUNNER_USER" /etc/omni
if [ ! -s /etc/omni/sandbox_secret ]; then
  head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > /etc/omni/sandbox_secret
  chown "$RUNNER_USER" /etc/omni/sandbox_secret
  chmod 600 /etc/omni/sandbox_secret
fi
install -d -m 755 /var/lib/omni-sandbox /var/lib/omni-sandbox/tmp
chmod 1777 /var/lib/omni-sandbox/tmp

RUNNER_DIR=/home/$RUNNER_USER/actions-runner
if [ ! -f "$RUNNER_DIR/.runner" ]; then
  VERSION=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/^v//')
  ARCH=$(uname -m); case "$ARCH" in x86_64) A=x64;; aarch64) A=arm64;; *) echo "unsupported arch $ARCH"; exit 1;; esac
  install -d -o "$RUNNER_USER" "$RUNNER_DIR"
  cd "$RUNNER_DIR"
  sudo -u "$RUNNER_USER" curl -fsSL -o runner.tgz \
    "https://github.com/actions/runner/releases/download/v${VERSION}/actions-runner-linux-${A}-${VERSION}.tar.gz"
  sudo -u "$RUNNER_USER" tar xzf runner.tgz && rm runner.tgz
  sudo -u "$RUNNER_USER" ./config.sh --unattended --url "$REPO_URL" --token "$TOKEN" \
    --name "$(hostname)" --labels omni-worker --replace
  ./svc.sh install "$RUNNER_USER"
  ./svc.sh start
fi

echo "OK: worker host ready. Push to the build branch or run the 'Deploy build worker' workflow."
