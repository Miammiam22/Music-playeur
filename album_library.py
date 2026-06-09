"""
album_library.py
----------------
Gestionnaire de données des albums.
Gère le stockage JSON, l'import d'images et de MP3.

Structure JSON : data/albums.json
Pochettes      : assets/covers/
Musiques       : assets/music/<album_id>/
"""

import json
import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

# ── Chemins ───────────────────────────────────────────────────────────────────
DATA_DIR   = "data"
DATA_FILE  = os.path.join(DATA_DIR, "albums.json")
COVERS_DIR = "assets/covers"
MUSIC_DIR  = "assets/music"

# ── Formats ───────────────────────────────────────────────────────────────────
IMAGE_TYPES = [("Images", "*.png *.jpg *.jpeg *.bmp *.tga *.webp"), ("Tous", "*.*")]
MUSIC_TYPES = [("Audio", "*.mp3 *.wav *.ogg *.flac *.aac"), ("MP3", "*.mp3"), ("Tous", "*.*")]

# ── Palette partagée pour les deux popups ─────────────────────────────────────
BG, FG, ACCENT, FIELD, ERR = "#0f0f17", "#e2e0f0", "#c084fc", "#1e1b2e", "#f87171"


# ─────────────────────────────────────────────────────────────────────────────
#  Utilitaires
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_dirs():
    for d in (DATA_DIR, COVERS_DIR, MUSIC_DIR):
        os.makedirs(d, exist_ok=True)


def _safe_copy(src: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    name, ext = os.path.splitext(os.path.basename(src))
    dest = os.path.join(dest_dir, f"{name}{ext}")
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(dest_dir, f"{name}_{counter}{ext}")
        counter += 1
    shutil.copy2(src, dest)
    return dest


def _make_style(root):
    """Applique le style sombre commun à une fenêtre tkinter."""
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TLabel",  background=BG, foreground=FG,
                    font=("Segoe UI", 10))
    style.configure("TButton", background=ACCENT, foreground="#0f0f17",
                    font=("Segoe UI", 10, "bold"), padding=6, relief="flat")
    style.map("TButton", background=[("active", "#a855f7")])
    style.configure("Ghost.TButton", background=BG, foreground=ACCENT,
                    font=("Segoe UI", 9), padding=4, relief="flat", borderwidth=1)
    style.map("Ghost.TButton", background=[("active", FIELD)])
    style.configure("Track.TButton", background="#1e1b2e", foreground="#86efac",
                    font=("Segoe UI", 9), padding=3, relief="flat")
    style.map("Track.TButton", background=[("active", "#2a2640")])
    return style


# ─────────────────────────────────────────────────────────────────────────────
#  JSON
# ─────────────────────────────────────────────────────────────────────────────

def load_albums() -> list[dict]:
    _ensure_dirs()
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_albums(albums: list[dict]):
    _ensure_dirs()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)


def add_album(album: dict) -> list[dict]:
    albums = load_albums()
    albums.append(album)
    save_albums(albums)
    return albums


def remove_album(album_id: str) -> list[dict]:
    albums = [a for a in load_albums() if a.get("id") != album_id]
    save_albums(albums)
    return albums


def add_tracks_to_album(album_id: str, track_paths: list[str]) -> Optional[dict]:
    """
    Copie plusieurs fichiers audio dans assets/music/<album_id>/
    et les enregistre dans 'tracks' sous la forme :
        {"name": "titre.mp3", "path": "assets/music/<id>/titre.mp3"}
    Le chemin est stocké en absolu pour pouvoir être lu directement.
    Retourne l'album mis à jour, ou None si introuvable.
    """
    albums = load_albums()
    for album in albums:
        if album.get("id") == album_id:
            dest_dir = os.path.join(MUSIC_DIR, album_id)
            # Noms déjà présents pour éviter les doublons exacts
            existing_names = {
                t["name"] if isinstance(t, dict) else t
                for t in album.get("tracks", [])
            }
            for path in track_paths:
                if not os.path.isfile(path):
                    continue
                copied      = _safe_copy(path, dest_dir)
                track_name  = os.path.basename(copied)
                track_entry = {
                    "name": track_name,
                    "path": os.path.abspath(copied),   # chemin absolu lisible
                }
                if track_name not in existing_names:
                    album.setdefault("tracks", []).append(track_entry)
                    existing_names.add(track_name)
            save_albums(albums)
            return album
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Popup 1 – Ajouter un album
# ─────────────────────────────────────────────────────────────────────────────

