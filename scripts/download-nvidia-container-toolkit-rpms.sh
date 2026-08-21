#!/usr/bin/env bash
# Download offline RPMs for NVIDIA Container Toolkit and yunion-hami.
# NVIDIA toolkit default version matches onecloud/roles/utils/ai-env (1.17.8-1).

set -euo pipefail

NCTK_VERSION="1.17.8-1"
HAMI_VERSION="1.0.0-1"
ARCH="x86_64"
OUTPUT_DIR="nvidia-container-toolkit-rpms"
FORCE=0

NCTK_BASE_URL="https://nvidia.github.io/libnvidia-container/stable/rpm"
HAMI_BASE_URL="https://iso.yunion.cn/rpm/8"

NCTK_PACKAGES=(
  libnvidia-container1
  libnvidia-container-tools
  nvidia-container-toolkit-base
  nvidia-container-toolkit
)

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Download NVIDIA Container Toolkit and yunion-hami RPMs for offline installation.

Options:
  -v, --version VERSION        NVIDIA Container Toolkit version (default: ${NCTK_VERSION})
      --hami-version VERSION   yunion-hami version (default: ${HAMI_VERSION})
  -a, --arch ARCH              Architecture: x86_64 or aarch64 (default: ${ARCH})
  -o, --output DIR             Output directory (default: ${OUTPUT_DIR})
      --force                  Re-download even if file already exists
  -h, --help                   Show this help

Examples:
  $(basename "$0")
  $(basename "$0") -o /tmp/nvidia-ctk
  $(basename "$0") -v 1.17.8-1 -a aarch64
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--version)
      NCTK_VERSION="${2:?missing value for $1}"
      shift 2
      ;;
    --hami-version)
      HAMI_VERSION="${2:?missing value for $1}"
      shift 2
      ;;
    -a|--arch)
      ARCH="${2:?missing value for $1}"
      shift 2
      ;;
    -o|--output)
      OUTPUT_DIR="${2:?missing value for $1}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$ARCH" in
  x86_64|aarch64) ;;
  *)
    echo "Unsupported arch: $ARCH (use x86_64 or aarch64)" >&2
    exit 1
    ;;
esac

download() {
  local url="$1"
  local dest="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 --retry-delay 2 -o "$dest" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$dest" "$url"
  else
    echo "Neither curl nor wget found" >&2
    exit 1
  fi
}

download_one() {
  local url="$1"
  local filename="$2"
  local dest="${OUTPUT_DIR}/${filename}"

  if [[ -f "$dest" && "$FORCE" -eq 0 ]]; then
    echo "Skip (exists): ${filename}"
    return 0
  fi

  echo "Downloading: ${filename}"
  local tmp="${dest}.partial"
  if ! download "$url" "$tmp"; then
    rm -f "$tmp"
    echo "Failed to download: ${url}" >&2
    exit 1
  fi
  mv "$tmp" "$dest"
}

mkdir -p "$OUTPUT_DIR"
NCTK_REPO_URL="${NCTK_BASE_URL}/${ARCH}"
HAMI_URL="${HAMI_BASE_URL}/${ARCH}/Packages/yunion-hami-${HAMI_VERSION}.${ARCH}.rpm"

echo "NCTK version : ${NCTK_VERSION}"
echo "HAMI version : ${HAMI_VERSION}"
echo "Arch         : ${ARCH}"
echo "Output       : ${OUTPUT_DIR}"
echo "NCTK source  : ${NCTK_REPO_URL}"
echo "HAMI source  : ${HAMI_BASE_URL}/${ARCH}/Packages/"
echo

for pkg in "${NCTK_PACKAGES[@]}"; do
  filename="${pkg}-${NCTK_VERSION}.${ARCH}.rpm"
  download_one "${NCTK_REPO_URL}/${filename}" "${filename}"
done

download_one "${HAMI_URL}" "yunion-hami-${HAMI_VERSION}.${ARCH}.rpm"

echo
echo "Downloaded RPMs:"
ls -lh "${OUTPUT_DIR}"/*.rpm
