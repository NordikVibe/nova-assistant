from Managers import ContextManager, LoadedPlugin

class BasePlugin:
    def __init__(self, context: ContextManager, plugin: LoadedPlugin):
        self.Context = context
        self.name = plugin.name
        self.description = plugin.description
        self.version = plugin.version
        self.author = plugin.author

    def on_load(self):
        """Called when the plugin is loaded."""
        self.Context.Libs.logger.trace(f"Plugin {self.name} v{self.version} by {self.author} loaded.")
        pass
    def on_unload(self):
        """Called when the plugin is unloaded."""
        self.Context.Libs.logger.trace(f"Plugin {self.name} v{self.version} by {self.author} unloaded.")
        pass
    def on_call(self, *args, **kwargs):
        """Called when the plugin is invoked."""
        self.Context.Libs.logger.trace(f"Plugin {self.name} v{self.version} by {self.author} called.")
        pass
        