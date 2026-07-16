from PluginSystem.PluginSystem import BasePlugin
from Managers import ContextManager, LoadedPlugin

class Plugin(BasePlugin):
    def __init__(self, contextManager: ContextManager, plugin: LoadedPlugin):
        super().__init__(contextManager, plugin)

    def on_load(self):
        super().on_load()
    
    def on_unload(self):
        super().on_unload()
    
    def on_call(self, *args, **kwargs) -> None:
        super().on_call(*args, **kwargs)

    def volumeSet_handler(self, slots: list) -> dict[str, int]:
        self.contextManager.context.platform.media.volume_set(slots[0])
        return {"volume": slots[0]}
    
    def volumeUp_handler(self, slots: list) -> dict[str, int]:
        self.contextManager.context.platform.media.volume_up(slots[0])
        return {"volume": f"+{slots[0]}"}
    
    def volumeDown_handler(self, slots: list) -> dict[str, int]:
        self.contextManager.context.platform.media.volume_down(slots[0])
        return {"volume": f"-{slots[0]}"}
    def volumeMute_handler(self, slots: list) -> dict[str, str]:
        self.contextManager.context.platform.media.volume_mute()
        return {"volume": True}
    def volumeUnmute_handler(self, slots: list) -> dict[str, str]:
        self.contextManager.context.platform.media.volume_unmute()
        return {"volume": False}
