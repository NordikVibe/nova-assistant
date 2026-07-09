from Managers import ContextManager
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

TARGET_SR = 48000
# ======================
# Confidence Thread
# ======================
def confidenceThread(Context: ContextManager):
    assitantActive = False
    intent_model = joblib.load(Context.Intent["Path"])
    ConfidenceQueue = Context.ConfidenceQueue
    stopEvent = Context.stopEvent
    logger = Context.Libs.logger
    logger.trace("ConfidenceThread started.")
    voice_hash = hashlib.sha256(Context.TTS['Voice'].encode('utf-8')).hexdigest()
    while not stopEvent.is_set():
        try:
            text = ConfidenceQueue.get()
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
            
            if Context.plugin_manager.intent_registry.get(intent).plugin.plugin_data.get("intents", "").get(intent, "").get("hasSlotInput", False):
                Context.Libs.logger.info(f"{intent} requires slot input. Parsing numbers from text: {text}.")
                text_with_numbers = parse(text, language="ru")
                Context.Libs.logger.info(f"Parsed text with numbers: {text_with_numbers}.")
                slots.append(re.search(r"(\d+)", text_with_numbers).group(1) if re.search(r"(\d+)", text_with_numbers) else None)
            handler = Context.plugin_manager.intent_registry[intent].handler
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
            
            ans = Context.plugin_manager.intent_registry[intent].plugin.getRandomAnswer(intent)
            if not ans:
                logger.warning(f"No response configured for intent '{intent}'.")
                continue
            if ans and "{value}" in ans and Context.plugin_manager.intent_registry.get(intent).plugin.plugin_data.get("intents", "").get(intent, "").get("hasSlotOutput", False):
                ans = ans.format(**handler_output) if handler_output else ans
            logger.trace(f"💬 RESPONSE: {ans}")
            path = f"PluginSystem/Cache/{voice_hash}/{hashlib.sha256(ans.encode('utf-8')).hexdigest()}.mp3"
            if os.path.exists(path):
                Context.AudioQueue.put(path)
            else:
                if Context.TTS.get("enabled", False):
                    Context.TTSQueue.put(ans)
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
def TTSThread(Context: ContextManager):
    tts = TTS(model_name=Context.TTS.get("Model"), progress_bar=True, gpu=False)
    voice = Context.TTS.get("Voice", None)
    tts_queue = Context.TTSQueue
    stopEvent = Context.stopEvent
    logger = Context.Libs.get("logger")
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
        Context.AudioQueue.put(audio_path)
    
def hypervisorThread(Context: ContextManager):
    ConfidenceThread = threading.Thread(target=confidenceThread, args=(Context,), daemon=True)
    ConfidenceThread.start()
    AudioThread = threading.Thread(target=audioThread, args=(Context,), daemon=True)
    AudioThread.start()
    if Context.TTS.get("enabled", False):
        TTSthread = threading.Thread(target=TTSThread, args=(Context,), daemon=True)
        TTSthread.start()