def _build_add_album_popup(on_success=None):
    root = tk.Tk()
    root.title("Ajouter un album")
    root.resizable(False, False)
    root.configure(bg=BG)
    _make_style(root)

    P = {"padx": 16, "pady": 5}

    tk.Label(root, text="＋  Nouvel album",
             bg=BG, fg=ACCENT, font=("Segoe UI", 14, "bold")
             ).grid(row=0, column=0, columnspan=3, pady=(18, 8))

    def lbl(text, row):
        ttk.Label(root, text=text).grid(row=row, column=0, sticky="w", **P)

    def entry(row):
        e = tk.Entry(root, bg=FIELD, fg=FG, insertbackground=FG,
                     relief="flat", font=("Segoe UI", 10), width=30, bd=4)
        e.grid(row=row, column=1, columnspan=2, sticky="ew", **P)
        return e

    lbl("Nom de l'album :", 1); e_name   = entry(1)
    lbl("Artiste :",        2); e_artist = entry(2)
    lbl("Année :",          3); e_year   = entry(3)

    lbl("Pochette :", 4)
    cover_var = tk.StringVar()
    tk.Label(root, textvariable=cover_var, bg=FIELD, fg="#86efac",
             font=("Segoe UI", 8), width=28, anchor="w",
             padx=6, pady=3).grid(row=4, column=1, sticky="ew", **P)

    def browse_cover():
        p = filedialog.askopenfilename(title="Choisir la pochette", filetypes=IMAGE_TYPES)
        if p:
            cover_var.set(p)

    ttk.Button(root, text="Parcourir…", style="Ghost.TButton",
               command=browse_cover).grid(row=4, column=2, **P)

    status_var = tk.StringVar()
    tk.Label(root, textvariable=status_var, bg=BG, fg=ERR,
             font=("Segoe UI", 9), wraplength=340
             ).grid(row=5, column=0, columnspan=3, pady=(0, 2))

    def do_add():
        name   = e_name.get().strip()
        artist = e_artist.get().strip()
        year   = e_year.get().strip()
        cover  = cover_var.get().strip()

        if not name:
            status_var.set("⚠  Le nom de l'album est obligatoire.")
            return
        if not cover or not os.path.isfile(cover):
            status_var.set("⚠  Sélectionnez une pochette valide.")
            return
        try:
            copied_cover = _safe_copy(cover, COVERS_DIR)
        except Exception as exc:
            status_var.set(f"Erreur : {exc}")
            return

        import uuid
        album = {
            "id":     str(uuid.uuid4())[:8],
            "name":   name,
            "artist": artist,
            "year":   year,
            "cover":  copied_cover,
            "tracks": [],
        }
        add_album(album)
        if on_success:
            on_success(album)
        messagebox.showinfo("Album ajouté", f"« {name} » ajouté !", parent=root)
        root.destroy()

    btn_row = tk.Frame(root, bg=BG)
    btn_row.grid(row=6, column=0, columnspan=3, pady=(6, 18))
    ttk.Button(btn_row, text="Ajouter",  command=do_add).pack(side="left", padx=10)
    ttk.Button(btn_row, text="Annuler",  command=root.destroy,
               style="Ghost.TButton").pack(side="left", padx=6)

    root.mainloop()


