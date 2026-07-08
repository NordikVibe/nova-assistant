# Nova Assistant

Nova Assistant is an offline-oriented voice assistant for Linux/Windows with Vosk STT, sklearn intent classification, and a plugin-based command system.

## Current architecture

Core pipeline:

1. Microphone input (`sounddevice`) is resampled and recognized by Vosk (`main.py`).
2. Recognized text is sent to `ConfidenceQueue`.
3. `threads.confidenceThread` classifies intent via `models/model.pkl`.
4. Intent handler from plugin executes and returns optional slot data.
5. Assistant selects a response from plugin YAML and plays cached/generated audio.

Main modules:

- `/home/runner/work/nova-assistant/nova-assistant/main.py` — runtime entrypoint (audio capture + STT loop)
- `/home/runner/work/nova-assistant/nova-assistant/preprocessing.py` — intent model training, plugin hash generation, TTS cache generation
- `/home/runner/work/nova-assistant/nova-assistant/Managers.py` — config/context, plugin loading, intent registry, training manager
- `/home/runner/work/nova-assistant/nova-assistant/threads.py` — intent confidence, audio playback, runtime TTS threads

Built-in plugins:

- `PluginSystem/Service` — activation intent
- `PluginSystem/Volume` — volume control via `pactl`
- `PluginSystem/Media` — media control via `playerctl`
- `PluginSystem/Apps` — app launching (example: AyuGram)

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`
- System audio tooling used by plugins (for Linux plugins): `pactl`, `playerctl`

## Setup and run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Prepare model/hash/cache (required after plugin YAML changes):

```bash
python preprocessing.py --config config.json
```

3. Run assistant:

```bash
python main.py --config config.json
```

Optional runtime flags:

- `-d, --debug` — verbose console logs
- `-c, --config` — custom config path
- `--about` — currently declared argument in CLI parser

## Configuration

Config file: `/home/runner/work/nova-assistant/nova-assistant/config.json`

Key sections:

- `TTS` — model, voice, enabled flag
- `STT` — Vosk model path
- `IntentModel` — sklearn model path
- `Audio` — input/output device names
- `Logging` — file/console log levels and path
- `User` — user profile data used by plugins

## Plugin system docs

Plugin development guides:

- `/home/runner/work/nova-assistant/nova-assistant/PluginSystem/dev.md` (English)
- `/home/runner/work/nova-assistant/nova-assistant/PluginSystem/devUA.md` (Українська)
- `/home/runner/work/nova-assistant/nova-assistant/PluginSystem/dev.RU.md` (Русский)
