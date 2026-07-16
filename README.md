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

- [main.py](https://github.com/NordikVibe/nova-assistant/blob/main/main.py) — runtime entrypoint (audio capture + STT loop)
- [Managers.py](https://github.com/NordikVibe/nova-assistant/blob/main/Managers.py) — container for all classes
- [threads.py](https://github.com/NordikVibe/nova-assistant/blob/main/threads.py) — intent confidence, audio playback, runtime TTS threads
- [system_apis/PlatformManagers.py](https://github.com/NordikVibe/nova-assistant/blob/main/system_apis/PlatformManagers.py) — platform abstraction for media and volume backends
- [telegram.py](https://github.com/NordikVibe/nova-assistant/blob/main/telegram.py) — optional Telegram bot input channel

Built-in plugins:

- `PluginSystem/Service` — activation intent
- `PluginSystem/Volume` — cross-platform volume control through system backends
- `PluginSystem/Media` — cross-platform media control through system backends
- `PluginSystem/Apps` — work with external apps

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`
- Linux or Windows

## Setup and run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. (Optional) Force preprocessing (model/hash/cache regeneration):

```bash
python main.py --config config.json --preprocess
```

`main.py` also auto-runs preprocessing when `hashsum.json` is missing or plugin YAML hashes changed.

3. Run assistant:

```bash
python main.py --config config.json
```

Optional runtime flags:

- `-d, --debug` — verbose console logs
- `-c, --config` — custom config path
- `--about` — currently declared argument in CLI parser
- `--preprocess` — force model retraining + hash/TTS cache refresh

## Configuration

Config file: [Config.json](https://github.com/NordikVibe/nova-assistant/blob/main/config.json)

Key sections:

- `TTS` — model, voice, enabled flag
- `STT` — Vosk model path
- `IntentModel` — sklearn model path
- `Audio` — input/output device names
- `Logging` — file/console log levels and path
- `Telegram` — Telegram bot enable flag and trusted users list
- `User` — user profile data used by plugins

Telegram token is read from `.env` (`TELEGRAM_API_TOKEN`). Use [example.env](https://github.com/NordikVibe/nova-assistant/blob/main/example.env) as a template.

## Plugin system docs

Plugin development guides:

- [English](https://github.com/NordikVibe/nova-assistant/blob/main/PluginSystem/dev.md)
- [Українська](https://github.com/NordikVibe/nova-assistant/blob/main/PluginSystem/devUA.md)
- [Русский](https://github.com/NordikVibe/nova-assistant/blob/main/PluginSystem/devRU.md)
