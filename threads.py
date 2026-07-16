from Managers import ContextManager
from functools import partial
from scipy.signal import resample_poly
import joblib
from number_parser import parse
import re
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
from telegram import TelegramThread

TARGET_SR = 48000
INPUT_SR = 44100
# ======================
# Confidence Thread
# ======================
def confidenceThread(contextManager: ContextManager):
    logger = contextManager.context.libraries.logger
    logger.trace("ConfidenceThread started.")
    assitantActive = False
    intent_model = joblib.load(contextManager.context.config.IntentModel.modelPath)
    stopEvent = contextManager.context.stopEvent
    plugin_manager = contextManager.context.plugin_manager
    voice_hash = hashlib.sha256(contextManager.config.TTS.Voice.encode('utf-8')).hexdigest()
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
            
            if plugin_manager.intent_registry.get(intent).plugin.plugin_data.get("intents", "").get(intent, "").get("hasSlotInput", False):
                logger.info(f"{intent} requires slot input. Parsing numbers from text: {text}.")
                text_with_numbers = parse(text, language="ru")
                logger.info(f"Parsed text with numbers: {text_with_numbers}.")
                slots.append(re.search(r"(\d+)", text_with_numbers).group(1) if re.search(r"(\d+)", text_with_numbers) else None)
            handler = plugin_manager.intent_registry[intent].handler
            if not handler:
                logger.warning(f"No handler found for intent '{intent}'.")

            if intent == "ACTIVATE":
                assitantActive = True
                logger.info("🟢 Assistant activated.")
            
            if handler and assitantActive and intent != "ACTIVATE":
                assitantActive = False
                logger.info(f"Executing handler for intent '{intent}'...")
                handler_output = handler(slots if slots else [None])
            else:
                logger.info(f"Handler for intent '{intent}' not executed. Assistant active: {assitantActive}, intent: {intent}.")
                handler_output = None
            
            ans = plugin_manager.intent_registry[intent].plugin.getRandomAnswer(intent)
            if re.match(r"{slot}", ans) and plugin_manager.intent_registry.get(intent).plugin.plugin_data.get("intents", "").get(intent, "").get("hasSlotOutput", False):
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
        except Exception:
            logger.exception("Confidence Crushed")
                
# ======================
# Audio Thread
# ======================
def audioThread(Context: ContextManager):
    sd.default.device = 6
    while not Context.stopEvent.is_set():
        path = Context.AudioQueue.get()  # ждём файл
        if not path:
            continue
        try:
            data, sr = sf.read(path, dtype="float32")
            sd.play(data, sr)
            sd.wait()
        except Exception as e:
            Context.Libs.logger.error(f"[AUDIO ERROR] {e}")

        Context.AudioQueue.task_done()

# ======================
# TTS Thread
# ======================
def TTSThread(contextManager: ContextManager):
    logger = contextManager.context.libraries.logger
    logger.trace("TTSThread started.")
    if contextManager.context.tts_model is None:
        logger.info("No TTS model found in context. Initializing TTS model...")
        tts = TTS(model_name=contextManager.config.TTS.Model, progress_bar=True, gpu=False)
    else:
        logger.info("TTS model found in context. Using existing TTS model.")
        tts = contextManager.context.tts_model
    voice = contextManager.config.TTS.Voice
    tts_queue = contextManager.context.TTSQueue
    stopEvent = contextManager.context.stopEvent
    voice_hash = hashlib.sha256(voice.encode('utf-8')).hexdigest()
    if not voice:
        logger.critical("[TTS ERROR] No voice specified in context.")
        exit(1)
    else:
        if Path(voice).is_file():
            def ttsSynthesize(text, output_path):
                tts.tts_to_file(text=text, output_path=output_path, language="ru", speaker_wav=voice, emotion="neutral")
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
                tts.tts_to_file(text=text, output_path=output_path, language="ru", speaker=voice, emotion="neutral")
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
    while not stopEvent.is_set():
        text = tts_queue.get()  # ждём текст
        if text is None:
            break
        logger.trace(f"🗣 TTS: {text}")
        
        audio_path = f"PluginSystem/Cache/{voice_hash}/{hashlib.sha256(text.encode('utf-8')).hexdigest()}.mp3"

        ttsSynthesize(text=text, output_path=audio_path)
        logger.trace(f"🗣 TTS audio generated: {audio_path}")
        contextManager.context.AudioQueue.put(audio_path)

def callback(indata, frames, time, status, contextManager: ContextManager):
    if status:
        contextManager.context.libraries.logger.warning(f"[STT WARNING] {status}")

    audio = indata[:, 0]
    resampled = resample_poly(audio, 16000, INPUT_SR).astype(np.int16)

    contextManager.context.STTQueue.put(resampled.tobytes())

def STTThread(contextManager: ContextManager):
    stt_model = Model(contextManager.config.STT.Model)
    STTqueue = contextManager.context.STTQueue
    stopEvent = contextManager.context.stopEvent
    logger = contextManager.context.libraries.logger
    logger.trace("STTThread started.")
    rec = KaldiRecognizer(stt_model, 16000, contextManager.context.plugin_manager.getGrammarForSTT())
    with sd.InputStream(
    device=contextManager.config.STT.InputDevice,
    samplerate=INPUT_SR,
    channels=1,
    dtype="int16",
    callback=partial(callback, contextManager=contextManager),
    blocksize=2048
    ):
        contextManager.context.libraries.logger.info("🎤 Говори...")

        while not stopEvent.is_set():
            data = STTqueue.get()
            
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if not text:
                    continue
                contextManager.context.libraries.logger.trace(f"🗣 TEXT: {text}")
                contextManager.context.ConfidenceQueue.put(text)
            else:
                pass
    
def hypervisorThread(contextManager: ContextManager):
    if contextManager.config.IntentModel.enabled:
        ConfidenceThread = threading.Thread(target=confidenceThread, args=(contextManager,), daemon=True)
        ConfidenceThread.start()
    if contextManager.config.Audio.enabled:
        AudioThread = threading.Thread(target=audioThread, args=(contextManager,), daemon=True)
        AudioThread.start()
    if contextManager.config.STT.enabled:
        sttThread = threading.Thread(target=STTThread, args=(contextManager,), daemon=True)
        sttThread.start()
    if contextManager.config.TTS.enabled:
        TTSthread = threading.Thread(target=TTSThread, args=(contextManager,), daemon=True)
        TTSthread.start()
    if contextManager.config.Telegram.enabled:
        telegramThread = threading.Thread(target=TelegramThread, args=(contextManager,), daemon=True)
        telegramThread.start()