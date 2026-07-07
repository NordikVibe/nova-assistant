# Plugin dev
If u want to do your own commands for assistant it gor you
Use "*python create_plugin.py*"  to create plugin pattern with writen name and your data like description, version and author name

After script you get clean plugin template:

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
*enabled: true* - if it not true plugin skips on load
*intent:* - name of your intent, i using upper case names, but you can use any, it just string
*handler:* - it's name of plugin's method, who exec on receiving intent. If handler does not refer to any method, it writes error to log and skip.
*examples: []* - list of phrases to which the assistant responds this intent
*hasSlot: false* - if your command has slot, you can set, to true(already it can extract only Russian number names, once later im want do possibility to use regex unit, for manually extract slot)
*responseNoSlot: []* - this phrases assistant voices on preprocessing stage and plays random after running handler(once i add optional llm module to config, and this list uses when this module disabled)
*responsesWithSlot: []* - this phrases assistant voices in real time. You must write this responses like "text{slot}text"
slot its returned values by your handler, and hasn't limits

**plugin.py**
```python
from ..PluginSystem import BasePlugin

class MediaPlugin(BasePlugin):
    def __init__(self, Context):
        super().__init__(plugin_manager, Context)
    
    def handler(self, slot):
        return slot
```
You can use **Context** to get all what you need, it contains all used library and some cross platform manager like audio, notification, overlay(may be add some later): self.Context.Libs.logger (i use loguru). How use my managers you can find in Plugin system folder later.