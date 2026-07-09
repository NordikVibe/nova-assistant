import json
import os
import re
import queue
import threading
from dataclasses import dataclass
import joblib
import yaml
from sklearn.pipeline import Pipeline
import importlib.util
import random
from typing import Callable, TypedDict
from loguru import logger
import sys
import subprocess


ContextManager = None

PLUGIN_SYSTEM_PATH = os.path.join(os.getcwd(), "PluginSystem")

DEFAULT_CONFIG = {
    "TTS": {
        "Voice": "Luis Moray",
        "Emotion": "neutral",
        "Model": "tts_models/multilingual/multi-dataset/xtts_v2",
        "enabled": False,
    },
    "STT": {
        "Model": "models/vosk-model-ru-0.42",
    },
    "IntentModel": {
        "Path": "models/model.pkl",
    },
    "Audio": {
        "InputDevice": "",
        "OutputDevice": ""
    },
    "Logging": {
        "FileLogLevel": "TRACE",
        "FileLogPath": "logs/app.log",
        "ConsoleLogLevel": "INFO",
        "ConsoleDebugLogLevel": "TRACE"
    },
    "User": {
        "Name": "User"
    },
    }
def merge(default: dict, user: dict):
    for key, value in default.items():
        if key not in user:
            user[key] = value
        elif isinstance(value, dict) and isinstance(user[key], dict):
            merge(value, user[key])

# ======================
# OBJECTS
# ======================
class IntentData(TypedDict):
    handler: str
    intent: str
    examples: list[str]
    answersNoSlot: list[str]
    answersWithSlot: list[str]
    hasSlot: bool

class IntentEntry(): 
    pass

class DotDict(dict):
    def __getattr__(self, name):
        return self[name]

class LoadedPlugin:
    intent_registry: dict[str, IntentEntry] = {}
    def __init__(self, plugin_meta_path: str, plugin_src_path: str, Context: ContextManager):
        with open(plugin_meta_path, "r", encoding="utf-8") as f:
            plugin_yaml = yaml.safe_load(f)
        meta = plugin_yaml.get("plugin-metadata", {})
        self.name = meta.get("name", "Unknown")
        self.version = meta.get("version", "Unknown")
        self.description = meta.get("description", "No description provided.")
        self.author = meta.get("author", "Unknown")
        self.enabled = meta.get("enabled", False)
        self.plugin_class = plugin_src_path
        self.plugin_data = plugin_yaml["plugin-data"] if "plugin-data" in plugin_yaml else {}
        self.Context = Context

        spec = importlib.util.spec_from_file_location(
            self.name,
            self.plugin_class
        )

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.instance = module.Plugin(Context, self)
        self.instance.on_load()
        self.module = module
        
        for intent_name, intent_data in plugin_yaml["plugin-data"]["intents"].items():

            handler = getattr(self.instance, intent_data["handler"])

            self.intent_registry[intent_name] = IntentEntry(
                plugin=self,
                intent=intent_data,
                handler=handler
            )
    def getRandomAnswer(self, intent: str) -> None | str:
        intent_data = self.plugin_data.get("intents", {}).get(intent, {})
        answers_no_slot = intent_data.get("responsesNoSlot", [])
        answers_with_slot = intent_data.get("responsesWithSlot", [])
        if not answers_no_slot and not answers_with_slot:
            return None
        tts_enabled = bool(self.Context.TTS.get("enabled", False))
        if intent_data.get("hasSlotOutput", False) and tts_enabled and answers_with_slot:
            return random.choice(answers_with_slot)
        if answers_no_slot:
            return random.choice(answers_no_slot)
        return random.choice(answers_with_slot)
    
@dataclass
class IntentEntry:
    plugin: LoadedPlugin
    intent: IntentData
    handler: Callable
# ======================
# MANAGERS
# ======================

