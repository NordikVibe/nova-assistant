import queue
import other
import joblib
import intents
import threading

def ConfidenceThread(ConfidenceQueue: queue.Queue, tts_queue: queue.Queue, audio_queue: queue.Queue, stopEvent: threading.Event, intent_model_path: str, mgr: intents.IntentManager):
    intent_model = joblib.load(intent_model_path)
    while not stopEvent.is_set():
        text = ConfidenceQueue.get()
        if text is None:
            break
        
        print(f"ConfidenceThread received: {text}")
        
        intent, confidence = other.probe_intent(intent_model, text)
        
        print(f"🧠 INTENT: {intent} ({confidence:.2f})")
        
        handler = mgr.get_handler_by_intent(intent)
        
        if intent in ["SET_VOLUME", "CHANGE_VOLUME_DOWN", "CHANGE_VOLUME_UP"]:
            slots = other.extract_slots(text, intent)
        else:
            slots = {}
        
        if intent == "ACTIVATE":
            active = True
            print("🟢 Assistant activated.")
        if handler and active and not intent == "ACTIVATE":
            active = False
            other.execute_handler(handler, slots)
        
        ans = mgr.get_random_response_by_intent(intent)
        if isinstance(ans, list):
            print(f"💬 RESPONSE: {ans[0]}")
            tts_queue.put(ans[0])
        elif isinstance(ans, str):
            print(f"💬 RESPONSE: {ans}")
            audio_queue.put(ans)