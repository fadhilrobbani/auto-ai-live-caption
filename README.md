# Auto AI Live Caption

A lightweight, real-time live speech captioning desktop overlay for Linux (optimized for KDE Plasma Wayland and GNOME) with future cross-platform portability to Windows and macOS.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-Qt6-green.svg)
![Faster-Whisper](https://img.shields.io/badge/ASR-Faster--Whisper-orange.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

---

## ✨ Features

- 🔊 **Desktop Audio & Microphone Capture**: Effortlessly caption YouTube videos, online lectures, meetings (Zoom, Google Meet, Teams), podcasts, or your own microphone in real time.
- ⚡ **Pluggable Model Architecture**:
  - **100% Offline Default**: Uses a pre-quantized INT8 `faster-whisper-base` model on your CPU with zero internet connection required.
  - **Ultra-fast Cloud APIs**: Seamlessly toggle to **Groq Whisper** (`whisper-large-v3-turbo`, <200ms latency) or **OpenAI Whisper** via API key.
  - **Custom Models**: Load custom local Whisper models (tiny, small, medium, large-v3, or custom paths).
- 🪟 **Modern Glassmorphism Floating Overlay**:
  - Frameless, translucent glass styling that floats above all windows (`Always on Top`).
  - **Clean Mode (`▲ Clean` / `▼ Controls`)**: One-click toggle to hide all buttons for a distraction-free, pure text caption view.
  - **Full 0% Opacity Support**: Go completely transparent (cinema-style subtitles) with built-in high-contrast black outline text shadows that remain crisp over bright or pure-white backgrounds.
  - **Native Dragging**: Smooth window repositioning anywhere across multi-monitor setups (Wayland `startSystemMove` and X11).
  - Quick action toolbar: **Pause / Resume**, **Desktop / Mic toggle**, **Font sizing (+ / -)**, **🧹 Clear**, and **⚙ Settings**.
  - **Auto-Following Audio**: Automatically tracks active system outputs (e.g. plugging/unplugging Bluetooth TWS earbuds or USB DACs) without restarting.
- 🧠 **Smart Speech Processing**:
  - Neural **Silero VAD** eliminates silence and prevents Whisper hallucinations.
  - **Text Stabilizer**: Reconciles rolling committed history with in-flight tentative words without jitter or duplicate words.
- 🌐 **Multilingual Support**: Supports Auto-detection, Indonesian (`id`), English (`en`), Japanese (`ja`), Spanish (`es`), and 90+ Whisper languages.

---

## 🚀 Quick Start

### 1. Prerequisites
The application utilizes your pre-installed Python virtual environment and offline Whisper model:
- **Python Virtual Environment**: `/home/fadhilrobbani/.local/share/venvs/speech-processing/bin/python`
- **Default Offline Model**: `/home/fadhilrobbani/.local/share/models/whisper/faster-whisper-base`

### 2. Launching the App
Run directly with Python:
```bash
/home/fadhilrobbani/.local/share/venvs/speech-processing/bin/python main.py
```
Or with specific CLI arguments:
```bash
# Capture from microphone in Indonesian:
./main.py --source mic --language id

# Capture desktop audio with larger font size:
./main.py --source desktop --font-size 22 --opacity 0.90
```

### 3. Desktop Application Menu Launcher
Copy the desktop launcher file to your local applications directory:
```bash
cp auto-ai-live-caption.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

---

## 🛠️ Project Structure

```
auto-ai-live-caption/
├── README.md                   # User guide & documentation
├── main.py                     # Application entry point & Qt lifecycle manager
├── auto-ai-live-caption.desktop# Desktop menu launcher
├── core/                       # Decoupled backend business logic
│   ├── audio/
│   │   ├── device_manager.py   # PulseAudio/PipeWire monitor & mic detection
│   │   └── streamer.py         # 16kHz mono float32 continuous audio stream
│   ├── vad/
│   │   └── processor.py        # Silero VAD speech segmenter (1.5s - 2.5s)
│   ├── models/
│   │   ├── base.py             # BaseCaptionEngine & CaptionResult contract
│   │   ├── faster_whisper.py   # Offline Faster-Whisper local engine
│   │   ├── groq_api.py         # Groq Whisper Cloud API engine (<200ms)
│   │   ├── openai_api.py       # OpenAI Whisper Cloud API engine
│   │   └── registry.py         # Dynamic model factory & manager
│   ├── stabilizer/
│   │   └── text_stabilizer.py  # Text reconciler & duplicate remover
│   └── config/
│       └── manager.py          # Persistent JSON config (~/.config/auto-ai-live-caption)
├── ui/                         # PySide6 Presentation Layer
│   ├── overlay.py              # Transparent draggable floating caption window
│   ├── controls.py             # Hover toolbar (pause, source, font, settings)
│   ├── settings_dialog.py      # Preferences modal (models, keys, audio devices)
│   └── worker.py               # Dedicated QThread pipeline orchestrator
└── tests/                      # Automated unit & integration tests
    ├── test_audio.py
    ├── test_vad.py
    ├── test_models.py
    ├── test_stabilizer.py
    ├── test_config.py
    ├── test_ui.py
    └── test_integration.py
```

---

## 🧪 Running Automated Tests

Run the complete test suite across all modules:
```bash
/home/fadhilrobbani/.local/share/venvs/speech-processing/bin/python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 📄 License
Clean-room implementation licensed under the **MIT License**. No GPL-encumbered code reused.
