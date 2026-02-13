#!/bin/bash

set -euo pipefail

# Install/build IgH (EtherLab) EtherCAT master + libecrt from source, pinned.
#
# This script lives in the repo so the appliance can be reproduced from scratch,
# but it *does* install artifacts into the host OS:
# - /usr/local/include/ecrt.h
# - /usr/local/lib/libethercat.so / pkg-config metadata
# - /usr/local/bin/ethercat
# - /usr/local/sbin/ethercatctl
# - /etc/systemd/system/ethercat.service (from IgH install)
# - /lib/modules/$(uname -r)/ethercat/{master,devices}/ec_*.ko.xz
#
# After install, use the repo templates in systemd/ethercat-host/ to configure:
# - /etc/ethercat.conf (bind by MAC)
# - ethercat.service drop-in to force /etc/ethercat.conf

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

IGH_VERSION="${IGH_VERSION:-1.6.8}"
TARBALL_URL="https://gitlab.com/etherlab.org/ethercat/-/archive/${IGH_VERSION}/ethercat-${IGH_VERSION}.tar.gz"

BUILD_ROOT="${REPO_ROOT}/build/etherlab"
SRC_TGZ="${BUILD_ROOT}/ethercat-${IGH_VERSION}.tar.gz"
SRC_DIR="${BUILD_ROOT}/ethercat-${IGH_VERSION}"

echo "== IgH EtherCAT master install =="
echo "Repo: ${REPO_ROOT}"
echo "Version: ${IGH_VERSION}"
echo "Build dir: ${SRC_DIR}"
echo ""

echo "1) Installing build dependencies..."
sudo apt-get update
sudo apt-get install -y \
  git build-essential autoconf automake libtool pkg-config bison flex

echo "2) Installing kernel headers for running kernel..."
sudo apt-get install -y "linux-headers-$(uname -r)"

echo "3) Seeding RevPi headers for external module builds (best-effort)..."
kver="$(uname -r)"
hdrdir="/usr/src/linux-headers-${kver}"
if [[ -d "${hdrdir}" && -f "/boot/config-${kver}" ]]; then
  sudo cp "/boot/config-${kver}" "${hdrdir}/.config" || true
  # Some vendor header trees lack include/config/auto.conf.cmd (required by some autotools checks).
  sudo bash -c "printf '%s\n' '# generated placeholder for external module builds' > '${hdrdir}/include/config/auto.conf.cmd'" || true
  if [[ -f "${hdrdir}/include/config/auto.conf" ]]; then
    sudo touch -r "${hdrdir}/include/config/auto.conf" "${hdrdir}/.config" || true
  fi
  if [[ -f "${hdrdir}/include/generated/autoconf.h" && ! -f "${hdrdir}/include/generated/autoconf.h.cmd" ]]; then
    sudo bash -c "printf '%s\n' '# placeholder' > '${hdrdir}/include/generated/autoconf.h.cmd'" || true
  fi
fi

echo "4) Downloading source tarball..."
mkdir -p "${BUILD_ROOT}"
curl -L --retry 5 --retry-delay 5 --connect-timeout 20 -o "${SRC_TGZ}" "${TARBALL_URL}"

echo "5) Extracting..."
rm -rf "${SRC_DIR}"
tar -xzf "${SRC_TGZ}" -C "${BUILD_ROOT}"

echo "6) Configuring..."
cd "${SRC_DIR}"
./bootstrap
./configure \
  --enable-kernel \
  --enable-generic \
  --with-linux-dir="/lib/modules/$(uname -r)/build" \
  --with-systemdsystemunitdir=/etc/systemd/system \
  --disable-initd

echo "7) Building userspace + libecrt..."
make -j"$(nproc)"
echo "8) Installing userspace..."
sudo make install
sudo ldconfig

echo "9) Building + installing kernel modules..."
make modules -j"$(nproc)"
sudo make modules_install
sudo depmod -a || true

echo ""
echo "Installed."
echo "Next:"
echo "  - Configure /etc/ethercat.conf from repo template: systemd/ethercat-host/ethercat.conf"
echo "  - Install the ethercat.service drop-in from repo: systemd/ethercat-host/ethercat.service.d/10-gradient.conf"
echo "  - Then: sudo systemctl enable --now ethercat.service"

