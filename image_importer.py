"""
image_importer.py
-----------------
Fonction utilitaire pour Ursina (Python 3.13) qui ouvre une fenêtre tkinter
permettant de choisir une image et de la copier dans un dossier cible,
tout en conservant le nom de fichier original.

Usage depuis ton projet Ursina :
    from image_importer import open_image_importer
    open_image_importer()          # dossier cible par défaut : assets/textures/
    open_image_importer("maps/")   # ou n'importe quel dossier
"""

import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ── Dossiers cibles ────────────────────────────────────────────────────────────
# Modifie ces chemins selon la structure de ton projet Ursina
TARGET_DIRS = {
    "Textures  (assets/album/)": "assets/textures/",
#posibiliter d'ajouter un dossiers
}

# Extensions acceptées
ALLOWED_EXTENSIONS = [
    ("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tga *.webp *.tiff"),
    ("PNG",    "*.png"),
    ("JPEG",   "*.jpg *.jpeg"),
    ("Tous",   "*.*"),
]
# ──────────────────────────────────────────────────────────────────────────────


def _ensure_dir(path: str) -> None:
    """Crée le dossier s'il n'existe pas encore."""
    os.makedirs(path, exist_ok=True)


def _copy_image(src: str, dest_dir: str) -> str:
    """
    Copie l'image src dans dest_dir en gardant le nom original.
    Si un fichier du même nom existe déjà, ajoute _1, _2 … pour éviter
    l'écrasement silencieux.
    Retourne le chemin complet du fichier copié.
    """
    _ensure_dir(dest_dir)
    filename  = os.path.basename(src)
    name, ext = os.path.splitext(filename)
    dest      = os.path.join(dest_dir, filename)

    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(dest_dir, f"{name}_{counter}{ext}")
        counter += 1

    shutil.copy2(src, dest)
    return dest


def _build_popup(default_dir_key: str | None = None) -> None:
    """Construit et lance la fenêtre tkinter (appelé dans un thread séparé)."""

    root = tk.Tk()
    root.title("Importer une image")
    root.resizable(False, False)
    root.configure(bg="#1e1e2e")

    # ── Style ─────────────────────────────────────────────────────────────────
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TLabel",      background="#1e1e2e", foreground="#cdd6f4",
                    font=("Segoe UI", 10))
    style.configure("TCombobox",   fieldbackground="#313244",
                    background="#313244",    foreground="#cdd6f4",
                    selectbackground="#45475a")
    style.configure("TButton",     background="#89b4fa", foreground="#1e1e2e",
                    font=("Segoe UI", 10, "bold"), padding=6)
    style.map("TButton",           background=[("active", "#b4befe")])

    PAD = {"padx": 14, "pady": 6}

    # ── Titre ─────────────────────────────────────────────────────────────────
    tk.Label(root, text="🖼  Importer une image",
             bg="#1e1e2e", fg="#89b4fa",
             font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=3,
                                                  pady=(16, 4))

    # ── Sélection du fichier ──────────────────────────────────────────────────
    ttk.Label(root, text="Fichier image :").grid(row=1, column=0, sticky="w", **PAD)

    file_var = tk.StringVar(value="Aucun fichier sélectionné")
    file_label = tk.Label(root, textvariable=file_var, bg="#313244",
                          fg="#a6e3a1", font=("Segoe UI", 9),
                          width=38, anchor="w", padx=6, pady=4,
                          relief="flat", bd=0)
    file_label.grid(row=1, column=1, sticky="ew", **PAD)

    def browse():
        path = filedialog.askopenfilename(
            title="Choisir une image",
            filetypes=ALLOWED_EXTENSIONS,
        )
        if path:
            file_var.set(path)

    ttk.Button(root, text="Parcourir…", command=browse).grid(
        row=1, column=2, **PAD)

    # ── Choix du dossier cible ────────────────────────────────────────────────
    ttk.Label(root, text="Dossier cible :").grid(row=2, column=0, sticky="w", **PAD)

    dir_keys     = list(TARGET_DIRS.keys())
    default_key  = default_dir_key if default_dir_key in dir_keys else dir_keys[0]
    dir_var      = tk.StringVar(value=default_key)

    combo = ttk.Combobox(root, textvariable=dir_var, values=dir_keys,
                         state="readonly", width=36)
    combo.grid(row=2, column=1, columnspan=2, sticky="ew", **PAD)

    # ── Option : dossier personnalisé ─────────────────────────────────────────
    custom_var = tk.StringVar()

    ttk.Label(root, text="… ou chemin libre :").grid(row=3, column=0,
                                                      sticky="w", **PAD)
    custom_entry = tk.Entry(root, textvariable=custom_var, bg="#313244",
                            fg="#cdd6f4", insertbackground="#cdd6f4",
                            relief="flat", font=("Segoe UI", 9), width=28)
    custom_entry.grid(row=3, column=1, sticky="ew", **PAD)

    def browse_dir():
        d = filedialog.askdirectory(title="Choisir un dossier")
        if d:
            custom_var.set(d + "/")

    ttk.Button(root, text="Choisir…", command=browse_dir).grid(
        row=3, column=2, **PAD)

    # ── Résultat ──────────────────────────────────────────────────────────────
    result_var = tk.StringVar()
    tk.Label(root, textvariable=result_var, bg="#1e1e2e", fg="#f38ba8",
             font=("Segoe UI", 9), wraplength=380).grid(
        row=4, column=0, columnspan=3, pady=(0, 4))

    # ── Boutons Importer / Annuler ────────────────────────────────────────────
    def do_import():
        src = file_var.get()
        if not src or src == "Aucun fichier sélectionné":
            messagebox.showwarning("Aucun fichier",
                                   "Veuillez d'abord sélectionner une image.",
                                   parent=root)
            return

        # Priorité au chemin libre s'il est renseigné
        dest_dir = custom_var.get().strip() or TARGET_DIRS[dir_var.get()]

        try:
            copied = _copy_image(src, dest_dir)
            result_var.set("")
            messagebox.showinfo(
                "✅ Image importée",
                f"Fichier copié :\n{copied}",
                parent=root,
            )
            root.destroy()
        except Exception as exc:
            result_var.set(f"Erreur : {exc}")

    btn_frame = tk.Frame(root, bg="#1e1e2e")
    btn_frame.grid(row=5, column=0, columnspan=3, pady=(4, 16))

    ttk.Button(btn_frame, text="⬇  Importer", command=do_import).pack(
        side="left", padx=10)
    ttk.Button(btn_frame, text="Annuler",
               command=root.destroy).pack(side="left", padx=10)

    root.mainloop()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def open_image_importer(default_dir_key: str | None = None) -> None:
    """
    Ouvre la popup d'import dans un thread séparé afin de ne pas
    bloquer la boucle principale d'Ursina.

    Paramètre optionnel :
        default_dir_key  –  clé du dossier pré-sélectionné dans TARGET_DIRS
                            (ex: "Textures  (assets/textures/)")
    """
    t = threading.Thread(
        target=_build_popup,
        args=(default_dir_key,),
        daemon=True,
    )
    t.start()


# ── Test standalone (sans Ursina) ─────────────────────────────────────────────
if __name__ == "__main__":
    # Lance directement la popup pour tester sans Ursina
    _build_popup()
