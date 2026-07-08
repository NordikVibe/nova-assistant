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
    
    def pause(self, slots):
        """Pause the currently playing media."""
        self.Context.Libs.logger.trace("Pausing media playback.")
        self.Context.Libs.subprocess.run(["playerctl", "pause"])
        
        pass
    def resume(self, slots):
        """Resume the currently playing media."""
        self.Context.Libs.logger.trace("Resuming media playback.")
        self.Context.Libs.subprocess.run(["playerctl", "play"])
        pass
    def stop(self, slots):
        """Stop the currently playing media."""
        self.Context.Libs.logger.trace("Stopping media playback.")
        self.Context.Libs.subprocess.run(["playerctl", "stop"])
        pass
    def next(self, slots):
        """Skip to the next media track."""
        self.Context.Libs.logger.trace("Skipping to the next media track.")
        self.Context.Libs.subprocess.run(["playerctl", "next"])
        pass
    def previous(self, slots):
        """Go back to the previous media track."""
        self.Context.Libs.logger.trace("Going back to the previous media track.")
        self.Context.Libs.subprocess.run(["playerctl", "previous"])
        pass