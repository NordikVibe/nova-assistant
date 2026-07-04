class BasePlugin:
    def __init__(self, yaml_path: str):
        self.author = None
        self.name = None
        self.description = None
        self.version = None
        