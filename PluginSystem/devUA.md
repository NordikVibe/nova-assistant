# Розробка плагінів (Українська)

Плагіни завантажуються з `/home/runner/work/nova-assistant/nova-assistant/PluginSystem`.

## Структура папки плагіна

Кожен плагін має бути окремою директорією з файлами:

- `plugin.py`
- `plugin.yaml`

Ігноруються:

- директорії/файли, що починаються з `!`
- директорії/файли, що починаються з `__`
- директорія `Cache`
- усе, що не є директорією плагіна

## Контракт `plugin.py`

Використовуй `BasePlugin` із `PluginSystem/PluginSystem.py`.

```python
from PluginSystem.PluginSystem import BasePlugin

class Plugin(BasePlugin):
    def __init__(self, Context, plugin):
        super().__init__(Context, plugin)

    def my_handler(self, slots):
        return {"value": "ok"}
```

Важливо:

- Ім'я класу: `Plugin`.
- Назви методів-обробників мають збігатися з `handler` у YAML.
- Обробник приймає `slots` (list).
- Доступні інструменти через `self.Context`, наприклад:
  - `self.Context.Libs.logger`
  - `self.Context.Libs.subprocess`
  - черги, конфіг і дані користувача.

## Контракт `plugin.yaml`

Базова структура:

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
        - "Приклад фрази"
      hasSlotInput: false
      hasSlotOutput: false
      responsesNoSlot:
        - "Готово"
      responsesWithSlot:
        - "Готово: {value}"
```

Пояснення полів:

- `plugin-metadata.enabled`: зараз плагін все одно завантажується, але для активного плагіна став `true`.
- `examples`: фрази для навчання моделі інтентів і граматики STT.
- `hasSlotInput`: якщо `true`, рантайм пробує витягти число з російського тексту.
- `hasSlotOutput`: вмикає вибір відповіді у слот-режимі.
- `responsesNoSlot`: звичайні відповіді, також використовуються для попередньої генерації аудіо.
- `responsesWithSlot`: відповіді для форматування через дані з handler.

## Оновлення моделі та кешу

Після змін у YAML запусти:

```bash
python preprocessing.py --config config.json
```

Оновлюються:

- `models/model.pkl`
- `hashsum.json`
- `PluginSystem/Cache/<voice_hash>/...`

## Що відбувається під час роботи

- `main.py` завантажує плагіни та формує STT-граматику з `examples`.
- `threads.confidenceThread` визначає інтент і викликає handler.
- Повернуті дані можуть підставлятися у відповідь.
- Відтворюється кешований або згенерований TTS-аудіофайл.
