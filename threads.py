from Managers import ContextManager
from scipy.signal import resample_poly
import joblib
from number_parser import parse
import re
import time
from pyrnnoise import RNNoise
import hashlib
import os
import sounddevice as sd
import soundfile as sf
import TTS
from pathlib import Path
import numpy as np
import librosa
import threading
import json
from vosk import Model, KaldiRecognizer

TARGET_SR = 48000
INPUT_SR = 48000


# ======================
# Confidence Thread
# ======================
def confidenceWorker(contextManager: ContextManager):
    logger = contextManager.context.libraries.logger
    logger.trace("ConfidenceThread started.")
    assistantActive = False
    intent_model = joblib.load(contextManager.config.IntentModel.model_path)
    stopEvent = contextManager.context.stopEvent
    plugin_manager = contextManager.context.plugin_manager
    voice_hash = hashlib.sha256(
        contextManager.config.TTS.voice.encode("utf-8")
    ).hexdigest()
    while not stopEvent.is_set():
        try:
            text = contextManager.context.ConfidenceQueue.get()
            slots = []
            if text is None:
                continue

            intent = intent_model.predict([text])[0]
            probs = intent_model.predict_proba([text])[0]

            probe = probs.argmax()
            best_prob = probs[probe]

            sorted_probs = sorted(probs, reverse=True)

            gap = sorted_probs[0] - sorted_probs[1]

            if best_prob < 0.4 or gap < 0.15:
                intent = "UNKNOWN"

            logger.info(f"🧠 INTENT: {intent} ({best_prob:.2f})")

            if intent == "UNKNOWN":
                continue

            if (
                plugin_manager.intent_registry.get(intent)
                .plugin.plugin_data.get("intents", "")
                .get(intent, "")
                .get("hasSlotInput", False)
            ):
                logger.info(
                    f"{intent} requires slot input. Parsing numbers from text: {text}."
                )
                text_with_numbers = parse(text, language="ru")
                logger.info(f"Parsed text with numbers: {text_with_numbers}.")
                slots.append(
                    re.search(r"(\d+)", text_with_numbers).group(1)
                    if re.search(r"(\d+)", text_with_numbers)
                    else 0
                )
            handler = plugin_manager.intent_registry[intent].handler
            if not handler:
                logger.warning(f"No handler found for intent '{intent}'.")

            if intent == "ACTIVATE":
                assistantActive = True
                logger.info("🟢 Assistant activated.")
            
            assistantActive = True
            
            # Temporarily disable deactivation but now its cringe

            if handler and assistantActive and intent != "ACTIVATE":
                # assistantActive = False
                logger.info(f"Executing handler for intent '{intent}'...")
                handler_output = handler(slots if slots else [0])
            else:
                logger.info(
                    f"Handler for intent '{intent}' not executed. Assistant active: {assistantActive}, intent: {intent}."
                )
                handler_output = None

            ans = plugin_manager.intent_registry[intent].plugin.getRandomAnswer(intent)
            if re.match(r"{slot}", ans) and plugin_manager.intent_registry.get(
                intent
            ).plugin.plugin_data.get("intents", "").get(intent, "").get(
                "hasSlotOutput", False
            ):
                ans = ans.format(**handler_output) if handler_output else ans
            logger.trace(f"💬 RESPONSE: {ans}")
            path = f"PluginSystem/Cache/{voice_hash}/{hashlib.sha256(ans.encode('utf-8')).hexdigest()}.mp3"
            if os.path.exists(path):
                contextManager.context.AudioQueue.put(path)
            else:
                if contextManager.config.TTS.enabled:
                    contextManager.context.TTSQueue.put(ans)
                else:
                    logger.warning("TTS is disabled. Cannot generate audio response.")
            contextManager.context.ConfidenceQueue.task_done()
        except Exception as e:
            logger.exception(f"Confidence Crushed: {str(e)}")


# ======================
# Audio Thread
# ======================
def audioWorker(contextManager: ContextManager):
    contextManager.context.libraries.logger.trace("AudioThread started.")
    
    while not contextManager.context.stopEvent.is_set():
        path = contextManager.context.AudioQueue.get()  # ждём файл
        if not path:
            continue
        try:
            data, sr = sf.read(path, dtype="float32")
            sd.play(data, sr)
            sd.wait()
        except Exception as e:
            contextManager.context.libraries.logger.error(f"[AUDIO ERROR] {e}")

        contextManager.context.AudioQueue.task_done()


