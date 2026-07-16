from PluginSystem.PluginSystem import BasePlugin
from Managers import ContextManager, LoadedPlugin

class Plugin(BasePlugin):
    def __init__(self, contextManager: ContextManager, plugin: LoadedPlugin):
        super().__init__(contextManager, plugin)

    def on_load(self):
        super().on_load()
    
    def on_unload(self):
        super().on_unload()
    
    def on_call(self, *args, **kwargs):
        super().on_call(*args, **kwargs)

    def open_telegram_handler(self, slots):
        self.contextManager.context.libraries.logger.trace("Opening Telegram...")
        self.contextManager.context.libraries.subprocess.run(["AyuGram"])
        return {}
