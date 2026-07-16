from doctest import debug
import json
import os
import platform
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
from system_apis.PlatformManagers import PlatformManager
from pydantic import BaseModel, field_validator
from pathlib import Path
from typing import Literal
from TTS.api import TTS

PLUGIN_SYSTEM_PATH = os.path.join(os.getcwd(), "PluginSystem")

DEFAULT_CONFIG = {
    "TTS": {
        "Voice": "Luis Moray",
        "Emotion": "neutral",
        "Model": "tts_models/multilingual/multi-dataset/xtts_v2",
        "enabled": True,
    },
    "STT": {"InputDevice": "", "Model": "models/vosk-model-ru-0.42", "enabled": True},
    "IntentModel": {"Path": "models/model.pkl", "enabled": True},
    "Audio": {"OutputDevice": "", "enabled": True},
    "Logging": {
        "FileLogLevel": "TRACE",
        "FileLogPath": "logs/app.log",
        "ConsoleLogLevel": "INFO",
        "ConsoleDebugLogLevel": "TRACE",
    },
    "User": {"Name": "User"},
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

class DotDict(dict):
    def __getattr__(self, name):
        return self[name]
    
class IntentConfig(BaseModel):
    modelPath: str
    enabled: bool
    @field_validator("modelPath")
    @classmethod
    def validate_path(cls, v):
        if Path(v).exists():
            return v
        else:
            raise ValueError(f"Intent model path '{v}' does not exist.")

class TTSConfig(BaseModel):
    voice: str
    emotion: str
    modelPath: str
    enabled: bool
    @field_validator("modelPath")
    @classmethod
    def validate_model(cls, v):
        if v.startswith("tts_models/"):
            return v
        else:
            raise ValueError(f"TTS model '{v}' is not a valid TTS model identifier.")
    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v):
        if v:
            if Path(v).exists() and Path(v).is_file() and v.endswith(".wav"):
                return v
            elif v in ["Luis Moray", "Alloy", "Antoni", "Bella", "Elli", "Jenny", "Josh", "Luna", "Rachel", "Sam", "Tessa"]:
                return v
            else:
                raise ValueError(f"TTS voice '{v}' is not a valid voice. Must be a path to a .wav file or one of the predefined voices.")
        else:
            raise ValueError("TTS voice cannot be empty.")
    @field_validator("emotion")
    @classmethod
    def validate_emotion(cls, v):
        if v in ["neutral", "happy", "sad", "angry"]:
            return v
        else:
            raise ValueError(f"TTS emotion '{v}' is not a valid emotion. Must be one of: 'neutral', 'happy', 'sad', 'angry'.")

class STTConfig(BaseModel):
    input_device: str
    modelPath: str
    enabled: bool
    @field_validator("modelPath")
    @classmethod
    def validate_model(cls, v):
        if Path(v).exists() and Path(v).is_dir():
            return v
        else:
            raise ValueError(f"STT model path '{v}' does not exist or is not a directory.")

class AudioConfig(BaseModel):
    output_device: str
    enabled: bool

class LoggingConfig(BaseModel):
    file_log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    file_log_path: str
    console_log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    console_debug_log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    @field_validator("file_log_path")
    @classmethod
    def validate_file_log_path(cls, v):
        if Path(v).parent.exists():
            return v
        else:
            raise ValueError(f"Log file path '{v}' does not exist.")

class UserConfig(BaseModel):
    name: str

class TelegramConfig(BaseModel):
    allowed_users: list[str]
    enabled: bool

@dataclass
class Context:
    stopEvent: threading.Event
    ConfidenceQueue: queue.Queue
    AudioQueue: queue.Queue
    TTSQueue: queue.Queue
    STTQueue: queue.Queue
    libraries: "Libraries"
    plugin_manager: "AssistantManager"
    args: dict
    platform_manager: "PlatformManager"
    tts_model: TTS | None = None

