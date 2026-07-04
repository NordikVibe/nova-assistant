import sounddevice as sd
import soundfile as sf

def audio_worker(audio_queue, stopEvent):
    while not stopEvent.is_set():
        path = audio_queue.get()  # ждём файл

        try:
            data, sr = sf.read(path, dtype="float32")

            sd.play(data, sr)
            sd.wait()

        except Exception as e:
            print(f"[AUDIO ERROR] {e}")

        audio_queue.task_done()