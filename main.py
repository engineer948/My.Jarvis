import json
import pyaudio
import numpy as np
import wakeword
import time

from vosk import Model, KaldiRecognizer

from search import handle_search
from spotify_control import handle_spotify
from info import handle_info
from youtube_control import handle_youtube
from app_control import handle_app

# =========================================================
# SETTINGS
# =========================================================

import sys, os

def get_model_path():
    if getattr(sys, 'frozen', False):
        bundled_model = os.path.join(sys._MEIPASS, "model")
        if os.path.exists(bundled_model):
            return bundled_model
        exe_model = os.path.join(os.path.dirname(sys.executable), "model")
        if os.path.exists(exe_model):
            return exe_model
    return "model"

MODEL_PATH = get_model_path()

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1280  # Chunk size optimized for openwakeword (80ms at 16kHz)

# =========================================================
# LOAD MODEL
# =========================================================

print("Loading model...")

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

print("Jarvis is listening...\n")

# =========================================================
# PYAUDIO
# =========================================================

p = pyaudio.PyAudio()

stream = p.open(
    format=pyaudio.paInt16,
    channels=CHANNELS,
    rate=SAMPLE_RATE,
    input=True,
    frames_per_buffer=CHUNK
)

stream.start_stream()

# =========================================================
# MAIN LOOP
# =========================================================

audio_buffer = []  # Ring buffer to prevent missing start of speech
was_active = False

while True:
    try:
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_np = np.frombuffer(data, dtype=np.int16)

        # Add chunk to sliding window buffer (up to 480ms / 6 chunks)
        audio_buffer.append(data)
        if len(audio_buffer) > 6:
            audio_buffer.pop(0)

        # Check if wake word detected in this chunk
        wakeword_detected = wakeword.check_wakeword_audio(audio_np)
        
        is_active = wakeword.is_active()

        if wakeword_detected:
            print("\n[WAKEWORD DETECTED]")

        # If wakeword was just triggered (was_active was False, now is_active is True),
        # feed the pre-roll audio buffer to Vosk so it doesn't miss the start of the sentence
        if is_active and not was_active:
            for chunk in audio_buffer:
                recognizer.AcceptWaveform(chunk)
            audio_buffer.clear()

        # If active, feed current audio to Vosk for full transcription
        if is_active:
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower().strip()

                if text:
                    print(f"\nYou said: {text}")

                    # Clean "jarvis" from text just in case it got transcribed too
                    active, clean_text = wakeword.process_text(text)
                    if clean_text:
                        # =============================================
                        # WINDOWS APPS
                        # =============================================
                        if handle_app(clean_text):
                            continue

                        # =============================================
                        # YOUTUBE
                        # =============================================
                        if handle_youtube(clean_text):
                            continue

                        # =============================================
                        # SEARCH
                        # =============================================
                        if handle_search(clean_text):
                            continue

                        # =============================================
                        # SPOTIFY
                        # =============================================
                        if handle_spotify(clean_text):
                            continue

                        # =============================================
                        # INFO
                        # =============================================
                        if handle_info(clean_text):
                            continue

                        # =============================================
                        # TEST
                        # =============================================
                        if "hello" in clean_text:
                            print("Hello sir")

        was_active = is_active

    except Exception as e:
        print(f"Error in stream: {e}")
        time.sleep(1)