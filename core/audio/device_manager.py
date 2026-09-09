"""
Audio Device Management & Enumeration for Linux (PulseAudio / PipeWire).
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    id: str
    name: str
    description: str
    is_monitor: bool  # True = Desktop Audio (loopback), False = Microphone
    is_default: bool


def _run_pactl_cmd(args: List[str]) -> Optional[str]:
    """Execute a pactl command safely and return stripped stdout or None."""
    try:
        res = subprocess.run(
            ["pactl"] + args,
            capture_output=True,
            text=True,
            check=True,
            timeout=3.0,
        )
        return res.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
        logger.warning("Failed to run pactl with args %s: %s", args, e)
        return None


def get_default_sink_name() -> Optional[str]:
    """Retrieve the current default PulseAudio / PipeWire playback sink."""
    return _run_pactl_cmd(["get-default-sink"])


def get_default_source_name() -> Optional[str]:
    """Retrieve the current default PulseAudio / PipeWire capture source."""
    return _run_pactl_cmd(["get-default-source"])


def list_audio_devices() -> List[AudioDevice]:
    """
    Enumerate all available audio sources, distinguishing between
    Desktop Audio monitor sinks (loopback) and Microphones.
    Includes dynamic System Default auto-switching entries at the top.
    """
    default_sink = get_default_sink_name()
    default_source = get_default_source_name()

    devices: List[AudioDevice] = [
        AudioDevice(
            id="@DEFAULT_MONITOR@",
            name="@DEFAULT_MONITOR@",
            description=f"✨ Auto (System Audio Output) [Currently: {default_sink or 'Default'}]",
            is_monitor=True,
            is_default=True,
        ),
        AudioDevice(
            id="@DEFAULT_SOURCE@",
            name="@DEFAULT_SOURCE@",
            description=f"✨ Auto (System Microphone) [Currently: {default_source or 'Default'}]",
            is_monitor=False,
            is_default=True,
        ),
    ]

    # Try JSON mode first (supported in modern pactl)
    json_output = _run_pactl_cmd(["-f", "json", "list", "sources"])
    if json_output:
        try:
            raw_sources = json.loads(json_output)
            for item in raw_sources:
                name = item.get("name", "")
                if not name:
                    continue
                
                desc = item.get("description", "")
                props = item.get("properties", {})
                if not desc:
                    desc = props.get("node.description") or props.get("device.description") or name

                # Identify if this is a monitor source (Desktop Audio)
                is_monitor = (
                    name.endswith(".monitor")
                    or props.get("device.class") == "monitor"
                    or "monitor" in props.get("media.class", "").lower()
                )

                # Check if it is default
                is_def = False
                if is_monitor:
                    if default_sink and name.startswith(default_sink):
                        is_def = True
                else:
                    if default_source and name == default_source:
                        is_def = True

                devices.append(
                    AudioDevice(
                        id=name,
                        name=name,
                        description=desc,
                        is_monitor=is_monitor,
                        is_default=is_def,
                    )
                )
            if len(devices) > 2:
                return devices
        except json.JSONDecodeError as err:
            logger.warning("Failed to parse pactl JSON: %s", err)

    # Fallback to plain text parsing if JSON is not available
    text_output = _run_pactl_cmd(["list", "short", "sources"])
    if text_output:
        for line in text_output.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                name = parts[1]
                is_monitor = name.endswith(".monitor")
                is_def = False
                if is_monitor:
                    if default_sink and name.startswith(default_sink):
                        is_def = True
                else:
                    if default_source and name == default_source:
                        is_def = True
                
                desc = "Desktop Audio (Monitor)" if is_monitor else "Microphone"
                devices.append(
                    AudioDevice(
                        id=name,
                        name=name,
                        description=f"{desc} [{name}]",
                        is_monitor=is_monitor,
                        is_default=is_def,
                    )
                )

    return devices


def get_default_device(monitor: bool = True) -> AudioDevice:
    """
    Get the default audio device for either desktop loopback (monitor=True)
    or microphone input (monitor=False).
    Returns dynamic auto-detect devices by default.
    """
    if monitor:
        def_sink = get_default_sink_name() or "Default"
        return AudioDevice(
            id="@DEFAULT_MONITOR@",
            name="@DEFAULT_MONITOR@",
            description=f"✨ Auto (System Audio Output) [Currently: {def_sink}]",
            is_monitor=True,
            is_default=True,
        )
    else:
        def_src = get_default_source_name() or "Default"
        return AudioDevice(
            id="@DEFAULT_SOURCE@",
            name="@DEFAULT_SOURCE@",
            description=f"✨ Auto (System Microphone) [Currently: {def_src}]",
            is_monitor=False,
            is_default=True,
        )