@dataclass
class Libraries:
    re: any
    os: any
    json: any
    queue: any
    threading: any
    sys: any
    logger: any
    subprocess: any
    platform: any

@dataclass
class Config:
    TTS: TTSConfig
    STT: STTConfig
    IntentModel: IntentConfig
    Audio: AudioConfig
    Logging: LoggingConfig
    User: UserConfig
    Telegram: TelegramConfig


class LoadedPlugin:
    intent_registry: dict[str, "IntentEntry"] = {}

    def __init__(
        self, plugin_meta_path: str, plugin_src_path: str, Context: "ContextManager"
    ):
        with open(plugin_meta_path, "r", encoding="utf-8") as f:
            plugin_yaml = yaml.safe_load(f)
        meta = plugin_yaml.get("plugin-metadata", {})
        self.name = meta.get("name", "Unknown")
        self.version = meta.get("version", "Unknown")
        self.description = meta.get("description", "No description provided.")
        self.author = meta.get("author", "Unknown")
        self.enabled = meta.get("enabled", False)
        self.plugin_class = plugin_src_path
        self.plugin_data = (
            plugin_yaml["plugin-data"] if "plugin-data" in plugin_yaml else {}
        )
        self.Context = Context

        spec = importlib.util.spec_from_file_location(self.name, self.plugin_class)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.instance = module.Plugin(Context, self)
        self.instance.on_load()
        self.module = module

        for intent_name, intent_data in plugin_yaml["plugin-data"]["intents"].items():
            handler = getattr(self.instance, intent_data["handler"])

            self.intent_registry[intent_name] = IntentEntry(
                plugin=self, intent=intent_data, handler=handler
            )

    def getRandomAnswer(self, intent: str) -> None | str:
        intent_data = self.plugin_data.get("intents", {}).get(intent, {})
        answers = [
            intent_data.get("responsesNoSlot", []),
            intent_data.get("responsesWithSlot", []),
        ]
        if not answers:
            return None
        random_index1 = (
            random.randint(0, 1)
            if intent_data.get("hasSlotOutput", False) and self.Context.TTS["enabled"]
            else 0
        )
        while not answers[random_index1]:
            random_index1 = random.randint(0, len(answers) - 1)
        random_index2 = random.randint(0, len(answers[random_index1]) - 1)
        return answers[random_index1][random_index2]


@dataclass
class IntentEntry:
    plugin: LoadedPlugin
    intent: IntentData
    handler: Callable


# ======================
# MANAGERS
# ======================


class ContextManager:
    def __init__(self, config_file: str = "config.json", args: dict = {debug: False}):
        self._load_cfg(config_file)
        self.config_file = config_file
        
        logger.remove()
        logger.add(
            self.config.Logging.file_log_path,
            level=self.config.Logging.file_log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )
        logger.add(
            sys.stdout,
            level=self.config.Logging.ConsoleDebugLogLevel if args.debug else self.config.Logging.ConsoleLogLevel,
        )
        
        self.context = Context(
            stopEvent=threading.Event(),
            ConfidenceQueue=queue.Queue(),
            AudioQueue=queue.Queue(),
            TTSQueue=queue.Queue(),
            STTQueue=queue.Queue(),
            libraries=Libraries(
                re=re,
                os=os,
                json=json,
                queue=queue,
                threading=threading,
                sys=sys,
                logger=logger,
                subprocess=subprocess,
                platform=platform,
            ),
            plugin_manager=AssistantManager(Context=self),
            args=args,
            platform_manager=PlatformManager(self),
        )

    def __getattribute__(self, name: str) -> Config | Context:
        if name in ["context", "config"]:
            return object.__getattribute__(self, name)
        return

    def __setattr__(self, name: str, value):
        if name in ["context", "config"]:
            object.__setattr__(self, name, value)
        else:
            raise AttributeError(f"Cannot set attribute '{name}' on ContextManager.")

    def write_config(self, new_params: dict) -> None:
        def _deep_update(orig: dict, updates: dict):
            for k, v in updates.items():
                if (
                    k in orig
                    and isinstance(orig[k], dict)
                    and isinstance(v, dict)
                ):
                    _deep_update(orig[k], v)
                else:
                    orig[k] = v

        # obtain a mutable dict representation of current config
        with open(self.config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        _deep_update(cfg, new_params)

        # write updated config to file
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(cfg, ensure_ascii=False, indent=4))

        self.config = Config(**cfg)

    def _load_cfg(self, cfg_file: str = "config.json") -> None:
        if Path(cfg_file).exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            merge(DEFAULT_CONFIG, config)
            self.config = Config(**config)
        else:
            print(
                f"⚠️ Config file {cfg_file} not found!. Creating a new one with default values."
            )
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=4))
            self.config = Config(**DEFAULT_CONFIG)


