import customtkinter as ctk
import tkinter as tk
import threading, json, pyaudio, audioop, time, math, random, requests
from datetime import datetime
from vosk import Model, KaldiRecognizer
import wakeword, numpy as np
from search import handle_search
from spotify_control import handle_spotify
from info import handle_info
from youtube_control import handle_youtube
from app_control import handle_app

BG = "#020810"; BLUE = "#00d4ff"; CYAN = "#00eeff"; TEAL = "#00ccaa"; RED = "#ff3344"


class JarvisUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("J.A.R.V.I.S."); self.geometry("1280x800"); self.minsize(960, 640)
        ctk.set_appearance_mode("dark")
        self.is_active = False; self.audio_alive = True
        self.is_thinking = False; self.current_rms = 0; self.mic_muted = False
        self.rms_history = [0.0] * 80; self.scan_y = 0; self.ring_angle = 0.0
        self.display_text = ""; self.display_text_time = 0
        self.weather_info = "Syncing..."; self.activation_start = None
        self.boot_dur = 5.5; self.log_lines = []
        self.pwr_pos = None; self.mic_pos = None; self.tts_pos = None; self.entry_shown = False

        self.dust = [{'a': random.uniform(0, math.pi*2), 'r': random.uniform(185, 360),
                      'spd': random.uniform(0.002, 0.007)*random.choice([-1,1]),
                      'sz': random.uniform(1, 2.5), 'al': random.uniform(0.08, 0.40)} for _ in range(55)]

        self.data_dots = [{'ang': random.uniform(0, math.pi*2),
                           'spd': random.uniform(0.018, 0.040)*random.choice([-1,1]),
                           'sz': random.uniform(1.5, 3.0)} for _ in range(22)]

        self.mods = [
            {'name':'NEURAL NET','icon':'NN', 'col':BLUE,      'ang':math.radians(270),'spd':0.005,'ri':0.0},
            {'name':'AUDIO SYS', 'icon':'AU', 'col':CYAN,      'ang':math.radians(330),'spd':0.005,'ri':0.0},
            {'name':'WEB SEARCH','icon':'NET','col':TEAL,       'ang':math.radians(30), 'spd':0.005,'ri':0.0},
            {'name':'MEDIA CTRL','icon':'MC', 'col':'#4499ff',  'ang':math.radians(90), 'spd':0.005,'ri':0.0},
            {'name':'KNOWLEDGE', 'icon':'KB', 'col':'#88aaff',  'ang':math.radians(150),'spd':0.005,'ri':0.0},
            {'name':'ENV DATA',  'icon':'ENV','col':'#00bbaa',  'ang':math.radians(210),'spd':0.005,'ri':0.0},
        ]

        threading.Thread(target=self._weather, daemon=True).start()
        self._setup_ui()
        threading.Thread(target=self._audio_loop, daemon=True).start()
        self._draw()

    def _setup_ui(self):
        self.configure(fg_color=BG)
        f = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        f.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._click)
        self.entry = ctk.CTkEntry(f, placeholder_text="COMMAND INPUT...", height=40,
            font=("Consolas", 13), fg_color="#04080f", text_color=BLUE,
            border_color="#143050", border_width=1, corner_radius=5)
        self.entry.bind("<Return>", lambda e: self._send())

    def _weather(self):
        while True:
            try:
                d = requests.get("https://wttr.in/?format=j1", timeout=5).json()
                self.weather_info = f"{d['current_condition'][0]['temp_C']}°C  {d['current_condition'][0]['weatherDesc'][0]['value']}"
            except: self.weather_info = "--°C"
            time.sleep(1800)

    def log(self, m):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {m}")
        self.log_lines.append(f"[{ts}] {m}")
        if len(self.log_lines) > 7: self.log_lines.pop(0)

    def trigger_display(self, t): self.display_text = t; self.display_text_time = time.time()

    def _fc(self, col, f):
        f = max(0.0, min(1.0, f)); c = col.lstrip('#')
        return f"#{int(int(c[0:2],16)*f):02x}{int(int(c[2:4],16)*f):02x}{int(int(c[4:6],16)*f):02x}"

    def _click(self, e):
        if self.pwr_pos:
            bx, by, br = self.pwr_pos
            if math.hypot(e.x-bx, e.y-by) <= br+6: self._deactivate(); return
        if self.mic_pos:
            bx, by, br = self.mic_pos
            if math.hypot(e.x-bx, e.y-by) <= br+6: self._toggle_mute(); return
        if hasattr(self, "tts_pos") and self.tts_pos:
            bx, by, br = self.tts_pos
            if math.hypot(e.x-bx, e.y-by) <= br+6: self._toggle_tts(); return
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if not self.is_active and math.hypot(e.x-w/2, e.y-h/2) <= 155: self._activate()

    def _activate(self):
        self.is_active = True; self.activation_start = time.time(); self.log("SYSTEM ACTIVATING")

    def _deactivate(self):
        self.is_active = False; self.activation_start = None; self.log("SYSTEM STANDBY")

    def _toggle_mute(self):
        self.mic_muted = not self.mic_muted
        self.log("MIC MUTED" if self.mic_muted else "MIC LIVE")

    def _toggle_tts(self):
        import tts_control
        new_state = not tts_control.is_tts_enabled()
        tts_control.set_tts_enabled(new_state)
        self.log("TTS VOICE ENABLED" if new_state else "TTS VOICE MUTED")

    def _process(self, text):
        self.is_thinking = True
        for fn in [handle_app, handle_youtube, handle_search, handle_spotify, handle_info]:
            if fn(text): self.is_thinking = False; return
        if "hello" in text: self.log("JARVIS: Hello, sir.")
        self.is_thinking = False

    def _send(self):
        text = self.entry.get().strip().lower()
        if text:
            self.entry.delete(0, "end"); wakeword.activate()
            self.trigger_display(f"► {text}")
            threading.Thread(target=self._process, args=(text,), daemon=True).start()

    # ── DRAW METHODS ─────────────────────────────────────

    def _circ_btn(self, x, y, r, icon_type, col, pulse_col=None):
        t = time.time()
        pc = pulse_col or col
        self.canvas.create_oval(x-r-8, y-r-8, x+r+8, y+r+8, outline=self._fc(pc, 0.08))
        self.canvas.create_oval(x-r-3, y-r-3, x+r+3, y+r+3, outline=self._fc(pc, 0.15))
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=self._fc("#040c18", 0.95),
                                outline=self._fc(col, 0.7), width=2)
        arc_s = (t*60) % 360
        self.canvas.create_arc(x-r, y-r, x+r, y+r, start=arc_s, extent=35,
                               outline=self._fc(col, 0.9), width=2, style=tk.ARC)
        
        # Vector Graphic Icons
        if icon_type == "pwr":
            # Power Icon (Circle with top cut + vertical line)
            self.canvas.create_arc(x-9, y-9, x+9, y+9, start=120, extent=300, 
                                   outline=self._fc(col, 0.95), width=2.5, style=tk.ARC)
            self.canvas.create_line(x, y-12, x, y+2, fill=self._fc(col, 0.95), width=2.5)
        elif icon_type == "mic_live":
            # Microphone Shape: vertical pill, cup, stem, base
            self.canvas.create_line(x, y-7, x, y+1, fill=self._fc(col, 0.95), width=6, capstyle=tk.ROUND)
            self.canvas.create_arc(x-8, y-6, x+8, y+4, start=180, extent=180, 
                                   outline=self._fc(col, 0.95), width=2, style=tk.ARC)
            self.canvas.create_line(x, y+4, x, y+9, fill=self._fc(col, 0.95), width=2)
            self.canvas.create_line(x-6, y+9, x+6, y+9, fill=self._fc(col, 0.95), width=2)
        elif icon_type == "mic_muted":
            # Microphone Shape in red with diagonal ban strike
            self.canvas.create_line(x, y-7, x, y+1, fill=self._fc(col, 0.6), width=6, capstyle=tk.ROUND)
            self.canvas.create_arc(x-8, y-6, x+8, y+4, start=180, extent=180, 
                                   outline=self._fc(col, 0.6), width=2, style=tk.ARC)
            self.canvas.create_line(x, y+4, x, y+9, fill=self._fc(col, 0.6), width=2)
            self.canvas.create_line(x-6, y+9, x+6, y+9, fill=self._fc(col, 0.6), width=2)
            self.canvas.create_line(x-12, y-12, x+12, y+12, fill=self._fc(RED, 0.95), width=3)
        elif icon_type == "speaker_on":
            # Speaker shape with audio wave lines
            self.canvas.create_polygon(x-8, y-4, x-4, y-4, x, y-8, x, y+8, x-4, y+4, x-8, y+4,
                                       fill=self._fc(col, 0.95), outline=self._fc(col, 0.95), width=1)
            self.canvas.create_arc(x-3, y-6, x+5, y+6, start=-60, extent=120, outline=self._fc(col, 0.95), width=2, style=tk.ARC)
            self.canvas.create_arc(x-5, y-10, x+9, y+10, start=-60, extent=120, outline=self._fc(col, 0.95), width=2, style=tk.ARC)
        elif icon_type == "speaker_off":
            # Speaker shape with banned red line
            self.canvas.create_polygon(x-8, y-4, x-4, y-4, x, y-8, x, y+8, x-4, y+4, x-8, y+4,
                                       fill=self._fc(col, 0.6), outline=self._fc(col, 0.6), width=1)
            self.canvas.create_line(x-12, y-12, x+12, y+12, fill=self._fc(RED, 0.95), width=3)
        return (x, y, r)

    def _draw_bg(self, w, h, bp):
        cx, cy = w/2, h/2; t = time.time()
        for i in range(6):
            r = 220+i*75+math.sin(t*0.3+i)*5
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                outline=self._fc("#002244", 0.07*(6-i)/6*bp), width=1)
        if bp > 0.5:
            self.scan_y = (self.scan_y+2) % h
            for i in range(4):
                y = self.scan_y - i*5
                if y > 0: self.canvas.create_line(0, y, w, y,
                    fill=self._fc(CYAN, 0.06*(1-i/4)*(bp-0.5)*2))

    def _draw_brackets(self, w, h, bp):
        if bp < 0.72: return
        a = (bp-0.72)/0.28; c = self._fc(BLUE, 0.35*a); L, m = 40, 18
        for (x1,y1),(x2,y2) in [
            ((m,m),(m+L,m)),((m,m),(m,m+L)),((w-m,m),(w-m-L,m)),((w-m,m),(w-m,m+L)),
            ((m,h-m),(m+L,h-m)),((m,h-m),(m,h-m-L)),((w-m,h-m),(w-m-L,h-m)),((w-m,h-m),(w-m,h-m-L))]:
            self.canvas.create_line(x1,y1,x2,y2, fill=c, width=2)

    def _draw_center(self, cx, cy, bp, t):
        ca = max(0.0, min(1.0, (bp-0.04)/0.16))
        sa = max(0.0, min(1.0, (bp-0.18)/0.22))
        ga = max(0.0, min(1.0, (bp-0.38)/0.20))
        if ca <= 0: return
        OR = 138; rot = self.ring_angle
        self.canvas.create_oval(cx-OR, cy-OR, cx+OR, cy+OR,
            outline=self._fc(BLUE, 0.18*ca), width=1)
        for i in range(12):
            self.canvas.create_arc(cx-OR, cy-OR, cx+OR, cy+OR,
                start=i*30+rot, extent=20, outline=self._fc(BLUE, 0.65*ca), width=2, style=tk.ARC)
        for i in range(72):
            a = math.radians(i*5+rot)
            ln, al = (13,0.72) if i%6==0 else (6,0.38) if i%3==0 else (3,0.16)
            self.canvas.create_line(cx+math.cos(a)*(OR-ln), cy+math.sin(a)*(OR-ln),
                cx+math.cos(a)*OR, cy+math.sin(a)*OR, fill=self._fc(CYAN, al*ca), width=1)
        if sa <= 0: return
        for r,lw,ext,spd,col,al in [
            (OR+16,2,48,-0.9,BLUE,0.55),(OR+26,1,32,1.5,CYAN,0.42),(OR+36,1,22,-2.0,TEAL,0.32),
            (122,2,58,1.1,BLUE,0.48),(108,1,42,-0.7,CYAN,0.36),(94,1,35,1.8,TEAL,0.26)]:
            s = (t*52*spd)%360
            for off in ([0,180] if ext>45 else [0,120,240]):
                self.canvas.create_arc(cx-r,cy-r,cx+r,cy+r,
                    start=s+off,extent=ext,outline=self._fc(col,al*sa),width=lw,style=tk.ARC)
        DSR = 115
        for dot in self.data_dots:
            dot['ang'] += dot['spd']
            dx = cx+math.cos(dot['ang'])*DSR; dy = cy+math.sin(dot['ang'])*DSR
            sz = dot['sz']
            self.canvas.create_oval(dx-sz,dy-sz,dx+sz,dy+sz,fill=self._fc(CYAN,0.7*sa),outline="")
        IR2 = 90
        for i in range(8):
            self.canvas.create_arc(cx-IR2,cy-IR2,cx+IR2,cy+IR2,
                start=i*45-rot*1.4,extent=30,outline=self._fc(BLUE,0.50*sa),width=2,style=tk.ARC)
        if ga <= 0: return
        # Center core is kept completely empty behind the voice visualizer for ultimate premium look.
        # Removing all geometry, polygons, expanding circles, and glow.
        pass

    def _draw_pulse(self, cx, cy, bp):
        pp = max(0.0, min(1.0, (bp-0.58)/0.12))
        if pp <= 0: return
        for i in range(3):
            p=(pp+i*0.33)%1.0; r=p*490; a=(1-p)*0.35
            if a>0.01: self.canvas.create_oval(cx-r,cy-r,cx+r,cy+r,
                outline=self._fc(BLUE if i%2==0 else CYAN,a),width=2)

    def _draw_modules(self, cx, cy, bp, t):
        mp = max(0.0, min(1.0, (bp-0.68)/0.24))
        if mp <= 0: return
        orb_r = 138+162; mr = 48
        for m in self.mods:
            m['ang'] += m['spd']; m['ri'] += 0.8
            ox = cx+math.cos(m['ang'])*orb_r; oy = cy+math.sin(m['ang'])*orb_r
            col = m['col']
            # Glow layers
            for gl,ga in [(mr+12,0.04),(mr+5,0.10)]:
                self.canvas.create_oval(ox-gl,oy-gl,ox+gl,oy+gl,fill=self._fc(col,ga*mp),outline="")
            # Outer ring
            self.canvas.create_oval(ox-mr,oy-mr,ox+mr,oy+mr,
                fill=self._fc("#030810",0.9),outline=self._fc(col,0.55*mp),width=2)
            # Rotating segmented arc (mini version of center)
            for i in range(6):
                self.canvas.create_arc(ox-mr,oy-mr,ox+mr,oy+mr,
                    start=i*60+m['ri'],extent=16,outline=self._fc(col,0.6*mp),width=1,style=tk.ARC)
            # Inner ring
            self.canvas.create_oval(ox-28,oy-28,ox+28,oy+28,
                outline=self._fc(col,0.25*mp),width=1)
            # Counter-rotating arc
            s2 = (-m['ri']*0.7)%360
            self.canvas.create_arc(ox-28,oy-28,ox+28,oy+28,
                start=s2,extent=40,outline=self._fc(CYAN,0.55*mp),width=1,style=tk.ARC)
            # Dot
            self.canvas.create_oval(ox-4,oy-4,ox+4,oy+4,fill=self._fc(col,0.7*mp),outline="")
            # Labels
            self.canvas.create_text(ox,oy-7,text=m['icon'],
                fill=self._fc(col,0.90*mp),font=("Consolas",10,"bold"))
            self.canvas.create_text(ox,oy+9,text=m['name'],
                fill=self._fc(col,0.50*mp),font=("Consolas",7))

    def _draw_visualizer(self, cx, cy, bp, t):
        vp = max(0.0, min(1.0, (bp-0.90)/0.10))
        if vp <= 0: return
        is_wake = wakeword.is_active()
        adj = max(0, self.current_rms-400)
        target = min(adj/28.0, 90)*vp
        if self.is_thinking: target += math.sin(t*3)*10+10
        sm = self.rms_history[-1]*0.75+target*0.25
        self.rms_history.append(sm)
        if len(self.rms_history) > 80: self.rms_history.pop(0)
        IR = 72; col = CYAN if is_wake else BLUE
        if self.is_thinking: col = TEAL
        pts = []
        for i in range(90):
            f=i/89; dx=-IR+IR*2*f; x=cx+dx
            idx=max(0,min(79,len(self.rms_history)-1-int((1-f)*79)))
            val=self.rms_history[idx]; env=1.0-(abs(f-0.5)*2)**2
            yoff=math.sin(f*15+t*4.5)*0.85*(val*0.85)*env
            mh=max(0,IR**2-dx**2); my=math.sqrt(mh)-3
            pts.extend([x, cy+max(-my,min(my,yoff))])
        if is_wake:
            self.canvas.create_line(*pts,fill=self._fc(col,0.18),width=9,smooth=True,capstyle=tk.ROUND)
        self.canvas.create_line(*pts,fill=self._fc(col,0.88*vp),width=2,smooth=True,capstyle=tk.ROUND)

    def _draw_dust(self, cx, cy, bp):
        dp = max(0.0, min(1.0, (bp-0.62)/0.22))
        if dp <= 0: return
        for p in self.dust:
            p['a'] += p['spd']; x=cx+math.cos(p['a'])*p['r']; y=cy+math.sin(p['a'])*p['r']
            s=p['sz']; self.canvas.create_oval(x-s,y-s,x+s,y+s,fill=self._fc(CYAN,p['al']*dp),outline="")

    def _draw_hud(self, w, h, bp):
        hp = max(0.0, min(1.0, (bp-0.74)/0.18))
        if hp <= 0: return
        now = datetime.now(); yo = -22*(1-hp)
        self.canvas.create_text(40,36+yo,text=now.strftime("%H:%M"),
            fill=self._fc(BLUE,hp),font=("Consolas",30,"bold"),anchor="w")
        self.canvas.create_text(40,68+yo,
            text=f"{now.strftime('%A, %d %B')}   {self.weather_info}",
            fill=self._fc("#0088bb",hp),font=("Consolas",10),anchor="w")
        import tts_control
        states=[("SYS","ACTIVE" if self.is_active else "STANDBY",BLUE if self.is_active else "#223344"),
                ("MIC","MUTED" if self.mic_muted else "LIVE",RED if self.mic_muted else CYAN),
                ("TTS","MUTED" if not tts_control.is_tts_enabled() else "LIVE",RED if not tts_control.is_tts_enabled() else CYAN),
                ("AI","PROCESSING" if self.is_thinking else "READY","#ffaa00" if self.is_thinking else "#224455")]
        bx,by=40,h-52+16*(1-hp)
        for i,(lbl,val,vc) in enumerate(states):
            x=bx+i*105
            self.canvas.create_text(x,by,text=lbl,fill=self._fc("#445566",hp),font=("Consolas",8),anchor="w")
            self.canvas.create_text(x,by+13,text=val,fill=self._fc(vc,hp),font=("Consolas",9,"bold"),anchor="w")

    def _draw_logs(self, w, h, bp):
        lp = max(0.0, min(1.0, (bp-0.78)/0.18))
        if lp <= 0 or not self.log_lines: return
        px,py = w-380, h-155
        self.canvas.create_text(px,py,text="◈ SYS.LOG",
            fill=self._fc(CYAN,0.45*lp),font=("Consolas",8,"bold"),anchor="w")
        for i,line in enumerate(self.log_lines[-6:]):
            al=(i+1)/7*0.65*lp
            self.canvas.create_text(px,py+14+i*17,text=line[:48],
                fill=self._fc(BLUE,al),font=("Consolas",8),anchor="w")

    def _draw_echo(self, cx, cy, col):
        el = time.time()-self.display_text_time
        if el < 4.0 and self.display_text:
            a = 1.0 if el<=3.0 else 4.0-el
            self.canvas.create_text(cx,cy+168-el*4,text=self.display_text,
                fill=self._fc(col,a),font=("Consolas",12,"bold"))

    # ── MAIN LOOP ────────────────────────────────────────
    def _draw(self):
        self.canvas.delete("all")
        w,h = self.canvas.winfo_width(),self.canvas.winfo_height()
        if w<=1 or h<=1: self.after(30,self._draw); return
        cx,cy = w/2,h/2; t = time.time()
        bp = min(1.0,(t-self.activation_start)/self.boot_dur) if self.activation_start else 0.0
        self.ring_angle += 0.5

        # Canvas buttons (always drawn)
        self.pwr_pos = self._circ_btn(w-52, 45, 22, "pwr", RED if self.is_active else BLUE)
        if self.is_active and bp >= 0.88:
            mic_type = "mic_muted" if self.mic_muted else "mic_live"
            mic_col = RED if self.mic_muted else CYAN
            self.mic_pos = self._circ_btn(w-105, 45, 22, mic_type, mic_col)
            
            import tts_control
            tts_active = tts_control.is_tts_enabled()
            tts_type = "speaker_on" if tts_active else "speaker_off"
            tts_col = CYAN if tts_active else RED
            self.tts_pos = self._circ_btn(w-158, 45, 22, tts_type, tts_col)
        else:
            self.mic_pos = None
            self.tts_pos = None

        # Entry visibility
        show = self.is_active and bp >= 0.88
        if show and not self.entry_shown:
            self.entry.place(relx=0.5,rely=0.94,anchor="center",relwidth=0.48)
            self.entry_shown = True
        elif not show and self.entry_shown:
            self.entry.place_forget(); self.entry_shown = False

        # Standby
        if not self.is_active:
            pulse = math.sin(t*1.8)*7
            self.canvas.create_oval(cx-118-pulse,cy-118-pulse,cx+118+pulse,cy+118+pulse,
                outline=self._fc(BLUE,0.20),width=1)
            self.canvas.create_oval(cx-95,cy-95,cx+95,cy+95,outline=self._fc(CYAN,0.10),width=1)
            self.canvas.create_text(cx,cy-8,text="J.A.R.V.I.S.",
                fill=self._fc(BLUE,0.55),font=("Consolas",20,"bold"))
            self.canvas.create_text(cx,cy+14,text="SYSTEM STANDBY",
                fill=self._fc(CYAN,0.28),font=("Consolas",9))
            self.after(30,self._draw); return

        col = CYAN if wakeword.is_active() else BLUE
        if self.is_thinking: col = TEAL
        self._draw_bg(w,h,bp); self._draw_brackets(w,h,bp); self._draw_dust(cx,cy,bp)
        self._draw_center(cx,cy,bp,t); self._draw_pulse(cx,cy,bp)
        self._draw_modules(cx,cy,bp,t); self._draw_visualizer(cx,cy,bp,t)
        self._draw_hud(w,h,bp); self._draw_logs(w,h,bp); self._draw_echo(cx,cy,col)
        self.after(30,self._draw)

    # ── AUDIO LOOP ───────────────────────────────────────
    def _audio_loop(self):
        try:
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
            model=Model(get_model_path()); rec=KaldiRecognizer(model,16000)
            p=pyaudio.PyAudio()
            stream=p.open(format=pyaudio.paInt16,channels=1,rate=16000,
                input=True,frames_per_buffer=1280)
            stream.start_stream(); self.log("AUDIO ENGINE ONLINE")
        except Exception as e: self.log(f"AUDIO ERROR: {e}"); return
        import tts_control
        buf,was_active=[],False
        while self.audio_alive:
            if self.mic_muted or tts_control.is_currently_speaking():
                self.current_rms=0; time.sleep(0.1); continue
            try:
                data=stream.read(1280,exception_on_overflow=False)
                rms=audioop.rms(data,2); self.current_rms=0 if rms<300 else rms
                buf.append(data)
                if len(buf)>6: buf.pop(0)
                audio_np=np.frombuffer(data,dtype=np.int16)
                ww=wakeword.check_wakeword_audio(audio_np); active=wakeword.is_active()
                if ww:
                    self.trigger_display("WAKEWORD DETECTED")
                    if not self.is_active: self._activate()
                if active and not was_active:
                    for c in buf: rec.AcceptWaveform(c)
                    buf.clear()
                if active and rec.AcceptWaveform(data):
                    txt=json.loads(rec.Result()).get("text","").lower().strip()
                    if txt:
                        ok,clean=wakeword.process_text(txt)
                        if clean:
                            self.log(f"VOX: {clean}"); self.trigger_display(f"► {clean}")
                            threading.Thread(target=self._process,args=(clean,),daemon=True).start()
                was_active=active
            except Exception as e: self.log(f"ERR: {e}"); time.sleep(1)
        try: stream.stop_stream(); stream.close(); p.terminate()
        except: pass

    def on_closing(self): self.audio_alive=False; self.destroy()