# ======================
# TTS Thread
# ======================
def TTSWorker(contextManager: ContextManager):
    logger = contextManager.context.libraries.logger
    logger.trace("TTSThread started.")
    if contextManager.context.tts_model is None:
        logger.info("No TTS model found in context. Initializing TTS model...")
        tts = TTS(
            model_name=contextManager.config.TTS.model_path,
            progress_bar=True,
            gpu=False,
        )
    else:
        logger.info("TTS model found in context. Using existing TTS model.")
        tts = contextManager.context.tts_model
    voice = contextManager.config.TTS.Voice
    tts_queue = contextManager.context.TTSQueue
    stopEvent = contextManager.context.stopEvent
    voice_hash = hashlib.sha256(voice.encode("utf-8")).hexdigest()
    if not voice:
        logger.critical("[TTS ERROR] No voice specified in context.")
        exit(1)
    else:
        if Path(voice).is_file():

            def ttsSynthesize(text, output_path):
                tts.tts_to_file(
                    text=text,
                    output_path=output_path,
                    language="ru",
                    speaker_wav=voice,
                    emotion="neutral",
                )
                data, sr = sf.read(output_path)
                data = data.astype(np.float32)
                if data.ndim > 1:
                    data = np.mean(data, axis=1)
                if sr != TARGET_SR:
                    data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
                data = np.nan_to_num(data)
                sf.write(output_path, data, TARGET_SR)
        else:

            def ttsSynthesize(text, output_path):
                tts.tts_to_file(
                    text=text,
                    output_path=output_path,
                    language="ru",
                    speaker=voice,
                    emotion="neutral",
                )
                data, sr = sf.read(output_path)
                data = data.astype(np.float32)
                if data.ndim > 1:
                    data = np.mean(data, axis=1)
                if sr != TARGET_SR:
                    data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
                data = np.nan_to_num(data)
                sf.write(output_path, data, TARGET_SR)

    while not stopEvent.is_set():
        text = tts_queue.get()  # ждём текст
        if text is None:
            break
        logger.trace(f"🗣 TTS: {text}")

        audio_path = f"PluginSystem/Cache/{voice_hash}/{hashlib.sha256(text.encode('utf-8')).hexdigest()}.mp3"

        ttsSynthesize(text=text, output_path=audio_path)
        logger.trace(f"🗣 TTS audio generated: {audio_path}")
        contextManager.context.AudioQueue.put(audio_path)

class STTclass:
    def __init__(self, contextManager: ContextManager):
        self.contextManager = contextManager
        self.stt_model = Model(contextManager.config.STT.model_path)
        self.recognizer = KaldiRecognizer(
            self.stt_model, 16000, contextManager.context.plugin_manager.getGrammarForSTT()
        )
        self.logger = contextManager.context.libraries.logger
        self.STTqueue = contextManager.context.STTQueue
        self.stopEvent = contextManager.context.stopEvent
        self.logger.trace("STTclass initialized.")

        self.denoiser = RNNoise()
    
    def callback(self, indata, frames, time, status):
        
        audio = indata[:, 0]
        
        audio = audio.astype(np.float32) / 32768.0

        # шумодав
        audio = self.denoiser.process_frame(audio)

        # обратно в int16
        audio = (audio * 32767).astype(np.int16)
        
        resampled = resample_poly(audio, 16000, INPUT_SR).astype(np.int16)

        self.contextManager.context.STTQueue.put(resampled.tobytes())
        
        self.contextManager.context.libraries.logger.trace(f"STT audio chunk received: {len(resampled)} samples, resampled to 16kHz.")
    
    
    def STTWorker(self):
        stt_model = Model(self.contextManager.config.STT.model_path)
        logger = self.contextManager.context.libraries.logger
        logger.trace("STTThread started.")
        logger.trace("Creating recognizer")
        iter_num = 0
        rec = KaldiRecognizer(
            stt_model, 16000, self.contextManager.context.plugin_manager.getGrammarForSTT()
        )
        logger.trace("Opening InputStream")
        with sd.InputStream(
            device=self.contextManager.config.STT.input_device,
            samplerate=INPUT_SR,
            channels=1,
            dtype="int16",
            callback=self.callback,
            blocksize=480,
        ):
            self.contextManager.context.libraries.logger.info("🎤 Говори...")

            while not self.contextManager.context.stopEvent.is_set():

                data = self.contextManager.context.STTQueue.get()
                if data is None:
                    break
                if iter_num % 10 == 0:
                    self.contextManager.context.libraries.logger.trace(f"Got audio {len(data)} bytes from STTQueue.")

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if not text:
                        continue
                    self.contextManager.context.libraries.logger.trace(f"🗣 TEXT: {text}")
                    self.contextManager.context.ConfidenceQueue.put(text)
                else:
                    self.contextManager.context.libraries.logger.trace(rec.PartialResult())


def hypervisorThread(contextManager: ContextManager):
    contextManager.context.libraries.logger.trace("HypervisorThread started.")
    threads_info = []
    thread_list = []
    if contextManager.config.STT.enabled:
        stt_instance = STTclass(contextManager)
        threads_info.append({"args": (), "target": stt_instance.STTWorker, "name": "STTThread"})
    
    if contextManager.config.TTS.enabled:
        threads_info.append({"args": (contextManager,), "target": TTSWorker, "name": "TTSThread"})
    
    if contextManager.config.IntentModel.enabled:
        threads_info.append({"args": (contextManager,), "target": confidenceWorker, "name": "ConfidenceThread"})
    
    if contextManager.config.Audio.enabled:
        threads_info.append({"args": (contextManager,), "target": audioWorker, "name": "AudioThread"})
    
    for thread_info in threads_info:
        thread = threading.Thread(
            target=thread_info["target"],
            args=thread_info["args"],
            name=thread_info["name"],
            daemon=True,
        )
        thread.start()
        thread_list.append(thread)
        contextManager.context.libraries.logger.info(f"Started {thread_info['name']}.")
    
    while not contextManager.context.stopEvent.is_set():
        for thread in thread_list:
            if not thread.is_alive():
                thread_info = threads_info[thread_list.index(thread)]
                contextManager.context.libraries.logger.warning(f"{thread.name} has stopped unexpectedly. Restarting...")
                new_thread = threading.Thread(
                    target=thread_info["target"],
                    args=thread_info["args"],
                    name=thread_info["name"],
                    daemon=True,
                )
                new_thread.start()
                thread_list[thread_list.index(thread)] = new_thread
                contextManager.context.libraries.logger.info(f"Restarted {thread.name}.")
    
    
