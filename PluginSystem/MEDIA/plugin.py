from ..PluginSystem import BasePlugin

class MediaPlugin(BasePlugin):
    def __init__(self, plugin_manager):
        super().__init__(plugin_manager)
        self.name = "MediaPlugin"
        self.description = "A plugin for media playback and control."
        self.version = "1.0.0"
        self.author = "Your Name"