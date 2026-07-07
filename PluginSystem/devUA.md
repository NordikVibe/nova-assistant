# Розробка плагінів
Якщо ти хочеш зробити власні команди для асистента — це для тебе.
Використай "*python create_plugin.py*", щоб створити шаблон плагіна з указаною назвою та твоїми даними: опис, версія й ім'я автора.

Після запуску скрипта ти отримаєш чистий шаблон плагіна:

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
*enabled: true* — якщо не true, плагін буде пропущено під час завантаження.
*intent:* — назва твого інтенту; я використовую назви у верхньому регістрі, але можна будь-які, це просто рядок.
*handler:* — це назва методу плагіна, який виконується при отриманні інтенту. Якщо handler не посилається на жоден метод, у лог записується помилка, і інтент пропускається.
*examples: []* — список фраз, на які асистент реагує цим інтентом.
*hasSlot: false* — якщо у твоїй команді є слот, можна встановити true (зараз може витягувати лише російські назви чисел; пізніше планую додати можливість використовувати regex-юніт для ручного витягування слота).
*responseNoSlot: []* — ці фрази асистент озвучує на етапі preprocessing і випадково відтворює після виконання handler (коли я додам опціональний llm-модуль у config, цей список буде використовуватися, якщо модуль вимкнений).
*responsesWithSlot: []* — ці фрази асистент озвучує в реальному часі. Пиши їх у форматі "text{slot}text".
slot — це значення, які повертає твій handler, і вони нічим не обмежені.

**plugin.py**
```python
from ..PluginSystem import BasePlugin

class MediaPlugin(BasePlugin):
    def __init__(self, Context):
        super().__init__(plugin_manager, Context)
    
    def handler(self, slot):
        return slot
```
Ти можеш використовувати **Context**, щоб отримати все необхідне: він містить усі використовувані бібліотеки та кілька кросплатформних менеджерів, як-от audio, notification, overlay (можливо, пізніше додам ще): self.Context.Libs.logger (я використовую loguru). Як користуватися моїми менеджерами, можна буде знайти пізніше в папці Plugin system.