class BasePluginManager:
    plugins: list[LoadedPlugin] = []

    def __init__(
        self, contextManager: ContextManager, plugin_folder: str = PLUGIN_SYSTEM_PATH
    ):
        self.contextManager = contextManager
        self.plugins: list[LoadedPlugin] = []
        self.intent_registry: dict[str, IntentEntry] = {}
        self._load_plugins(plugin_folder)

    def _load_plugins(self, plugin_folder: str):
        plugin_folder = os.path.join(os.getcwd(), plugin_folder)

        for pluginDir in os.listdir(plugin_folder):
            plugin_data = None
            plugin_src = None
            if (
                os.path.isfile(os.path.join(plugin_folder, pluginDir))
                or pluginDir.startswith("!")
                or pluginDir.startswith("__")
                or pluginDir == "Cache"
            ):
                continue

            for file in os.listdir(os.path.join(plugin_folder, pluginDir)):
                if file.endswith(".yaml"):
                    plugin_data = os.path.join(plugin_folder, pluginDir, file)

                elif file.endswith(".py"):
                    plugin_src = os.path.join(plugin_folder, pluginDir, file)

            if plugin_data is None or plugin_src is None:
                self.contextManager.context.libraries.logger.warning(
                    f"Plugin {pluginDir} is missing "
                    f"{'plugin.yaml' if plugin_data is None else 'plugin.py'}"
                )
                continue

            self.plugins.append(
                LoadedPlugin(
                    plugin_meta_path=plugin_data,
                    plugin_src_path=plugin_src,
                    Context=self.contextManager,
                )
            )
            for name, entry in self.plugins[-1].intent_registry.items():
                self.intent_registry[name] = entry


class TrainingManager(BasePluginManager):
    model: Pipeline = None

    def __init__(
        self,
        plugin_folder: str = PLUGIN_SYSTEM_PATH,
        contextManager: ContextManager = None,
        model: Pipeline = None,
    ):
        super().__init__(contextManager, plugin_folder)
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
        joblib.dump(self.model, self.contextManager.config.IntentModel.modelPath)

    def getDataForTTS(self) -> list:
        data = []
        for plugin in self.plugins:
            for intent_name, intent_data in plugin.plugin_data.get(
                "intents", {}
            ).items():
                answers = intent_data.get("responsesNoSlot", [])
                data.append(answers)
        return data


class AssistantManager(BasePluginManager):
    def __init__(
        self, plugin_folder: str = PLUGIN_SYSTEM_PATH, contextManager: ContextManager = None
    ):
        super().__init__(contextManager, plugin_folder)

    def getPluginByName(self, name: str) -> LoadedPlugin:
        for plugin in self.plugins:
            if plugin.name == name:
                return plugin
        return None

    def getGrammarForSTT(self) -> str:
        grammar = []
        for plugin in self.plugins:
            for intent_name, intent_data in plugin.plugin_data.get(
                "intents", {}
            ).items():
                for example in intent_data.get("examples", []):
                    grammar.append(f"{example}")
        grammar.append("[unk]")
        grammar = list(set(grammar))
        return json.dumps(grammar, ensure_ascii=False)