def open_add_album_popup(on_success=None):
    threading.Thread(target=_build_add_album_popup, args=(on_success,), daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
#  Popup 2 – Ajouter des musiques à un album existant
# ─────────────────────────────────────────────────────────────────────────────

def _build_add_tracks_popup(album: dict, on_success=None):
    """
    Fenêtre tkinter pour ajouter des MP3 à un album déjà créé.
    - Sélection multiple de fichiers audio
    - Liste visuelle des fichiers sélectionnés (avec bouton ✕ pour retirer)
    - Affiche les pistes déjà présentes dans l'album
    - on_success(album_mis_à_jour) appelé après import
    """
    root = tk.Tk()
    root.title(f"Ajouter des musiques — {album.get('name','?')}")
    root.resizable(False, False)
    root.configure(bg=BG)
    _make_style(root)

    P = {"padx": 16, "pady": 4}

    # ── Titre ──────────────────────────────────────────────────────────────
    tk.Label(root, text=f"♪  {album.get('name','?')}",
             bg=BG, fg=ACCENT, font=("Segoe UI", 13, "bold")
             ).grid(row=0, column=0, columnspan=2, pady=(16, 2), padx=16)
    tk.Label(root, text=f"{album.get('artist','?')}  ·  {album.get('year','')}",
             bg=BG, fg="#888", font=("Segoe UI", 9)
             ).grid(row=1, column=0, columnspan=2, pady=(0, 10), padx=16)

    # ── Pistes déjà présentes ──────────────────────────────────────────────
    existing = album.get("tracks", [])
    if existing:
        tk.Label(root, text="Pistes déjà dans l'album :",
                 bg=BG, fg="#aaa", font=("Segoe UI", 9, "italic")
                 ).grid(row=2, column=0, columnspan=2, sticky="w", padx=16)

        exist_frame = tk.Frame(root, bg=FIELD, bd=0)
        exist_frame.grid(row=3, column=0, columnspan=2, sticky="ew",
                         padx=16, pady=(2, 10))
        for t in existing:
            t_name = t["name"] if isinstance(t, dict) else t
            tk.Label(exist_frame, text=f"  u2713  {t_name}", bg=FIELD, fg="#86efac",
                     font=("Segoe UI", 8), anchor="w"
                     ).pack(fill="x", pady=1)

    # ── Sélection de nouveaux fichiers ─────────────────────────────────────
    tk.Label(root, text="Nouveaux fichiers à ajouter :",
             bg=BG, fg=FG, font=("Segoe UI", 10)
             ).grid(row=4, column=0, sticky="w", **P)

    ttk.Button(root, text="＋ Sélectionner des fichiers…",
               command=lambda: _browse_tracks()
               ).grid(row=4, column=1, sticky="e", **P)

    # ── Liste des fichiers sélectionnés ────────────────────────────────────
    list_frame = tk.Frame(root, bg=FIELD, bd=0)
    list_frame.grid(row=5, column=0, columnspan=2, sticky="nsew",
                    padx=16, pady=(0, 6))
    root.grid_rowconfigure(5, weight=1)

    # Canvas + scrollbar pour la liste
    canvas   = tk.Canvas(list_frame, bg=FIELD, bd=0, highlightthickness=0,
                         height=140, width=380)
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
    inner    = tk.Frame(canvas, bg=FIELD)

    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Compteur
    count_var = tk.StringVar(value="0 fichier sélectionné")
    tk.Label(root, textvariable=count_var, bg=BG, fg="#888",
             font=("Segoe UI", 8)
             ).grid(row=6, column=0, columnspan=2, pady=(0, 4))

    # ── État interne : liste des chemins choisis ───────────────────────────
    selected_paths: list[str] = []

    def _refresh_list():
        for widget in inner.winfo_children():
            widget.destroy()
        for i, path in enumerate(selected_paths):
            row_f = tk.Frame(inner, bg=FIELD)
            row_f.pack(fill="x", pady=1)

            tk.Label(row_f, text=f"  {os.path.basename(path)}",
                     bg=FIELD, fg="#e2e0f0", font=("Segoe UI", 9),
                     anchor="w", width=38
                     ).pack(side="left")

            def _remove(idx=i):
                selected_paths.pop(idx)
                _refresh_list()
                count_var.set(f"{len(selected_paths)} fichier(s) sélectionné(s)")

            ttk.Button(row_f, text="✕", style="Ghost.TButton",
                       command=_remove, width=3
                       ).pack(side="right", padx=4)

        count_var.set(f"{len(selected_paths)} fichier(s) sélectionné(s)")

    def _browse_tracks():
        paths = filedialog.askopenfilenames(
            title="Sélectionner les fichiers audio",
            filetypes=MUSIC_TYPES,
        )
        for p in paths:
            if p not in selected_paths:
                selected_paths.append(p)
        _refresh_list()

    # ── Statut ──────────────────────────────────────────────────────────────
    status_var = tk.StringVar()
    tk.Label(root, textvariable=status_var, bg=BG, fg=ERR,
             font=("Segoe UI", 9), wraplength=380
             ).grid(row=7, column=0, columnspan=2, pady=(0, 2))

    # ── Boutons ─────────────────────────────────────────────────────────────
    def do_import():
        if not selected_paths:
            status_var.set("⚠  Sélectionnez au moins un fichier audio.")
            return
        try:
            updated = add_tracks_to_album(album["id"], selected_paths)
        except Exception as exc:
            status_var.set(f"Erreur : {exc}")
            return

        if updated is None:
            status_var.set("⚠  Album introuvable dans la base.")
            return

        n = len(selected_paths)
        if on_success:
            on_success(updated)
        messagebox.showinfo(
            "Musiques ajoutées",
            f"{n} fichier(s) ajouté(s) à « {album.get('name','?')} » !",
            parent=root,
        )
        root.destroy()

    btn_row = tk.Frame(root, bg=BG)
    btn_row.grid(row=8, column=0, columnspan=2, pady=(4, 18))
    ttk.Button(btn_row, text="⬇  Importer", command=do_import).pack(side="left", padx=10)
    ttk.Button(btn_row, text="Annuler", command=root.destroy,
               style="Ghost.TButton").pack(side="left", padx=6)

    root.mainloop()


def open_add_tracks_popup(album: dict, on_success=None):
    """
    Lance la popup d'ajout de musiques dans un thread séparé.
    album       : dict de l'album cible (doit avoir un 'id')
    on_success  : fonction appelée avec l'album mis à jour après import
    """
    threading.Thread(
        target=_build_add_tracks_popup,
        args=(album, on_success),
        daemon=True,
    ).start()
