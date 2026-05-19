import time
import numpy as np

# Try importing openwakeword
try:
    import openwakeword
    from openwakeword.model import Model
    # Download models if not present
    openwakeword.utils.download_models()
    oww_model = Model(wakeword_models=["hey_jarvis"], vad_threshold=0.5)
except Exception as e:
    print(f"Failed to load openwakeword: {e}")
    oww_model = None

WAKE_WORD = "jarvis"
ACTIVE_TIME = 60

jarvis_active_until = 0

def is_active():
    return time.time() < jarvis_active_until

def activate():
    global jarvis_active_until
    jarvis_active_until = time.time() + ACTIVE_TIME

def deactivate():
    global jarvis_active_until
    jarvis_active_until = 0

def process_text(text):
    text = text.lower().strip()

    # Wake word detect
    if WAKE_WORD in text:
        activate()
        # remove jarvis from sentence
        text = text.replace(WAKE_WORD, "").strip()
        return True, text

    # Already active
    if is_active():
        return True, text

    return False, text

def check_wakeword_audio(audio_frame_np):
    """
    Takes a numpy array of 1280 samples (16kHz, 16-bit PCM).
    Returns True if wake word is detected.
    """
    if oww_model is None:
        return False
        
    prediction = oww_model.predict(audio_frame_np)
    # The key might be "hey_jarvis"
    score = prediction.get("hey_jarvis", 0.0)
    if score > 0.4:  # Slightly lower threshold for better responsiveness
        activate()
        return True
    return False