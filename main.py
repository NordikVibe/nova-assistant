from curses import raw
from Cython.CodeWriter import CondExprNode
from scipy.signal import resample_poly
from vosk import Model, KaldiRecognizer

import sounddevice as sd
import numpy as np
import soundfile as sf

import json
import queue
import argparse
import signal
import threading

import intents

import confidenceThread
import audioThread
import TTSThread

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
parser.add_argument("-mlm", "--mlmodel", type=str, default="model.pkl", help="Path to the intent model file")
parser.add_argument("-stt", "--sttmodel", type=str, default="vosk-model-small-ru-0.22", help="Path to the STT model directory")
parser.add_argument("-ttsm", "--ttsmodel", type=str, default="tts_model", help="Path to the TTS model directory")

args = parser.parse_args()

# ======================
# MODELS
# ======================

stt_model = Model(args.sttmodel)

mgr = intents.get_intents("Plugins")
STTqueue = queue.Queue()
raw_grammar = mgr.get_grammar_by_intent()
raw_grammar.extend([
    "ноль",
    "десять",
    "двадцать",
    "тридцать",
    "сорок",
    "пятьдесят",
    "шестьдесят",
    "семьдесят",
    "восемьдесят",
    "девяносто",
    "сто"
])
grammar = json.dumps(raw_grammar, ensure_ascii=False)
rec = KaldiRecognizer(stt_model, 16000, grammar)

# ======================
# THREADING
# ======================
stopEvent = threading.Event()

ConfidenceQueue = queue.Queue()
AudioQueue = queue.Queue()
TTSQueue = queue.Queue()

ConfidenceThread = threading.Thread(target=ConfidenceThread.ConfidenceThread, args=(ConfidenceQueue, TTSQueue, AudioQueue, stopEvent, args.mlmodel, mgr), daemon=True)
ConfidenceThread.start()
AudioThread = threading.Thread(target=audioThread.audioWorker, args=(AudioQueue, stopEvent), daemon=True)
AudioThread.start()
TTSThread = threading.Thread(target=TTSThread.TTSThread, args=(TTSQueue, stopEvent), daemon=True)
TTSThread.start()


# ======================
# CALLBACK
# ======================
def callback(indata, frames, time, status):
    if status:
        print(status)

    audio = np.frombuffer(indata, dtype=np.int16)
    resampled = resample_poly(audio, OUT_RATE, IN_RATE).astype(np.int16)

    STTqueue.put(resampled.tobytes())

def kill_signal_handler(sig, frame):
    print(f"Received termination signal {sig}. Stopping threads...")
    print("🛑 Terminating...")
    stopEvent.set()
    ConfidenceThread.join()
    AudioThread.join()
    TTSThread.join()
    print("Successfully terminated.")
    exit(0)

signal.signal(signal.SIGINT, kill_signal_handler)
signal.signal(signal.SIGTERM, kill_signal_handler)


# ======================
# MAIN LOOP
# ======================
with sd.InputStream(
    device=DEVICE,
    samplerate=IN_RATE,
    channels=1,
    dtype="int16",
    callback=callback,
    blocksize=8000,
):
    print("🎤 Говори...")

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

            print(f"🗣 TEXT: {text}")
            
            ConfidenceQueue.put(text)

        else:
            pass
        