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

    def volumeSet_handler(self, slots: list):
        command = f'pactl set-sink-volume @DEFAULT_SINK@ {slots[0]}%'.split(" ")
        self.Context.Libs["subprocess"].run(command)
        return {"volume": slots[0]}
    
    def volumeUp_handler(self, slots: list):
        command = f'pactl set-sink-volume @DEFAULT_SINK@ +{slots[0]}%'.split(" ")
        self.Context.Libs["subprocess"].run(command)
        return {"volume": f"+{slots[0]}"}
    
    def volumeDown_handler(self, slots: list):
        command = f'pactl set-sink-volume @DEFAULT_SINK@ -{slots[0]}%'.split(" ")
        self.Context.Libs["subprocess"].run(command)
        return {"volume": f"-{slots[0]}"}
    def volumeMute_handler(self, slots: list):
        command = 'pactl set-sink-mute @DEFAULT_SINK@ true'.split(" ")
        self.Context.Libs["subprocess"].run(command)
        return {"volume": "true"}
    def volumeUnmute_handler(self, slots: list):
        command = 'pactl set-sink-mute @DEFAULT_SINK@ false'.split(" ")
        self.Context.Libs["subprocess"].run(command)
        return {"volume": "false"}
