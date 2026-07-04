import os
import json
import importlib
import re
import random


class Intent:
    def __init__(self, intent: str, examples: list[str], handler, responses_text: dict[int, str], responses_text_to_preproc: list[str], responses_audio: list[str], path: str = None):
        self.intent = intent
        self.examples = examples
        self.handler = handler
        self.responses_text_to_preproc = responses_text_to_preproc
        self.responses_text = responses_text
        self.responses_audio = responses_audio
        self.path = path

class IntentManager:
    def __init__(self):
        self.intents = []

    def add_intent(self, intent: Intent):
        self.intents.append(intent)
    
    def add_intents(self, intents: list[Intent]):
        self.intents.extend(intents)

    def get_intent(self, intent_name: str) -> Intent:
        for intent in self.intents:
            if intent.intent == intent_name:
                return intent
        return None
    def get_handler_by_intent(self, intent_name: str):
        intent = self.get_intent(intent_name)
        if intent:
            return intent.handler
        return None
    
    def get_learning_data(self)-> tuple[list[str], list[str]]:
        texts = []
        intents = []
        for intent in self.intents:
            for example in intent.examples:
                texts.append(example)
                intents.append(intent.intent)
        return texts, intents
    
    def get_handler_by_intent(self, intent_name: str):
        intent = self.get_intent(intent_name)
        if intent:
            return intent.handler
        return None
    def get_grammar_by_intent(self):
        gram = []
        for intent in self.intents:
            for example in intent.examples:
                gram.append(example.lower())
        return gram
    
    def get_preprocess_text_answers(self)-> list[dict[list[str], str]]:
        answers = []
        for intent in self.intents:
            answers.append({"response": intent.responses_text_to_preproc, "path": intent.path})
        return answers
    def get_random_response_by_intent(self, intent_name: str):
        
        intent = self.get_intent(intent_name)
        if len(list(intent.responses_text.keys())) > 0:
            rand = random.choice(list(intent.responses_text.keys()))
        else:
            return None
        if not "{slot}" in intent.responses_text[rand]:
            return f"{intent.path}/response_{rand}.mp3"
        else:
            return [intent.responses_text[rand]]

def get_intents(plugin_folder: str, mgr: IntentManager = None) -> IntentManager:
    if mgr is None:
        mgr = IntentManager()
    responses_audio = []
    plugin_folder = os.path.join(os.getcwd(), plugin_folder)
    
    print(f"Loading intents from {plugin_folder}")
        
    for foldername in os.listdir(plugin_folder):
        answers_texts = []
        folder_path = os.path.join(plugin_folder, foldername)
        if not os.path.isdir(folder_path):
            print(f"Skipping {folder_path}")
            continue
        intent_file = os.path.join(folder_path, "intent.json")
        if not os.path.isfile(intent_file):
            print(f"Skipping {folder_path}, no intent.json found")
            continue
        for filename in os.listdir(folder_path):
            if filename.startswith("response") and filename.endswith(".mp3"):
                responses_audio.append(os.path.join(folder_path, filename))
        with open(intent_file, "r") as f:
            examples = []
            intent_data = json.load(f)
            for example in intent_data["examples"]:
                examples.append(example)
                examples.append(example.lower())
            for answer in intent_data.get("answers", {}).keys():
                if not "{slot}" in intent_data["answers"][answer]:
                    answers_texts.append([intent_data["answers"][answer], answer])
            intent = Intent(
                intent=intent_data["intent"],
                examples=examples,
                handler=importlib.import_module(f"Plugins.{foldername}.handler").handle_intent,
                responses_text_to_preproc=answers_texts,
                responses_text=intent_data.get("answers", {}),
                responses_audio=responses_audio,
                path=folder_path
            )
        mgr.add_intent(intent)
        
    return mgr

class IntentManager:
    def __init__(self):
        self.intents = []
    
    def load_intents(self, plugin_folder: str):
        get_intents(plugin_folder, self)

class TrainingManager(IntentManager):
    def __init__(self):
        super().__init__()

class AssistantManager(IntentManager):
    def __init__(self):
        super().__init__()