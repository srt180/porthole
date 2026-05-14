#!/usr/bin/env bash

set -euo pipefail

REPO="${PORTHOLE_REPO:-srt180/porthole}"
BIN_NAME="porthole"
BIN_DIR="${HOME}/.local/bin"
VERSION="latest"

usage() {
  cat <<'EOF'
Install the Porthole prebuilt binary from GitHub Releases.

Usage:
  install.sh [--version v0.1.2] [--bin-dir /path/to/bin] [--repo owner/name]

Options:
  --version  Release tag to install. Defaults to the latest release.
  --bin-dir  Directory where the binary will be installed. Defaults to ~/.local/bin.
  --repo     GitHub repository in owner/name form. Defaults to srt180/porthole.
  -h, --help Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    --bin-dir)
      BIN_DIR="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${VERSION}" || -z "${BIN_DIR}" || -z "${REPO}" ]]; then
  echo "Missing required argument value." >&2
  usage >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but was not found." >&2
  exit 1
fi

if ! command -v tar >/dev/null 2>&1; then
  echo "tar is required but was not found." >&2
  exit 1
fi

OS="$(uname -s)"
ARCH="$(uname -m)"

case "${OS}" in
  Darwin)
    PLATFORM="darwin"
    ;;
  Linux)
    PLATFORM="linux"
    ;;
  *)
    echo "Unsupported operating system: ${OS}" >&2
    exit 1
    ;;
esac

case "${ARCH}" in
  x86_64|amd64)
    TARGET_ARCH="x86_64"
    ;;
  arm64|aarch64)
    TARGET_ARCH="arm64"
    ;;
  *)
    echo "Unsupported architecture: ${ARCH}" >&2
    exit 1
    ;;
esac

ASSET_NAME="${BIN_NAME}-${PLATFORM}-${TARGET_ARCH}.tar.gz"

if [[ "${VERSION}" == "latest" ]]; then
  DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${ASSET_NAME}"
else
  VERSION="${VERSION#refs/tags/}"
  if [[ "${VERSION}" != v* ]]; then
    VERSION="v${VERSION}"
  fi
  DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${ASSET_NAME}"
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

ARCHIVE_PATH="${TMP_DIR}/${ASSET_NAME}"

echo "Downloading ${ASSET_NAME} from ${REPO}..."
curl -fsSL "${DOWNLOAD_URL}" -o "${ARCHIVE_PATH}"

mkdir -p "${BIN_DIR}"
tar -xzf "${ARCHIVE_PATH}" -C "${TMP_DIR}"
install -m 0755 "${TMP_DIR}/${BIN_NAME}" "${BIN_DIR}/${BIN_NAME}"

echo "Installed ${BIN_NAME} to ${BIN_DIR}/${BIN_NAME}"
echo "Make sure ${BIN_DIR} is in your PATH."
