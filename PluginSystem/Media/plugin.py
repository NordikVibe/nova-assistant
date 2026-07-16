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
    
    def pause(self, slots):
        """Pause the currently playing media."""
        self.contextManager.context.libraries.logger.trace("Pausing media playback.")
        self.contextManager.context.libraries.subprocess.run(["playerctl", "pause"])
        
        pass
    def resume(self, slots):
        """Resume the currently playing media."""
        self.contextManager.context.libraries.logger.trace("Resuming media playback.")
        self.contextManager.context.libraries.subprocess.run(["playerctl", "play"])
        pass
    def stop(self, slots):
        """Stop the currently playing media."""
        self.contextManager.context.libraries.logger.trace("Stopping media playback.")
        self.contextManager.context.libraries.subprocess.run(["playerctl", "stop"])
        pass
    def next(self, slots):
        """Skip to the next media track."""
        self.contextManager.context.libraries.logger.trace("Skipping to the next media track.")
        self.contextManager.context.libraries.subprocess.run(["playerctl", "next"])
        pass
    def previous(self, slots):
        """Go back to the previous media track."""
        self.contextManager.context.libraries.logger.trace("Going back to the previous media track.")
        self.contextManager.context.platform_manager.media.previous_track()
        pass