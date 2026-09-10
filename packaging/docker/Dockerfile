FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system build tools, packaging utilities, and runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    curl \
    wget \
    file \
    patchelf \
    desktop-file-utils \
    ca-certificates \
    tar \
    gzip \
    xz-utils \
    binutils \
    libpulse0 \
    libasound2 \
    libgl1 \
    libegl1 \
    libxkbcommon0 \
    libdbus-1-3 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libfontconfig1 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Install nFPM for .deb and .rpm packaging
RUN NFPM_VERSION="2.41.3" && \
    curl -sfL "https://github.com/goreleaser/nfpm/releases/download/v${NFPM_VERSION}/nfpm_${NFPM_VERSION}_Linux_x86_64.tar.gz" | tar -xz -C /usr/local/bin nfpm && \
    chmod +x /usr/local/bin/nfpm

# Install appimagetool (pre-extracted to run without FUSE in containers)
RUN mkdir -p /opt/appimagetool && \
    curl -sfL "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage" -o /tmp/appimagetool.AppImage && \
    chmod +x /tmp/appimagetool.AppImage && \
    cd /opt/appimagetool && \
    /tmp/appimagetool.AppImage --appimage-extract && \
    rm /tmp/appimagetool.AppImage && \
    ln -s /opt/appimagetool/squashfs-root/AppRun /usr/local/bin/appimagetool

# Upgrade pip and pre-install build and application dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir \
    pyinstaller>=6.10.0 \
    PySide6>=6.6.0 \
    faster-whisper>=1.0.0 \
    ctranslate2>=4.0.0 \
    onnxruntime>=1.16.0 \
    numpy>=1.24.0 \
    scipy>=1.10.0 \
    soundfile>=0.12.0 \
    httpx>=0.25.0 \
    huggingface-hub>=0.20.0

WORKDIR /workspace
