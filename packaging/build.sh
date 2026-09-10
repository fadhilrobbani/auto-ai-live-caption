#!/usr/bin/env bash
# ==============================================================================
# Unified Build & Packaging CLI for Auto AI Live Caption
# Supports: Flatpak, AppImage, Debian (.deb), Red Hat (.rpm), and Python Wheels
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/build"

mkdir -p "${DIST_DIR}" "${BUILD_DIR}"

PYTHON="${PYTHON:-python3}"
IN_CONTAINER=false

# Check if running in container flag is passed
for arg in "$@"; do
  if [ "$arg" = "--in-container" ]; then
    IN_CONTAINER=true
    PYTHON="python3"
  fi
done

if [ "$IN_CONTAINER" = false ]; then
  if [ -f "/home/fadhilrobbani/.local/share/venvs/speech-processing/bin/python" ]; then
    PYTHON="/home/fadhilrobbani/.local/share/venvs/speech-processing/bin/python"
  fi
fi

print_header() {
  echo ""
  echo "===================================================================="
  echo "  Auto AI Live Caption — Build & Packaging System"
  echo "===================================================================="
  echo ""
}

show_help() {
  print_header
  echo "Usage: ./packaging/build.sh <target> [options]"
  echo ""
  echo "Standard Targets (Host environment):"
  echo "  appimage  Build standalone portable AppImage (.AppImage)"
  echo "  deb       Build Debian / Ubuntu package (.deb)"
  echo "  rpm       Build Fedora / RHEL / openSUSE package (.rpm)"
  echo "  flatpak   Build Flatpak bundle (requires flatpak-builder)"
  echo "  binary    Build standalone directory bundle with PyInstaller"
  echo "  wheel     Build standard Python wheel (.whl)"
  echo "  all       Build all portable distributions (binary, appimage, deb, rpm, wheel)"
  echo ""
  echo "Containerized Targets (Isolated Docker / Podman build, cross-distro glibc):"
  echo "  docker <target>   Run build target inside Ubuntu 22.04 Docker container"
  echo "                    Example: ./packaging/build.sh docker appimage"
  echo "                             ./packaging/build.sh docker deb"
  echo "                             ./packaging/build.sh docker all"
  echo ""
}

check_pyinstaller() {
  if ! ${PYTHON} -c "import PyInstaller" >/dev/null 2>&1; then
    echo "===================================================================="
    echo "Notice: 'PyInstaller' is not installed in: ${PYTHON}"
    echo "===================================================================="
    echo "To build without polluting your local system, use isolated Docker:"
    echo "  ./packaging/build.sh docker ${TARGET}"
    echo ""
    echo "Alternatively, install PyInstaller into your local environment:"
    echo "  ${PYTHON} -m pip install pyinstaller"
    echo "===================================================================="
    exit 1
  fi
}

build_binary() {
  check_pyinstaller
  echo ">>> [1/1] Building PyInstaller standalone distribution..."
  cd "${ROOT_DIR}"
  ${PYTHON} -m PyInstaller --clean -y "${SCRIPT_DIR}/pyinstaller/auto-ai-live-caption.spec"
  echo "✓ Standalone binary created at: ${DIST_DIR}/auto-ai-live-caption/"
}

build_appimage() {
  echo ">>> Building AppImage..."
  build_binary
  "${SCRIPT_DIR}/appimage/build_appimage.sh"
}

get_nfpm() {
  if command -v nfpm >/dev/null 2>&1; then
    echo "nfpm"
  elif [ -f "${BUILD_DIR}/nfpm" ]; then
    echo "${BUILD_DIR}/nfpm"
  else
    echo ">>> Downloading nFPM packaging tool..." >&2
    local NFPM_VERSION="2.41.3"
    curl -sfL "https://github.com/goreleaser/nfpm/releases/download/v${NFPM_VERSION}/nfpm_${NFPM_VERSION}_Linux_x86_64.tar.gz" | tar -xz -C "${BUILD_DIR}" nfpm
    chmod +x "${BUILD_DIR}/nfpm"
    echo "${BUILD_DIR}/nfpm"
  fi
}

build_deb() {
  echo ">>> Building Debian/Ubuntu package (.deb)..."
  if [ ! -d "${DIST_DIR}/auto-ai-live-caption" ]; then
    build_binary
  fi
  NFPM_BIN=$(get_nfpm)
  cd "${SCRIPT_DIR}/nfpm"
  ${NFPM_BIN} package --config nfpm.yaml --packager deb --target "${DIST_DIR}/auto-ai-live-caption_1.0.0_amd64.deb"
  echo "✓ .deb package created at: ${DIST_DIR}/auto-ai-live-caption_1.0.0_amd64.deb"
}

