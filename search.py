import webbrowser
import urllib.parse

waiting_confirmation = False
pending_search = ""

def handle_search(text):
    global waiting_confirmation, pending_search
    text = text.lower().strip()

    firefox_path = r"C:\Program Files\Mozilla Firefox\firefox.exe"
    try:
        webbrowser.register("firefox", None, webbrowser.BackgroundBrowser(firefox_path))
    except: pass

    if waiting_confirmation:
        if "yes" in text:
            url = f"https://www.google.com/search?q={urllib.parse.quote(pending_search)}"
            try: webbrowser.get("firefox").open(url)
            except: webbrowser.open(url)
            print(f"Searching: {pending_search}")
            waiting_confirmation = False; pending_search = ""
            return True
        elif "no" in text:
            print("Cancelled")
            waiting_confirmation = False; pending_search = ""
            return True

    # Match clean and explicit search triggers
    query = None
    if text.startswith("search for "):
        query = text[len("search for "):].strip()
    elif text.startswith("search "):
        query = text[len("search "):].strip()
    elif text.startswith("google search "):
        query = text[len("google search "):].strip()
    elif text.startswith("google "):
        query = text[len("google "):].strip()
    elif text.startswith("look up "):
        query = text[len("look up "):].strip()
    elif text.startswith("find "):
        query = text[len("find "):].strip()

    if query:
        pending_search = query
        print(f'Search: "{pending_search}" — confirm? (yes/no)')
        waiting_confirmation = True
        return True

    return False