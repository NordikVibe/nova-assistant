import scipy as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from TTS.api import TTS
import soundfile as sf
import joblib
import intents
import torch
from other import normalize_and_overwrite

tensor_cache = torch.load("speaker.pt", map_location="cpu")

def synthesize(model: TTS, text: str, output_path: str = "output.wav", language: str = "ru", speaker_wav: str = None, emotion: str = None, tensor: dict = tensor_cache):
    model.tts_to_file(text=text, speaker_wav=speaker_wav, language=language, file_path=output_path, emotion=emotion)
    normalize_and_overwrite(output_path)
    

model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), max_features=1000),
    LogisticRegression(max_iter=1000)
)

mgr = intents.get_intents("Plugins")

text, intent = mgr.get_learning_data()

model.fit(text, intent)
joblib.dump(model, "model.pkl")

tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True, gpu=False)

print("[+] Generating audio responses...")

for response in mgr.get_preprocess_text_answers():
    print(f"[+] Generating audio for intent: {response['path']}")
    for text in response["response"]:
        print(f"[+] Generating audio for text: {text}")
        output_path = f"{response['path']}/response_{text[1]}.mp3"
        synthesize(model=tts, text=text[0], output_path=output_path, language="ru", speaker_wav="audio_2026-06-29_23-04-48.ogg", emotion="neutral")

