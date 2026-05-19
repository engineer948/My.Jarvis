import keyboard
import webbrowser
import urllib.parse
import ctypes
import time

waiting_youtube = False
pending_youtube_search = ""

def focus_youtube_window():
    """
    Finds a visible browser window/tab containing 'youtube' in its title
    and brings it to the absolute foreground so that media shortcuts work.
    """
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
    ShowWindow = ctypes.windll.user32.ShowWindow

    found_hwnd = None

    def foreach_window(hwnd, lParam):
        nonlocal found_hwnd
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value.lower()
                if "youtube" in title:
                    found_hwnd = hwnd
                    return False  # stop enumeration
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    
    if found_hwnd:
        ShowWindow(found_hwnd, 9)  # SW_RESTORE (restores window if minimized)
        SetForegroundWindow(found_hwnd)
        time.sleep(0.1)  # brief sleep to guarantee focus registers
        return True
    return False

def handle_youtube(text):
    global waiting_youtube
    global pending_youtube_search

    text = text.lower().strip()

    firefox_path = r"C:\Program Files\Mozilla Firefox\firefox.exe"

    try:
        webbrowser.register(
            "firefox",
            None,
            webbrowser.BackgroundBrowser(firefox_path)
        )
    except:
        pass

    # =========================================
    # YES / NO
    # =========================================

    if waiting_youtube:
        if "yes" in text:
            query = urllib.parse.quote(pending_youtube_search)
            url = f"https://www.youtube.com/results?search_query={query}"
            
            try:
                webbrowser.get("firefox").open(url)
            except:
                webbrowser.open(url)

            print(f"Searching on YouTube: {pending_youtube_search}")

            waiting_youtube = False
            pending_youtube_search = ""
            return True

        elif "no" in text:
            print("Cancelled")
            waiting_youtube = False
            pending_youtube_search = ""
            return True

    # =========================================
    # SEARCH COMMAND
    # =========================================

    # Explicit, clean triggers for YouTube search
    query = None
    if text.startswith("youtube search "):
        query = text[len("youtube search "):].strip()
    elif text.startswith("search youtube "):
        query = text[len("search youtube "):].strip()
    else:
        for suffix in (" on youtube", " youtube", " on you tube", " you tube"):
            if text.endswith(suffix):
                possible_query = text[:-len(suffix)].strip()
                if possible_query.startswith("search "):
                    query = possible_query[len("search "):].strip()
                else:
                    query = possible_query
                break

    if query:
        pending_youtube_search = query
        print(f'YouTube search: "{pending_youtube_search}" — confirm? (yes/no)')
        waiting_youtube = True
        return True

    # =========================================
    # PLAY / STOP
    # =========================================

    if "play video" in text:
        if focus_youtube_window():
            keyboard.send("k")
            print("Video played")
        else:
            print("YouTube window not found")
        return True

    if "stop video" in text:
        if focus_youtube_window():
            keyboard.send("k")
            print("Video stopped")
        else:
            print("YouTube window not found")
        return True

    # =========================================
    # NEXT / PREVIOUS
    # =========================================

    if "next video" in text:
        if focus_youtube_window():
            keyboard.send("shift+n")
            print("Next video")
        else:
            print("YouTube window not found")
        return True

    if "previous video" in text:
        if focus_youtube_window():
            keyboard.send("shift+p")
            print("Previous video")
        else:
            print("YouTube window not found")
        return True

    # =========================================
    # VOLUME
    # =========================================

    if "adjust youtube volume" in text or "increase youtube volume" in text:
        if focus_youtube_window():
            keyboard.send("up")
            keyboard.send("up")
            print("YouTube volume increased by 10%")
        else:
            print("YouTube window not found")
        return True

    if "reduce youtube volume" in text or "decrease youtube volume" in text:
        if focus_youtube_window():
            keyboard.send("down")
            keyboard.send("down")
            print("YouTube volume reduced by 10%")
        else:
            print("YouTube window not found")
        return True

    return False
