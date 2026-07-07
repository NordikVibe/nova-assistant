# Разработка плагинов
Если ты хочешь сделать свои команды для ассистента — это для тебя.
Используй "*python create_plugin.py*", чтобы создать шаблон плагина с указанным именем и твоими данными: описание, версия и имя автора.

После запуска скрипта ты получишь чистый шаблон плагина:

**plugin.yaml**
```yaml
plugin-meta:
    name: 'Your plugin name'
    description: 'your desc'
    version: 'your v'
    author: 'your name or anon'
    enabled: true

plugin-data:
    intents:
        your-intent:
            intent: 'intent name'
            handler: 'name of method handler from plugin.py'
            examples: []
            hasSlot: false
            responsesNoSlot: []
            responsesWithSlot: []
```
*enabled: true* — если не true, плагин пропускается при загрузке.
*intent:* — название твоего интента; я использую названия в верхнем регистре, но можно любые, это просто строка.
*handler:* — это имя метода плагина, который выполняется при получении интента. Если handler не ссылается ни на один метод, в лог пишется ошибка, и интент пропускается.
*examples: []* — список фраз, на которые ассистент отвечает этим интентом.
*hasSlot: false* — если в твоей команде есть слот, можно установить true (сейчас может извлекать только русские названия чисел; позже хочу добавить возможность использовать regex-юнит для ручного извлечения слота).
*responseNoSlot: []* — эти фразы ассистент озвучивает на этапе preprocessing и случайно воспроизводит после выполнения handler (когда я добавлю опциональный llm-модуль в config, этот список будет использоваться, если модуль отключен).
*responsesWithSlot: []* — эти фразы ассистент озвучивает в реальном времени. Пиши их в формате "text{slot}text".
slot — это возвращаемые твоим handler значения, и они ничем не ограничены.

**plugin.py**
```python
from ..PluginSystem import BasePlugin

class MediaPlugin(BasePlugin):
    def __init__(self, Context):
        super().__init__(plugin_manager, Context)
    
    def handler(self, slot):
        return slot
```
Ты можешь использовать **Context**, чтобы получить всё необходимое: он содержит все используемые библиотеки и несколько кроссплатформенных менеджеров, таких как audio, notification, overlay (возможно, позже добавлю ещё): self.Context.Libs.logger (я использую loguru). Как использовать мои менеджеры, можно будет найти позже в папке Plugin system.
