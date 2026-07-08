from PluginSystem.PluginSystem import BasePlugin

class Plugin(BasePlugin):
    def __init__(self, Context, plugin):
        super().__init__(Context, plugin)

    def on_load(self):
        super().on_load()
    
    def on_unload(self):
        super().on_unload()
    
    def on_call(self, *args, **kwargs):
        super().on_call(*args, **kwargs)

    def activate_handler(self, slots):
        return {"value": self.Context.User["Name"]}
