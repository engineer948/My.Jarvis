import os
import glob
import subprocess
import threading

# Common aliases for apps/games to make recognition extremely smart
APP_ALIASES = {
    "gta 5": ["grand theft auto v", "gta v", "gta5", "gtav"],
    "gta v": ["grand theft auto v", "gta 5", "gta5", "gtav"],
    "chrome": ["google chrome", "chrome browser"],
    "firefox": ["mozilla firefox", "firefox browser"],
    "word": ["microsoft word", "word office"],
    "excel": ["microsoft excel", "excel office"],
    "powerpoint": ["microsoft powerpoint", "powerpoint office"],
    "cmd": ["command prompt", "cmd.exe"],
    "notepad": ["notepad++", "notepad"],
    "steam": ["steam client", "steam"],
    "spotify": ["spotify music", "spotify client"]
}

def get_start_menu_shortcuts():
    """
    Scans the Windows Start Menu folders (both user and system-wide)
    to find all installed application shortcuts (.lnk and .url files).
    """
    shortcuts = {}
    
    # Path 1: User Start Menu
    user_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
    # Path 2: System Start Menu
    system_dir = os.path.expandvars(r"%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs")
    
    search_dirs = [user_dir, system_dir]
    
    for base_dir in search_dirs:
        if os.path.exists(base_dir):
            # Recursively find all .lnk and .url files
            for root, _, files in os.walk(base_dir):
                for file in files:
                    if file.lower().endswith(('.lnk', '.url')):
                        name_without_ext = os.path.splitext(file)[0].lower()
                        full_path = os.path.join(root, file)
                        shortcuts[name_without_ext] = full_path
                        
    return shortcuts

def find_best_match(query, shortcuts):
    """
    Fuzzy matches the query string with the collected Start Menu shortcuts.
    """
    query = query.lower().strip()
    
    # Check if there is an exact or near-exact match first
    if query in shortcuts:
        return shortcuts[query]
        
    # Check aliases
    for alias_key, aliases in APP_ALIASES.items():
        if query == alias_key or query in aliases:
            for alias in [alias_key] + aliases:
                if alias in shortcuts:
                    return shortcuts[alias]
                # Try finding substring match for alias
                for name, path in shortcuts.items():
                    if alias in name or name in alias:
                        return path

    # Substring / Token matching score
    best_match = None
    best_score = 0
    query_tokens = set(query.split())
    
    for name, path in shortcuts.items():
        name_tokens = set(name.split())
        
        # Calculate overlap
        overlap = query_tokens.intersection(name_tokens)
        score = len(overlap)
        
        # Give extra points if query is a direct substring of the name
        if query in name:
            score += 2
            
        # Give extra points for prefix match
        if name.startswith(query):
            score += 1
            
        if score > best_score:
            best_score = score
            best_match = path
            
    if best_score > 0:
        return best_match
        
    return None

def handle_app(text):
    """
    Handles voice commands to open windows apps.
    Usage: "open chrome", "open gta 5", "run steam", etc.
    """
    text = text.lower().strip()
    
    # Supported triggers
    triggers = ["open ", "run ", "start ", "launch "]
    target_app = ""
    
    for trigger in triggers:
        if text.startswith(trigger):
            target_app = text[len(trigger):].strip()
            break
            
    if not target_app:
        return False
        
    # Remove unnecessary words
    target_app = target_app.replace(" app", "").replace(" application", "").strip()
    
    print(f"Searching for application: {target_app}...")
    
    shortcuts = get_start_menu_shortcuts()
    match_path = find_best_match(target_app, shortcuts)
    
    if match_path:
        print(f"Found app shortcut: {os.path.basename(match_path)}")
        try:
            # os.startfile resolves shortcuts (.lnk / .url) flawlessly on Windows
            os.startfile(match_path)
            print(f"Successfully launched {target_app}!")
            return True
        except Exception as e:
            print(f"Failed to open app: {e}")
            return True
    else:
        # Fallback to direct system execution for basic commands like "cmd", "notepad"
        try:
            # Try running directly as system command if start menu shortcut wasn't found
            os.startfile(target_app + ".exe")
            print(f"Launched via system fallback: {target_app}.exe")
            return True
        except:
            print(f"Application '{target_app}' not found in system or start menu.")
            
    return False
