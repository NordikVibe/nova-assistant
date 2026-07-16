# Plugin Development (English)

This project loads plugins from `/home/runner/work/nova-assistant/nova-assistant/PluginSystem`.

## Plugin folder layout

Each plugin must be a directory with:

- `plugin.py`
- `plugin.yaml`

Folders/files are ignored when they:

- start with `!`
- start with `__`
- are `Cache`
- are not directories

## `plugin.py` contract

Use `BasePlugin` from `PluginSystem/PluginSystem.py`.

```python
from PluginSystem.PluginSystem import BasePlugin

class Plugin(BasePlugin):
    def __init__(self, Context, plugin):
        super().__init__(Context, plugin)

    def my_handler(self, slots):
        # your logic
        return {"value": "ok"}
```

Notes:

- Class name must be `Plugin`.
- Handler names must match YAML `handler` values.
- Handler signature should accept `slots` (list).
- You can use:
  - `self.contextManager.context.libraries.logger`
  - `self.contextManager.context.libraries.subprocess`
  - queues/config from `self.contextManager.context`.

## `plugin.yaml` contract

Minimal structure used by loader/runtime:

```yaml
plugin-metadata:
  name: Example
  version: 1
  description: Example plugin
  author: YourName
  enabled: true

plugin-data:
  intents:
    example.intent:
      intent: example.intent
      handler: my_handler
      examples:
        - "Example phrase"
      hasSlotInput: false
      hasSlotOutput: false
      responsesNoSlot:
        - "Done"
      responsesWithSlot:
        - "Done: {value}"
```

Important fields:

- `plugin-metadata.enabled`: currently loaded even when false; keep true for active plugins.
- `examples`: training phrases for intent model and STT grammar.
- `hasSlotInput`: if true, runtime tries to parse a number from Russian text.
- `hasSlotOutput`: enables slot-style response selection in runtime.
- `responsesNoSlot`: responses used for normal output and preprocessing cache generation.
- `responsesWithSlot`: responses intended for formatted output.

## Training and cache refresh

After changing plugin YAML, trigger preprocessing from `main.py`:

```bash
python main.py --preprocess
```

This updates:

- `models/model.pkl` (intent classifier)
- `hashsum.json` (YAML integrity map checked by `main.py`)
- `PluginSystem/Cache/<voice_hash>/...` (pre-generated TTS responses)

`main.py` also starts preprocessing automatically when hashes are missing or outdated.

## Runtime flow

- `main.py` builds plugin manager and grammar from plugin examples.
- `threads.confidenceThread` predicts intent and calls plugin handler.
- Returned data can be used for response formatting.
- Audio is played from cache or generated in TTS thread (if enabled).
