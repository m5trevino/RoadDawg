#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import os
import threading
import datetime
import signal
import sys
import socket
from flask import Flask, request, jsonify
from flask_cors import CORS
import webbrowser
import logging
import pyperclip 

# CONFIG
BASE_DIR = os.path.expanduser("~/RoadDawg")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DB_PATH = os.path.join(STORAGE_DIR, "overwatch.db")
PORT = 5575

# CYBERPUNK PALETTE
C_BG = "#050505"
C_PANEL = "#0f0f0f"
C_CYAN = "#00f3ff"
C_PINK = "#ff0055"
C_GREEN = "#00ff41"
C_DIM = "#444444"
FONT_MONO = ("Courier New", 10)
FONT_BOLD = ("Courier New", 10, "bold")

def force_shutdown(signum=None, frame=None):
    print("\n\033[1;91m[🐶] SYSTEM HALTED.\033[0m")
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
    print(f"\033[1;96m[⚡] INCOMING: {data.get('filename')} (Seq: {data.get('sequence_index')})\033[0m")
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO projects (uuid, title, platform, last_updated) VALUES (?, ?, ?, ?)", (data['uuid'], data['title'], data['platform'], datetime.datetime.now()))
        c.execute("INSERT INTO artifacts (project_uuid, sequence_index, filename, content, type, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (data['uuid'], data['sequence_index'], data['filename'], data['content'], data['type'], datetime.datetime.now()))
        conn.commit(); conn.close()
        if gui_app: gui_app.event_generate("<<NewDrop>>")
        return jsonify({"status": "secured"}), 200
    except: return jsonify({"status": "error"}), 500

def start_server(): 
    try: app.run(port=PORT, debug=False, use_reloader=False)
    except: force_shutdown()

class CyberButton(tk.Label):
    def __init__(self, parent, text, fg, bg, cmd):
        super().__init__(parent, text=f" {text} ", fg=fg, bg=bg, font=FONT_BOLD, cursor="hand2")
        self.cmd = cmd; self.default_bg = bg
        self.bind("<Button-1>", lambda e: self.cmd())
        self.bind("<Enter>", lambda e: self.config(bg=C_DIM))
        self.bind("<Leave>", lambda e: self.config(bg=self.default_bg))

class RoadDawgApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ROAD DAWG v3.1 | CONTROL CENTER")
        self.geometry("1400x800")
        self.configure(bg=C_BG)
        self.bind("<<NewDrop>>", self.refresh_data)
        self.protocol("WM_DELETE_WINDOW", force_shutdown)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background=C_BG, foreground=C_GREEN, fieldbackground=C_BG, borderwidth=0, font=FONT_MONO, rowheight=25)
        style.configure("Treeview.Heading", background=C_PANEL, foreground=C_CYAN, font=FONT_BOLD, borderwidth=1, relief="flat")
        style.map("Treeview", background=[('selected', C_PINK)], foreground=[('selected', 'white')])
        
        # DARK SCROLLBAR STYLE
        style.configure("Vertical.TScrollbar", background=C_PANEL, troughcolor=C_BG, borderwidth=0, arrowcolor=C_CYAN)

        header = tk.Frame(self, bg=C_BG, height=50)
        header.pack(fill=tk.X, pady=5)
        tk.Label(header, text=" :: ROAD DAWG :: ", bg=C_BG, fg=C_CYAN, font=("Courier New", 20, "bold")).pack(side=tk.LEFT, padx=10)
        self.status_var = tk.StringVar(value="[ ONLINE ]")
        tk.Label(header, textvariable=self.status_var, bg=C_BG, fg=C_GREEN, font=FONT_MONO).pack(side=tk.RIGHT, padx=20)

        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=C_BG, sashwidth=4, sashrelief=tk.FLAT, showhandle=False)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- PANE 1: PROJECTS ---
        self.f_proj = tk.Frame(self.paned, bg=C_PANEL, bd=1, relief="solid")
        self.l_proj = self.create_tree(self.f_proj, ["Title"])
        self.l_proj.heading("Title", text="// OPERATIONS")
        self.l_proj.bind("<<TreeviewSelect>>", self.load_timeline)
        self.paned.add(self.f_proj, width=300)
        
        # --- PANE 2: TIMELINE ---
        self.f_time = tk.Frame(self.paned, bg=C_PANEL, bd=1, relief="solid")
        self.l_time = self.create_tree(self.f_time, ["Seq", "File", "Time"])
        self.l_time.heading("Seq", text="#"); self.l_time.column("Seq", width=50, anchor="center")
        self.l_time.heading("File", text="// ASSET"); self.l_time.heading("Time", text="// TIMESTAMP")
        self.l_time.tag_configure('checkpoint', foreground=C_PINK)
        self.l_time.bind("<Button-3>", self.context_menu)
        self.l_time.bind("<<TreeviewSelect>>", self.inspect)
        self.paned.add(self.f_time, width=500)
        
        # --- PANE 3: INSPECTOR ---
        self.f_insp = tk.Frame(self.paned, bg=C_BG, bd=0)
        tools = tk.Frame(self.f_insp, bg=C_BG); tools.pack(fill=tk.X, pady=(0, 5))
        CyberButton(tools, "RECONSTRUCT", "white", C_PINK, self.reconstruct).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        CyberButton(tools, "COPY BUNDLE", "black", C_GREEN, self.batch_copy).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        self.f_prev_cont = tk.Frame(self.f_insp, bg=C_PANEL, bd=1, relief="solid")
        self.f_prev_cont.pack(fill=tk.BOTH, expand=True)
        self.l_prev = self.create_tree(self.f_prev_cont, ["File", "Ver"])
        self.l_prev.heading("File", text="// TARGET FILE"); self.l_prev.heading("Ver", text="// VERSION")
        self.paned.add(self.f_insp, width=400)
        
        self.load_projects()

    def create_tree(self, parent, cols):
        # Container to hold tree + scrollbar
        container = tk.Frame(parent, bg=C_PANEL)
        container.pack(fill=tk.BOTH, expand=True)
        
        tree = ttk.Treeview(container, columns=cols, show="headings", selectmode="extended")
        sb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def load_projects(self):
        for i in self.l_proj.get_children(): self.l_proj.delete(i)
        try:
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT uuid, title FROM projects ORDER BY last_updated DESC")
            for r in c.fetchall(): self.l_proj.insert("", "end", iid=r[0], values=(r[1],))
            conn.close()
        except: pass

    def refresh_data(self, event): 
        self.status_var.set("[ DATA INCOMING... ]")
        self.after(1000, lambda: self.status_var.set("[ ONLINE ]"))
        self.load_projects()

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
            if a[1] in cps: name = f"🚩 {cps[a[1]]} | {name}"; tags=('checkpoint',)
            self.l_time.insert("", "0", iid=a[0], values=(a[1], name, a[3]), tags=tags)
        # Auto-scroll to bottom to show latest
        if self.l_time.get_children(): self.l_time.yview_moveto(1)

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
            m = tk.Menu(self, tearoff=0, bg=C_PANEL, fg=C_CYAN, font=FONT_MONO)
            m.add_command(label="[+] SET CHECKPOINT", command=self.add_cp)
            m.post(event.x_root, event.y_root)

    def add_cp(self):
        sel_p = self.l_proj.selection(); sel_t = self.l_time.selection()
        if not sel_p or not sel_t: return
        seq = int(self.l_time.item(sel_t[0])['values'][0])
        lbl = simpledialog.askstring("CHECKPOINT", "LABEL:")
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
        messagebox.showinfo("ROAD DAWG", f"RECONSTRUCTED:\n{path}")
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
        messagebox.showinfo("BATCH COPY", f"COPIED {len(files)} FILES.")

if __name__ == "__main__":
    t = threading.Thread(target=start_server, daemon=True); t.start()
    gui_app = RoadDawgApp()
    try: gui_app.mainloop()
    except KeyboardInterrupt: force_shutdown()
