import os
import keyboard
import ctypes

waiting_spotify = False
pending_song = ""

def get_spotify_window_title_and_class():
    """
    Scans active Windows handles using standard win32 API calls via ctypes.
    Locates the Spotify window handle by its official class name 'SpotifyMainWindow'
    and extracts its exact current window title.
    """
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    GetClassName = ctypes.windll.user32.GetClassNameW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    spotify_title = None

    def foreach_window(hwnd, lParam):
        nonlocal spotify_title
        if IsWindowVisible(hwnd):
            class_buff = ctypes.create_unicode_buffer(256)
            GetClassName(hwnd, class_buff, 256)
            class_name = class_buff.value
            
            if class_name == "SpotifyMainWindow":
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    spotify_title = buff.value
                else:
                    spotify_title = ""
                return False  # Stop enumeration once found
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return spotify_title


def get_spotify_state():
    """
    Determines whether Spotify is 'closed', 'paused', or 'playing' based
    on the window presence and exact window title rules.
    """
    title = get_spotify_window_title_and_class()
    if title is None:
        return "closed"
    
    title_lower = title.lower().strip()
    # Spotify defaults to its name when paused or waiting in standby
    if title_lower in ("spotify", "spotify free", "spotify premium", "spotify unlimited"):
        return "paused"
    
    return "playing"


def handle_spotify(text):
    global waiting_spotify
    global pending_song

    text = text.lower().strip()

    # =========================================
    # YES / NO CONFIRMATION
    # =========================================
    if waiting_spotify:
        if "yes" in text:
            try:
                spotify_uri = f"spotify:search:{pending_song}"
                os.startfile(spotify_uri)
                print(f"Searching on Spotify: {pending_song}")
            except Exception as e:
                print("Spotify app not found")
                print(e)

            waiting_spotify = False
            pending_song = ""
            return True

        elif "no" in text:
            print("Cancelled")
            waiting_spotify = False
            pending_song = ""
            return True

    # =========================================
    # SEARCH & PLAY A SONG
    # =========================================
    query = None
    if text.startswith("play song "):
        query = text[len("play song "):].strip()
    elif text.startswith("play spotify "):
        query = text[len("play spotify "):].strip()
    elif text.startswith("spotify play "):
        query = text[len("spotify play "):].strip()
    elif text.endswith(" on spotify"):
        possible_query = text[:-len(" on spotify")].strip()
        if possible_query.startswith("play "):
            query = possible_query[len("play "):].strip()
        else:
            query = possible_query

    if query:
        pending_song = query
        print(f'Spotify search: "{pending_song}" — confirm? (yes/no)')
        waiting_spotify = True
        return True

    # =========================================
    # PAUSE / STOP MUSIC (Explicit Pause)
    # =========================================
    if "stop music" in text:
        keyboard.send("play/pause media")
        print("Music paused")
        return True

    # =========================================
    # PLAY MUSIC / CONTINUE (Explicit Play)
    # =========================================
    if "play music" in text:
        keyboard.send("play/pause media")
        print("Music continued")
        return True

    # =========================================
    # NEXT MUSIC
    # =========================================
    if "next music" in text:
        keyboard.send("next track")
        print("Next music")
        return True

    # =========================================
    # PREVIOUS MUSIC
    # =========================================
    if "previous music" in text:
        keyboard.send("previous track")
        print("Previous music")
        return True

    return False