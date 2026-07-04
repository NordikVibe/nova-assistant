import queue
import threading
import TTS

AUDIO_PATH = "tmp.wav"

def TTSThread(tts_queue: queue.Queue, stopEvent: threading.Event):
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True, gpu=False)
    while not stopEvent.is_set():
        text = tts_queue.get()  # ждём текст
        if text is None:
            break
        print(f"🗣 TTS: {text}")
        
        tts.tts_to_file(text=text, output_path=AUDIO_PATH, language="ru", speaker_wav="audio_2026-06-29_23-04-48.ogg", emotion="neutral")
        print(f"🗣 TTS audio generated: {AUDIO_PATH}")