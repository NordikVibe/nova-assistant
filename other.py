import re

import sklearn
import sklearn.pipeline
import sounddevice as sd
import soundfile as sf
import numpy as np
import librosa

TARGET_SR = 48000

def probe_intent(model: sklearn.pipeline.Pipeline, text: str) -> tuple[str, float]:
    intent = model.predict([text])[0]

    """ proba = model.predict_proba([text])[0]
    
    for cls, prob in zip(model.classes_, proba):
        print(f"{cls}: {prob:.2f}")
    confidence = max(proba) """
    
    probs = model.predict_proba([text])[0]

    best_idx = probs.argmax()
    best_prob = probs[best_idx]

    sorted_probs = sorted(probs, reverse=True)

    gap = sorted_probs[0] - sorted_probs[1]

    if best_prob < 0.4:
        return "UNKNOWN", best_prob

    elif gap < 0.15:
        return "UNKNOWN", best_prob

    else:
        return intent, best_prob

def extract_slots(text, intent=None) -> dict[str, str]:
    slots = {}
    num_in_text = False
    numbers = {
        "ноль": 0,
        "десять": 10,
        "двадцать": 20,
        "тридцать": 30,
        "сорок": 40,
        "пятьдесят": 50,
        "шестьдесят": 60,
        "семьдесят": 70,
        "восемьдесят": 80,
        "девяносто": 90,
        "сто": 100
        }
    print(f"🔍 Extracting slots for intent '{intent}'...")
    
    if intent == "SET_VOLUME" or intent == "CHANGE_VOLUME_DOWN" or intent == "CHANGE_VOLUME_UP":
        for num in numbers:
            if num in text:
                num_in_text = True
                
        if num_in_text:
            for num in numbers:
                if num in text:
                    slots["volume"] = numbers[num]
                    print(f"🔢 SLOT: volume = {slots['volume']}")
                    return slots
    if intent == "SET_VOLUME" or intent == "CHANGE_VOLUME_DOWN" or intent == "CHANGE_VOLUME_UP":
        if "немного" in text:
            slots["volume"] = "10"
        m = re.search(r"(\d+)", text)
        if m:
            slots["volume"] = int(m.group(1))
        return slots

def execute_handler(handler, slots: dict[str, str] = None):
    if handler:
        handler(slots or {})
    return None

def mask_text(text):
    toMask = [
        "немного",
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
    ]
    for item in toMask:
        text = re.sub(item, "<MASK>", text)
    return re.sub(r"\d+", "<MASK>", text)

def playAudio(file_path: str):
    data, sr = sf.read(file_path)
    sd.play(data, sr)
    
def normalize_and_overwrite(path: str):
    data, sr = sf.read(path)
    data = data.astype(np.float32)
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    if sr != TARGET_SR:
        data = librosa.resample(
            data,
            orig_sr=sr,
            target_sr=TARGET_SR
        )
        sr = TARGET_SR
    data = np.nan_to_num(data)
    sf.write(path, data, sr)

    return path, sr