import builtins
import re
_orig=builtins.print
def _uiprint(*a,**k):
    text = " ".join(str(x) for x in a)
    _orig(*a,**k)
    if "app" in globals() and app:
        try: app.trigger_display(text)
        except: pass
        
    # Hook Text-to-Speech speaking feedback:
    # Filter out system logs and user inputs (starting with '[', '►', 'VOX:', or 'ERR:')
    if not (text.startswith("[") or text.startswith("►") or text.startswith("VOX:") or text.startswith("ERR:")):
        try:
            import tts_control
            # Remove confirmation prompt suffixes like "— confirm? (yes/no)", "confirm? (yes/no)", "yes or no" from spoken audio
            speak_text = re.sub(r'—\s*confirm\?.*$', '', text, flags=re.IGNORECASE)
            speak_text = re.sub(r'confirm\?.*$', '', speak_text, flags=re.IGNORECASE)
            speak_text = re.sub(r'\(yes/no\)', '', speak_text, flags=re.IGNORECASE)
            speak_text = speak_text.strip()
            if speak_text:
                tts_control.speak(speak_text)
        except Exception as e:
            _orig(f"TTS execution error: {e}")
            
builtins.print=_uiprint

if __name__=="__main__":
    app=JarvisUI()
    app.protocol("WM_DELETE_WINDOW",app.on_closing)
    app.mainloop()
