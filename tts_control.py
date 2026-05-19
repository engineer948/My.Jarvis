import win32com.client
import threading
import json
import os

CONFIG_FILE = "config.json"
_speaking_active = False

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"tts_enabled": True}

def save_settings(settings_dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings_dict, f, indent=4)
    except:
        pass

_settings = load_settings()

def is_tts_enabled():
    return _settings.get("tts_enabled", True)

def set_tts_enabled(enabled):
    _settings["tts_enabled"] = enabled
    save_settings(_settings)

def is_currently_speaking():
    """Returns True if the assistant is currently outputting speech audio."""
    global _speaking_active
    return _speaking_active

def _speak_worker(text):
    global _speaking_active
    _speaking_active = True
    try:
        import pythoncom
        pythoncom.CoInitialize()
        
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(text)
    except Exception as e:
        print(f"TTS Thread Error: {e}")
    finally:
        _speaking_active = False

def speak(text):
    """
    Speaks the given text asynchronously in a background thread
    if TTS feedback is enabled in the configuration settings.
    """
    if is_tts_enabled():
        thread = threading.Thread(target=_speak_worker, args=(text,), daemon=True)
        thread.start()
