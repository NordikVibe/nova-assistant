from Managers import ContextManager, TrainingManager
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from TTS.api import TTS

import json
import argparse
import threading
import hashlib
import builtins
import soundfile as sf
import numpy as np
import librosa
import gc

import threads
from pathlib import Path
# ======================
# ARGUMENTS
# ======================

parser = argparse.ArgumentParser(description="Voice Assistant")
parser.add_argument("--about", help="Show information about the program", action="store_true")
parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
parser.add_argument("-c", "--config", type=str, default="config.json", help="Path to the config file")
parser.add_argument("--preprocess", action="store_true", help="Force preprocessing of the model and TTS generation")

args = parser.parse_args()

# =====================
# CONTEXT
# =====================

context_manager = ContextManager(config_file=args.config, args=args)


# ======================
# HASH CHECK
# ======================
if not Path("hashsum.json").exists():
    context_manager.context.libraries.logger.warning("⚠️ Hash sum file not found! Need to relearn sklearn model. Please wait for preprocessing to finish.")
    need_preprocessing = True
else:
    check_hash_sum_file = open("hashsum.json", "r", encoding="utf-8")
    check_hash_sum = json.load(check_hash_sum_file)
    check_hash_sum_file.close()
    for pluginF in Path("PluginSystem").iterdir():
        if not pluginF.is_dir() or pluginF.name.startswith("!") or pluginF.name.startswith("__") or pluginF.name == "Cache":
            continue
        if need_preprocessing:
            break
        for file in pluginF.iterdir():
            if file.suffix == ".yaml":
                hash = hashlib.sha256(file.read_bytes()).hexdigest()
                context_manager.context.libraries.logger.trace(f"Hash for {pluginF.name}/{file.name}: {hash}")
                if hash != check_hash_sum.get(f"{pluginF.name}/{file.name}"):
                    context_manager.context.libraries.logger.warning(f"⚠️ Hash mismatch for {pluginF.name}/{file.name}! Expected: {check_hash_sum.get(f'{pluginF.name}/{file.name}')}, Got: {hash}")
                    context_manager.context.libraries.logger.info("Need to start preprocessing to update hashes. Please wait for preprocessing to finish.")
                    need_preprocessing = True
                    break
                else:
                    continue

if need_preprocessing or args.preprocess:
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), max_features=1000),
        LogisticRegression(max_iter=1000)
    )
    manager = TrainingManager(Context=context_manager, model=model)
    manager.train_model()
    manager.dump_model()
    
    if Path(context_manager.config.TTS.Voice).is_file():
        def ttsSynthesize(text, output_path, tts):
            tts.tts_to_file(text=text, file_path=output_path, language="ru", speaker_wav=context_manager.config.TTS.Voice, emotion=context_manager.config.TTS.Emotion)
            data, sr = sf.read(output_path)
            data = data.astype(np.float32)
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if sr != 48000:
                data = librosa.resample(
                    data,
                    orig_sr=sr,
                    target_sr=48000
                )
            data = np.nan_to_num(data)
            sf.write(output_path, data, 48000)
    else:
        def ttsSynthesize(text, output_path):
            tts.tts_to_file(text=text, file_path=output_path, language="ru", speaker=context_manager.config.TTS.Voice, emotion=context_manager.config.TTS.Emotion)
            data, sr = sf.read(output_path)
            data = data.astype(np.float32)
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if sr != 48000:
                data = librosa.resample(
                    data,
                    orig_sr=sr,
                    target_sr=48000
                )
            data = np.nan_to_num(data)
            sf.write(output_path, data, 48000)
    
    hash_sum_file = open("hashsum.json", "w", encoding="utf-8")
    hash_sums = {}
    for pluginF in Path("PluginSystem").iterdir():
        if pluginF.is_file() or pluginF.name.startswith("!") or pluginF.name.startswith("__") or pluginF.name == "Cache":
            continue
        for file in pluginF.iterdir():
            if file.suffix == ".yaml":
                hash_value = hashlib.sha256(file.read_bytes()).hexdigest()
                context_manager.context.libraries.logger.info(f"Hash for {pluginF}/{file}: {hash_value}")
                hash_sums[f"{pluginF}/{file}"] = hash_value
    json.dump(hash_sums, hash_sum_file, ensure_ascii=False, indent=4)
    hash_sum_file.close()

    context_manager.context.libraries.logger.success("Training completed and model saved to 'models/model.pkl'.")
    context_manager.context.libraries.logger.info("Checking for audio files to generate...")
    
    data = manager.getDataForTTS()
    data_to_tts = []
    
    voice_hash = hashlib.sha256(context_manager.config.TTS.Voice.encode('utf-8')).hexdigest()
    
    if not Path(f"PluginSystem/Cache/{voice_hash}").exists():
        Path(f"PluginSystem/Cache/{voice_hash}").mkdir(parents=True, exist_ok=True)
        context_manager.context.libraries.logger.info(f"Created cache directory for voice: PluginSystem/Cache/{voice_hash}")
    
    default_print = builtins.print
    builtins.print = lambda *args, **kwargs: default_print(*args, **kwargs) if not args[0].startswith("Generating TTS for") else None
    
    for unit in data:
        text = unit["text"]
        intent = unit["intent"]
        output_path = f"PluginSystem/Cache/{voice_hash}/{hashlib.sha256(text.encode('utf-8')).hexdigest()}.mp3"
        if not Path(output_path).exists():
            context_manager.context.libraries.logger.info(f"Generating TTS for intent '{intent}': {text}")
            ttsSynthesize(text=text, output_path=output_path)
            context_manager.context.libraries.logger.info(f"TTS generated and saved to: {output_path}")
        else:
            context_manager.context.libraries.logger.info(f"TTS already exists for intent '{intent}': {text}, skipping generation.")
    
    if not data_to_tts:
        context_manager.context.libraries.logger.info("All TTS audio files are already generated.")
    else:
        context_manager.context.libraries.logger.info(f"Ready to generate {len(data_to_tts)} new TTS audio files.")
        
        tts = TTS(model_name=context_manager.config.TTS.Model, progress_bar=True, gpu=False)

        for text, path in data_to_tts:
            ttsSynthesize(text=text, output_path=path, tts=tts)
            context_manager.context.libraries.logger.info(f"{text} generated and saved to: {path}")

        if context_manager.config.TTS.enabled:
            context_manager.context.TTSMODEL = tts
            context_manager.context.libraries.logger.info("TTS model initialized and set in context.")
        else:
            context_manager.context.libraries.logger.info("TTS is disabled in the config. TTS model will not be set in context. Deleting TTS model to free up memory...")
            del tts
            gc.collect()


# ======================
# THREAD HYPERVISOR
# ======================

HyperVisorThread = threading.Thread(target=threads.hypervisorThread, args=(context_manager,), daemon=True)
HyperVisorThread.start()
