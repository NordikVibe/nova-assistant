from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from TTS.api import TTS
from Managers import TrainingManager, ContextManager
import json
import hashlib
import os
import soundfile as sf
import numpy as np
import librosa
import argparse
import builtins

TARGET_SR = 48000

parser = argparse.ArgumentParser(description="Voice Assistant")
parser.add_argument("--config", default="config.json", help="Path to config file")
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
args = parser.parse_args()

model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), max_features=1000),
    LogisticRegression(max_iter=1000)
)
context_manager = ContextManager(config_file=args.config, args=args)
manager = TrainingManager(Context=context_manager, model=model)
manager.train_model()
manager.dump_model()

if os.path.exists(context_manager.TTS["Voice"]):
    def ttsSynthesize(text, output_path):
        tts.tts_to_file(text=text, file_path=output_path, language="ru", speaker_wav=context_manager.TTS["Voice"], emotion="neutral")
        data, sr = sf.read(output_path)
        data = data.astype(np.float32)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        if sr != TARGET_SR:
            data = librosa.resample(
                data,
                orig_sr=sr,
                target_sr=TARGET_SR
            )
        data = np.nan_to_num(data)
        sf.write(output_path, data, TARGET_SR)
else:
    def ttsSynthesize(text, output_path):
        tts.tts_to_file(text=text, file_path=output_path, language="ru", speaker=context_manager.TTS["Voice"], emotion="neutral")
        data, sr = sf.read(output_path)
        data = data.astype(np.float32)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        if sr != TARGET_SR:
            data = librosa.resample(
                data,
                orig_sr=sr,
                target_sr=TARGET_SR
            )
        data = np.nan_to_num(data)
        sf.write(output_path, data, TARGET_SR)

hash_sum_file = open("hashsum.json", "w", encoding="utf-8")
hash_sums = {}
for pluginF in os.listdir("PluginSystem"):
    if os.path.isfile(os.path.join("PluginSystem", pluginF)) or pluginF.startswith("!") or pluginF.startswith("__") or pluginF == "Cache":
        continue
    for file in os.listdir(f"PluginSystem/{pluginF}"):
        if file.endswith(".yaml"):
            hash_value = hashlib.sha256(open(f"PluginSystem/{pluginF}/{file}", "rb").read()).hexdigest()
            context_manager.Libs.logger.info(f"Hash for {pluginF}/{file}: {hash_value}")
            hash_sums[f"{pluginF}/{file}"] = hash_value
json.dump(hash_sums, hash_sum_file, ensure_ascii=False, indent=4)
hash_sum_file.close()
            

context_manager.Libs.logger.success("Training completed and model saved to 'models/model.pkl'.")
context_manager.Libs.logger.info("Checking for audio files to generate...")

data = manager.getDataForTTS()
data_to_tts = []

voice_hash = hashlib.sha256(context_manager.TTS['Voice'].encode('utf-8')).hexdigest()
if not os.path.exists(f"PluginSystem/Cache/{voice_hash}"):
    os.makedirs(f"PluginSystem/Cache/{voice_hash}")
    context_manager.Libs.logger.warning(f"Voice cache directory not found for voice '{context_manager.TTS['Voice']}', creating directory: PluginSystem/Cache/{voice_hash}")

old_print = builtins.print
builtins.print = lambda *a, **k: None
for unit in data:
    for response in unit:
        path = f"PluginSystem/Cache/{voice_hash}/{hashlib.sha256(response.encode('utf-8')).hexdigest()}.mp3"
        if not os.path.exists(path):
            data_to_tts.append((response, path))
            context_manager.Libs.logger.trace(f"[+] Audio does not exist for text: {response}, add to queue.")
        else:
            context_manager.Libs.logger.trace(f"[+] Audio already exists for text: {response}, skipping generation.")
            continue

if not data_to_tts:
    context_manager.Libs.logger.success("[+] All audio responses already exist, skipping generation.")
    exit(0)
generation_count = len(data_to_tts)
context_manager.Libs.logger.trace(f"[+] Generating audio for {generation_count} responses...")

tts = TTS(model_name=context_manager.TTS['Model'], progress_bar=True, gpu=False)

for data in data_to_tts:
    text, path = data
    context_manager.Libs.logger.trace(f"[+] Generating audio for text: {text}\n[+] left {generation_count - data_to_tts.index(data) - 1} responses to generate...")
    ttsSynthesize(text=text, output_path=path)

context_manager.Libs.logger.success("[+] Audio generation completed.")

