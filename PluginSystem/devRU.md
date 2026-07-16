# Разработка плагинов (Русский)

Плагины загружаются из `/home/runner/work/nova-assistant/nova-assistant/PluginSystem`.

## Структура папки плагина

Каждый плагин должен быть отдельной директорией с файлами:

- `plugin.py`
- `plugin.yaml`

Игнорируются:

- файлы/папки, начинающиеся с `!`
- файлы/папки, начинающиеся с `__`
- папка `Cache`
- элементы, которые не являются директориями плагинов

## Контракт `plugin.py`

Используй `BasePlugin` из `PluginSystem/PluginSystem.py`.

```python
from PluginSystem.PluginSystem import BasePlugin

class Plugin(BasePlugin):
    def __init__(self, Context, plugin):
        super().__init__(Context, plugin)

    def my_handler(self, slots):
        return {"value": "ok"}
```

Важно:

- Имя класса: `Plugin`.
- Имя метода-обработчика должно совпадать с `handler` в YAML.
- Обработчик принимает `slots` (list).
- Через `self.Context` доступны логгер, subprocess, очереди и конфиг.

## Контракт `plugin.yaml`

Базовая структура:

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
        - "Пример фразы"
      hasSlotInput: false
      hasSlotOutput: false
      responsesNoSlot:
        - "Готово"
      responsesWithSlot:
        - "Готово: {value}"
```

Описание полей:

- `plugin-metadata.enabled`: сейчас плагин загружается даже при `false`, но для рабочего плагина ставь `true`.
- `examples`: фразы для обучения модели интентов и формирования STT-грамматики.
- `hasSlotInput`: если `true`, рантайм пытается извлечь число из русского текста.
- `hasSlotOutput`: включает выбор ответа в режиме слота.
- `responsesNoSlot`: обычные ответы, также используются при генерации кэша аудио.
- `responsesWithSlot`: ответы, в которые подставляются данные из handler.

## Обновление модели и кэша

После изменения YAML запусти принудительный препроцессинг через `main.py`:

```bash
python main.py --config config.json --preprocess
```

Это обновляет:

- `models/model.pkl`
- `hashsum.json`
- `PluginSystem/Cache/<voice_hash>/...`

`main.py` также автоматически запускает препроцессинг, если хэши отсутствуют или устарели.

## Что происходит во время работы

- `main.py` загружает плагины и собирает STT-грамматику из `examples`.
- `threads.confidenceThread` определяет интент и вызывает handler.
- Данные handler могут использоваться при формировании ответа.
- Проигрывается кэшированный или сгенерированный TTS-аудиофайл.
