#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import os
import threading
import datetime
import signal
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import webbrowser
import logging
import pyperclip 

# CONFIG
BASE_DIR = os.path.expanduser("~/road_dawg")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DB_PATH = os.path.join(STORAGE_DIR, "overwatch.db")
PORT = 5575

# THEME: STREET LEVEL
BG_ROOT = "#0a0a0a"
BG_PANEL = "#141414"
FG_TEXT = "#e0e0e0" 
FG_ACCENT = "#ff3b30" # Red
FG_GREEN = "#30d158"  # Green
FONT_BOLD = ("Consolas", 10, "bold")

def force_shutdown(signum=None, frame=None):
    print("\n[🐶] ROAD DAWG SIGNING OFF.")
    os._exit(0)

signal.signal(signal.SIGINT, force_shutdown)

def init_db():
    if not os.path.exists(STORAGE_DIR): os.makedirs(STORAGE_DIR)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS projects (uuid TEXT PRIMARY KEY, title TEXT, platform TEXT, last_updated DATETIME)')
    c.execute('CREATE TABLE IF NOT EXISTS artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT, project_uuid TEXT, sequence_index INTEGER, filename TEXT, content TEXT, type TEXT, timestamp DATETIME)')
    c.execute('CREATE TABLE IF NOT EXISTS checkpoints (id INTEGER PRIMARY KEY AUTOINCREMENT, project_uuid TEXT, sequence_index INTEGER, label TEXT, timestamp DATETIME)')
    conn.commit(); conn.close()

init_db()

app = Flask(__name__)
CORS(app)
log = logging.getLogger('werkzeug'); log.setLevel(logging.ERROR)

