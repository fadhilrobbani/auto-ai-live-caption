#!/usr/bin/env bash
# Build script to generate standalone AppImage for Auto AI Live Caption
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/appimage"
APPDIR="${BUILD_DIR}/AppDir"
OUTPUT_DIR="${ROOT_DIR}/dist"

echo "=== Building Auto AI Live Caption AppImage ==="

mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/lib"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/metainfo"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${OUTPUT_DIR}"

# 1. Install or copy binaries
if [ -d "${ROOT_DIR}/dist/auto-ai-live-caption" ]; then
  echo "--> Copying PyInstaller standalone distribution to AppDir..."
  cp -r "${ROOT_DIR}/dist/auto-ai-live-caption/"* "${APPDIR}/usr/bin/"
else
  echo "--> PyInstaller bundle not found. Building with pyinstaller spec..."
  python3 -m PyInstaller --clean -y "${ROOT_DIR}/packaging/pyinstaller/auto-ai-live-caption.spec"
  cp -r "${ROOT_DIR}/dist/auto-ai-live-caption/"* "${APPDIR}/usr/bin/"
fi

# 2. Copy AppRun, Desktop entry, and Icons
echo "--> Installing AppRun, desktop metadata, and icons..."
cp "${SCRIPT_DIR}/AppRun" "${APPDIR}/AppRun"
chmod +x "${APPDIR}/AppRun"

cp "${ROOT_DIR}/packaging/flatpak/io.github.fadhilrobbani.AutoAILiveCaption.desktop" \
   "${APPDIR}/io.github.fadhilrobbani.AutoAILiveCaption.desktop"
cp "${ROOT_DIR}/packaging/flatpak/io.github.fadhilrobbani.AutoAILiveCaption.desktop" \
   "${APPDIR}/usr/share/applications/io.github.fadhilrobbani.AutoAILiveCaption.desktop"

cp "${ROOT_DIR}/packaging/flatpak/io.github.fadhilrobbani.AutoAILiveCaption.metainfo.xml" \
   "${APPDIR}/usr/share/metainfo/io.github.fadhilrobbani.AutoAILiveCaption.metainfo.xml"

cp "${ROOT_DIR}/packaging/assets/io.github.fadhilrobbani.AutoAILiveCaption.svg" \
   "${APPDIR}/io.github.fadhilrobbani.AutoAILiveCaption.svg"
cp "${ROOT_DIR}/packaging/assets/io.github.fadhilrobbani.AutoAILiveCaption.svg" \
   "${APPDIR}/usr/share/icons/hicolor/scalable/apps/io.github.fadhilrobbani.AutoAILiveCaption.svg"

# Symlink .DirIcon for desktop managers
ln -sf "io.github.fadhilrobbani.AutoAILiveCaption.svg" "${APPDIR}/.DirIcon"

# 3. Locate or download appimagetool
APPIMAGETOOL=""
if command -v appimagetool >/dev/null 2>&1; then
  APPIMAGETOOL="appimagetool"
elif [ -f "${BUILD_DIR}/appimagetool" ]; then
  APPIMAGETOOL="${BUILD_DIR}/appimagetool"
else
  mkdir -p "${BUILD_DIR}"
  echo "--> Downloading appimagetool..."
  curl -sfL -o "${BUILD_DIR}/appimagetool" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "${BUILD_DIR}/appimagetool"
  APPIMAGETOOL="${BUILD_DIR}/appimagetool"
fi

# 4. Generate AppImage
echo "--> Generating AppImage..."
# Use --appimage-extract-and-run if appimagetool is an AppImage and FUSE is unavailable
if [ "${APPIMAGETOOL}" != "appimagetool" ]; then
  ARCH=x86_64 "${APPIMAGETOOL}" --appimage-extract-and-run "${APPDIR}" "${OUTPUT_DIR}/AutoAILiveCaption-1.0.0-x86_64.AppImage" || \
  ARCH=x86_64 "${APPIMAGETOOL}" "${APPDIR}" "${OUTPUT_DIR}/AutoAILiveCaption-1.0.0-x86_64.AppImage"
else
  ARCH=x86_64 "${APPIMAGETOOL}" "${APPDIR}" "${OUTPUT_DIR}/AutoAILiveCaption-1.0.0-x86_64.AppImage"
fi

echo "=== Successfully created: ${OUTPUT_DIR}/AutoAILiveCaption-1.0.0-x86_64.AppImage ==="
