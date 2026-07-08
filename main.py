from scipy.signal import resample_poly
from vosk import Model, KaldiRecognizer

from Managers import ContextManager, AssistantManager

import sounddevice as sd
import numpy as np

import json
import queue
import argparse
# import signal
import threading
import hashlib
import os

import threads

# ======================
# AUDIO SETTINGS
# ======================
DEVICE = 6
IN_RATE = 44100
OUT_RATE = 16000

# ======================
# ARGUMENTS
# ======================

parser = argparse.ArgumentParser(description="Voice Assistant")
parser.add_argument("--about", help="Show information about the program", action="store_true")
parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
parser.add_argument("-c", "--config", type=str, default="config.json", help="Path to the config file")

args = parser.parse_args()

# =====================
# CONTEXT
# =====================

context_manager = ContextManager(config_file=args.config, args=args)


# =====================
# PLUGINS
# =====================

plugin_manager = AssistantManager(Context=context_manager)
context_manager.plugin_manager = plugin_manager

# ======================
# HASH CHECK
# ======================
if not os.path.exists("hashsum.json"):
    context_manager.Libs.logger.error("⚠️ Hash sum file not found! Please run 'python preprocessing.py' to generate it.")
    exit(1)
hash_sums = json.load(open("hashsum.json", "r", encoding="utf-8"))
for pluginF in os.listdir("PluginSystem"):
    if not os.path.isdir(f"PluginSystem/{pluginF}") or pluginF.startswith("!") or pluginF.startswith("__") or pluginF == "Cache":
        continue
    for file in os.listdir(f"PluginSystem/{pluginF}"):
        if file.endswith(".yaml"):
            hash_value = hashlib.sha256(open(f"PluginSystem/{pluginF}/{file}", "rb").read()).hexdigest()
            context_manager.Libs.logger.info(f"Hash for {pluginF}/{file}: {hash_value}")
            try:
                hash_check_fail = hash_value != hash_sums.get(f"{pluginF}/{file}")
            except KeyError:
                hash_check_fail = True
                context_manager.Libs.logger.warning(f"⚠️ Hash not found for {pluginF}/{file}!")
                exit(1)
            if hash_check_fail:
                if args.debug:
                    context_manager.Libs.logger.info(f"⚠️ Hash mismatch for {pluginF}/{file}! Expected: {hash_sums.get(f'{pluginF}/{file}')}, Got: {hash_value}")
                context_manager.Libs.logger.info("Please rebuild sklearn model with 'python preprocessing.py' for update hashes")
                exit(1)

# ======================
# MODELS
# ======================

stt_model = Model(context_manager.STT.get("Model"))
STTqueue = queue.Queue()
rec = KaldiRecognizer(stt_model, 16000, plugin_manager.getGrammarForSTT())

# ======================
# THREAD HYPERVISOR
# ======================

HyperVisorThread = threading.Thread(target=threads.hypervisorThread, args=(context_manager,), daemon=True)
HyperVisorThread.start()


# ======================
# CALLBACK
# ======================
def callback(indata, frames, time, status):
    if status:
        context_manager.Libs.logger.info(status)

    audio = indata[:, 0]
    resampled = resample_poly(audio, OUT_RATE, IN_RATE).astype(np.int16)

    STTqueue.put(resampled.tobytes())

# def kill_signal_handler(sig, frame):
#     context_manager.Libs.logger.info(f"Received termination signal {sig}. Stopping threads...")
#     context_manager.Libs.logger.info("🛑 Terminating...")
#     context_manager.stopEvent.set()
#     ConfidenceThread.join()
#     AudioThread.join()
#     if context_manager.TTS.get("Enabled"):
#         TTSThread.join()
#     context_manager.Libs.logger.info("Successfully terminated.")
#     exit(0)

# signal.signal(signal.SIGINT, kill_signal_handler)
# signal.signal(signal.SIGTERM, kill_signal_handler)


# ======================
# MAIN LOOP
# ======================
with sd.InputStream(
    device=DEVICE,
    samplerate=IN_RATE,
    channels=1,
    dtype="int16",
    callback=callback,
    blocksize=2048,
):
    context_manager.Libs.logger.info("🎤 Говори...")

    while True:
        data = STTqueue.get()
        # -------------------
        # STT (Vosk)
        # -------------------
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()
            if not text:
                continue
            context_manager.Libs.logger.trace(f"🗣 TEXT: {text}")
            context_manager.ConfidenceQueue.put(text)
        else:
            pass
        