@app.route('/api/drop', methods=['POST'])
def receive_drop():
    data = request.json
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO projects (uuid, title, platform, last_updated) VALUES (?, ?, ?, ?)", (data['uuid'], data['title'], data['platform'], datetime.datetime.now()))
        c.execute("INSERT INTO artifacts (project_uuid, sequence_index, filename, content, type, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (data['uuid'], data['sequence_index'], data['filename'], data['content'], data['type'], datetime.datetime.now()))
        conn.commit(); conn.close()
        if gui_app: gui_app.event_generate("<<NewDrop>>")
        return jsonify({"status": "secured"}), 200
    except: return jsonify({"status": "error"}), 500

def start_server(): app.run(port=PORT, debug=False, use_reloader=False)

class RoadDawgApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ROAD DAWG | CONTROL CENTER")
        self.geometry("1400x800")
        self.configure(bg=BG_ROOT)
        self.bind("<<NewDrop>>", self.refresh_data)
        self.protocol("WM_DELETE_WINDOW", force_shutdown)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background=BG_PANEL, foreground=FG_TEXT, fieldbackground=BG_PANEL, borderwidth=0)
        style.configure("Treeview.Heading", background="#000", foreground=FG_ACCENT, font=FONT_BOLD)
        style.map("Treeview", background=[('selected', '#333')], foreground=[('selected', '#fff')])
        
        header = tk.Frame(self, bg="black", height=45)
        header.pack(fill=tk.X)
        tk.Label(header, text=" :: ROAD DAWG v2.0 :: ", bg="black", fg=FG_GREEN, font=("Consolas", 16, "bold")).pack(side=tk.LEFT, padx=15)

        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=BG_ROOT, sashwidth=4, sashrelief=tk.FLAT)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 1. PROJECTS
        self.f_proj = tk.Frame(self.paned, bg=BG_PANEL)
        self.l_proj = ttk.Treeview(self.f_proj, columns=("Title",), show="headings")
        self.l_proj.heading("Title", text="OPERATIONS"); self.l_proj.pack(fill=tk.BOTH, expand=True)
        self.l_proj.bind("<<TreeviewSelect>>", self.load_timeline)
        self.paned.add(self.f_proj, width=300)
        
        # 2. TIMELINE
        self.f_time = tk.Frame(self.paned, bg=BG_PANEL)
        self.l_time = ttk.Treeview(self.f_time, columns=("Seq", "File", "Time"), show="headings")
        self.l_time.heading("Seq", text="#"); self.l_time.column("Seq", width=50)
        self.l_time.heading("File", text="ASSET"); self.l_time.heading("Time", text="TIMESTAMP")
        self.l_time.tag_configure('checkpoint', foreground=FG_GREEN)
        self.l_time.bind("<Button-3>", self.context_menu)
        self.l_time.bind("<<TreeviewSelect>>", self.inspect)
        self.l_time.pack(fill=tk.BOTH, expand=True)
        self.paned.add(self.f_time, width=500)
        
        # 3. INSPECTOR
        self.f_insp = tk.Frame(self.paned, bg=BG_ROOT)
        tools = tk.Frame(self.f_insp, bg="black")
        tools.pack(fill=tk.X)
        tk.Button(tools, text="⚡ RECONSTRUCT", bg=FG_ACCENT, fg="white", font=FONT_BOLD, command=self.reconstruct).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(tools, text="📋 COPY BUNDLE", bg=FG_GREEN, fg="black", font=FONT_BOLD, command=self.batch_copy).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.l_prev = ttk.Treeview(self.f_insp, columns=("File", "Ver"), show="headings")
        self.l_prev.heading("File", text="FILE"); self.l_prev.heading("Ver", text="VERSION")
        self.l_prev.pack(fill=tk.BOTH, expand=True)
        self.paned.add(self.f_insp, width=400)
        
        self.load_projects()

    def load_projects(self):
        for i in self.l_proj.get_children(): self.l_proj.delete(i)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT uuid, title FROM projects ORDER BY last_updated DESC")
        for r in c.fetchall(): self.l_proj.insert("", "end", iid=r[0], values=(r[1],))
        conn.close()

    def refresh_data(self, event): self.load_projects()

    def load_timeline(self, event):
        sel = self.l_proj.selection()
        if not sel: return
        for i in self.l_time.get_children(): self.l_time.delete(i)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT id, sequence_index, filename, timestamp, type FROM artifacts WHERE project_uuid=? ORDER BY sequence_index ASC", (sel[0],))
        arts = c.fetchall()
        c.execute("SELECT sequence_index, label FROM checkpoints WHERE project_uuid=?", (sel[0],))
        cps = {r[0]: r[1] for r in c.fetchall()}
        conn.close()
        for a in arts:
            name = a[2]; tags = ()
            if a[1] in cps: name = f"✅ {cps[a[1]]} | {name}"; tags=('checkpoint',)
            self.l_time.insert("", "0", iid=a[0], values=(a[1], name, a[3]), tags=tags)

    def inspect(self, event):
        sel_p = self.l_proj.selection(); sel_t = self.l_time.selection()
        if not sel_p or not sel_t: return
        seq = int(self.l_time.item(sel_t[0])['values'][0])
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT filename, MAX(sequence_index) FROM artifacts WHERE project_uuid=? AND sequence_index<=? GROUP BY filename", (sel_p[0], seq))
        files = c.fetchall(); conn.close()
        for i in self.l_prev.get_children(): self.l_prev.delete(i)
        for f in files: self.l_prev.insert("", "end", values=(f[0], f"#{f[1]}"))

    def context_menu(self, event):
        item = self.l_time.identify_row(event.y)
        if item:
            self.l_time.selection_set(item)
            m = tk.Menu(self, tearoff=0); m.add_command(label="Mark Checkpoint", command=self.add_cp); m.post(event.x_root, event.y_root)

    def add_cp(self):
        sel_p = self.l_proj.selection(); sel_t = self.l_time.selection()
        if not sel_p or not sel_t: return
        seq = int(self.l_time.item(sel_t[0])['values'][0])
        lbl = simpledialog.askstring("Checkpoint", "Label:")
        if lbl:
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("INSERT INTO checkpoints (project_uuid, sequence_index, label, timestamp) VALUES (?, ?, ?, ?)", (sel_p[0], seq, lbl, datetime.datetime.now()))
            conn.commit(); conn.close(); self.load_timeline(None)

    def reconstruct(self):
        sel_p = self.l_proj.selection(); sel_t = self.l_time.selection()
        if not sel_p or not sel_t: return
        seq = int(self.l_time.item(sel_t[0])['values'][0])
        title = self.l_proj.item(sel_p[0])['values'][0].replace(" ", "_")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(STORAGE_DIR, f"{title}_REV_{seq}_{ts}")
        os.makedirs(path, exist_ok=True)
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT filename, MAX(sequence_index) FROM artifacts WHERE project_uuid=? AND sequence_index<=? GROUP BY filename", (sel_p[0], seq))
        for win in c.fetchall():
            c.execute("SELECT content FROM artifacts WHERE project_uuid=? AND filename=? AND sequence_index=?", (sel_p[0], win[0], win[1]))
            with open(os.path.join(path, win[0]), 'w') as f: f.write(c.fetchone()[0])
        conn.close()
        messagebox.showinfo("ROAD DAWG", f"Files Reconstructed:\n{path}")
        webbrowser.open(path)
    
    def batch_copy(self):
        sel_p = self.l_proj.selection(); sel_t = self.l_time.selection()
        if not sel_p or not sel_t: return
        seq = int(self.l_time.item(sel_t[0])['values'][0])
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT filename, MAX(sequence_index) FROM artifacts WHERE project_uuid=? AND sequence_index<=? GROUP BY filename", (sel_p[0], seq))
        files = c.fetchall()
        installer = "#!/bin/bash\n# ROAD DAWG BATCH INSTALLER\n\n"
        for win in files:
            fname = win[0]; ver = win[1]
            c.execute("SELECT content FROM artifacts WHERE project_uuid=? AND filename=? AND sequence_index=?", (sel_p[0], fname, ver))
            content = c.fetchone()[0]
            installer += f"echo '[+] Installing {fname} (v{ver})...'\n"
            installer += f"cat << 'EOF' > {fname}\n{content}\nEOF\n\n"
            if fname.endswith(".sh") or fname.endswith(".py"): installer += f"chmod +x {fname}\n"
        conn.close()
        pyperclip.copy(installer)
        messagebox.showinfo("BATCH COPY", f"Copied {len(files)} files as a single installer script.")

if __name__ == "__main__":
    t = threading.Thread(target=start_server, daemon=True); t.start()
    gui_app = RoadDawgApp()
    try: gui_app.mainloop()
    except KeyboardInterrupt: force_shutdown()