class ContextManager:
    def __init__(self, config_file: str = "config.json", args: dict = None):
        self.context = {}
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            print(f"⚠️ Config file {config_file} not found!. Creating a new one with default values.")
            config = {}
        merge(DEFAULT_CONFIG, config)
        
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(config, ensure_ascii=False, indent=4))
        
        logger.remove()
        logger.add(config["Logging"]["FileLogPath"], level=config["Logging"]["FileLogLevel"], rotation="10 MB", retention="7 days", compression="zip")
        logger.add(sys.stdout, level=config["Logging"]["ConsoleDebugLogLevel"] if args.debug else config["Logging"]["ConsoleLogLevel"])
        self.context["TTS"] = config.get("TTS")
        self.context["Libs"] = DotDict({
            "re": re,
            "os": os,
            "json": json,
            "queue": queue,
            "threading": threading,
            "sys": sys,
            "logger": logger,
            "subprocess": subprocess
            })
        self.context["stopEvent"] = threading.Event()
        self.context["ConfidenceQueue"] = queue.Queue()
        self.context["AudioQueue"] = queue.Queue()
        self.context["TTSQueue"] = queue.Queue()
        self.context["Intent"] = config.get("IntentModel")
        self.context["STT"] = config.get("STT")
        self.context["Audio"] = config.get("Audio")
        self.context["logging"] = config.get("Logging")
        self.context["User"] = config.get("User")
        # self.context[]

    def __getattribute__(self, name):
        if name in ["context", "__dict__", "__class__"]:
            return object.__getattribute__(self, name)
        context = object.__getattribute__(self, "context")
        return context.get(name, None)
    def __setattr__(self, name: str, value):
        if name == "context":
            object.__setattr__(self, name, value)
            return

        self.context[name] = value

class BasePluginManager:
    plugins: list[LoadedPlugin] = []
    def __init__(self, Context: ContextManager, plugin_folder: str = PLUGIN_SYSTEM_PATH):
        self.Context = Context
        self.plugins: list[LoadedPlugin] = []
        self.intent_registry: dict[str, IntentEntry] = {}
        self._load_plugins(plugin_folder)
    
    def _load_plugins(self, plugin_folder: str):
        plugin_folder = os.path.join(os.getcwd(), plugin_folder)
        
        for pluginDir in os.listdir(plugin_folder):
            plugin_data = None
            plugin_src = None
            if os.path.isfile(os.path.join(plugin_folder, pluginDir)) or pluginDir.startswith("!") or pluginDir.startswith("__") or pluginDir == "Cache":
                continue

            for file in os.listdir(os.path.join(plugin_folder, pluginDir)):
                if file.endswith(".yaml"):
                    plugin_data = os.path.join(plugin_folder, pluginDir, file)

                elif file.endswith(".py"):
                    plugin_src = os.path.join(plugin_folder, pluginDir, file)

            if plugin_data is None or plugin_src is None:
                self.Context.Libs.logger.warning(
                    f"Plugin {pluginDir} is missing "
                    f"{'plugin.yaml' if plugin_data is None else 'plugin.py'}"
                )
                continue

            self.plugins.append(
                LoadedPlugin(
                    plugin_meta_path=plugin_data,
                    plugin_src_path=plugin_src,
                    Context=self.Context
                )
            )
            for name, entry in self.plugins[-1].intent_registry.items():
                self.intent_registry[name] = entry
                
class TrainingManager(BasePluginManager):
    model: Pipeline = None
    def __init__(self, plugin_folder: str = PLUGIN_SYSTEM_PATH, Context: ContextManager = None, model: Pipeline = None):
        super().__init__(Context, plugin_folder)
        self.model = model

    def train_model(self):
        X = []
        y = []
        for plugin in self.plugins:
            for _, intent in plugin.plugin_data["intents"].items():
                for example in intent["examples"]:
                    for n in [example, example.lower(), example.upper()]:
                        X.append(n)
                        y.append(intent["intent"])
        self.model.fit(X, y)
        return self.model
    def dump_model(self, path: str = "models/model.pkl"):
        joblib.dump(self.model, self.Context.Intent["Path"])
    def getDataForTTS(self) -> list:
        data = []
        for plugin in self.plugins:
            for intent_name, intent_data in plugin.plugin_data.get("intents", {}).items():
                answers = intent_data.get("responsesNoSlot", [])
                data.append(answers)
        return data
                
class AssistantManager(BasePluginManager):
    def __init__(self, plugin_folder: str = PLUGIN_SYSTEM_PATH, Context: ContextManager = None):
        super().__init__(Context, plugin_folder)
    def getPluginByName(self, name: str) -> LoadedPlugin:
        for plugin in self.plugins:
            if plugin.name == name:
                return plugin
        return None
    def getGrammarForSTT(self) -> str:
        grammar = []
        for plugin in self.plugins:
            for intent_name, intent_data in plugin.plugin_data.get("intents", {}).items():
                for example in intent_data.get("examples", []):
                    grammar.append(f"{example}")
        grammar.append("[unk]")
        grammar = list(set(grammar))
        return json.dumps(grammar, ensure_ascii=False)