build_rpm() {
  echo ">>> Building Red Hat/Fedora package (.rpm)..."
  if [ ! -d "${DIST_DIR}/auto-ai-live-caption" ]; then
    build_binary
  fi
  NFPM_BIN=$(get_nfpm)
  cd "${SCRIPT_DIR}/nfpm"
  ${NFPM_BIN} package --config nfpm.yaml --packager rpm --target "${DIST_DIR}/auto-ai-live-caption-1.0.0-1.x86_64.rpm"
  echo "✓ .rpm package created at: ${DIST_DIR}/auto-ai-live-caption-1.0.0-1.x86_64.rpm"
}

build_wheel() {
  echo ">>> Building Python wheel..."
  cd "${ROOT_DIR}"
  ${PYTHON} -m pip wheel --no-deps -w "${DIST_DIR}" .
  echo "✓ Wheel created at: ${DIST_DIR}/"
}

build_flatpak() {
  echo ">>> Building Flatpak package..."
  if ! command -v flatpak-builder >/dev/null 2>&1; then
    echo "Error: 'flatpak-builder' is not installed."
    echo "Install it via your package manager:"
    echo "  Arch/CachyOS: sudo pacman -S flatpak-builder"
    echo "  Fedora:       sudo dnf install flatpak-builder"
    echo "  Ubuntu:       sudo apt install flatpak-builder"
    exit 1
  fi

  cd "${ROOT_DIR}"
  flatpak-builder --force-clean \
    --repo="${BUILD_DIR}/flatpak-repo" \
    "${BUILD_DIR}/flatpak-app" \
    "${SCRIPT_DIR}/flatpak/io.github.fadhilrobbani.AutoAILiveCaption.yaml"

  flatpak build-bundle "${BUILD_DIR}/flatpak-repo" \
    "${DIST_DIR}/AutoAILiveCaption.flatpak" \
    io.github.fadhilrobbani.AutoAILiveCaption

  echo "✓ Flatpak bundle created at: ${DIST_DIR}/AutoAILiveCaption.flatpak"
}

run_in_docker() {
  local subtarget="${1:-appimage}"
  local engine="docker"
  if ! command -v docker >/dev/null 2>&1; then
    if command -v podman >/dev/null 2>&1; then
      engine="podman"
    else
      echo "Error: Neither 'docker' nor 'podman' was found on your system."
      exit 1
    fi
  fi

  echo "===================================================================="
  echo "  Running containerized build (${engine}) for target: ${subtarget}"
  echo "===================================================================="

  # Check if image already exists
  if ! ${engine} image inspect auto-ai-live-caption-builder:latest >/dev/null 2>&1; then
    echo ">>> Building Docker builder image (auto-ai-live-caption-builder:latest)..."
    ${engine} build -t auto-ai-live-caption-builder:latest -f "${SCRIPT_DIR}/docker/Dockerfile" "${ROOT_DIR}"
  fi

  echo ">>> Launching container with volume mount..."
  ${engine} run --rm \
    --user "$(id -u):$(id -g)" \
    -v "${ROOT_DIR}:/workspace" \
    -w /workspace \
    -e HOME=/tmp \
    auto-ai-live-caption-builder:latest \
    ./packaging/build.sh "${subtarget}" --in-container

  echo ""
  echo "✓ Containerized build completed successfully!"
  echo "Artifacts are ready in: ${DIST_DIR}"
}

TARGET="${1:-help}"

# Allow flags like: ./packaging/build.sh appimage --docker
if [ "$2" = "--docker" ]; then
  run_in_docker "${TARGET}"
  exit 0
fi

case "${TARGET}" in
  docker|--docker)
    run_in_docker "${2:-appimage}"
    ;;
  binary)
    build_binary
    ;;
  appimage)
    build_appimage
    ;;
  deb)
    build_deb
    ;;
  rpm)
    build_rpm
    ;;
  wheel)
    build_wheel
    ;;
  flatpak)
    build_flatpak
    ;;
  all)
    build_binary
    build_appimage
    build_deb
    build_rpm
    build_wheel
    echo ""
    echo "=== All packaging targets built successfully in: ${DIST_DIR} ==="
    ls -lh "${DIST_DIR}"
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    echo "Unknown target: ${TARGET}"
    show_help
    exit 1
    ;;
esac
