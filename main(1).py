"""
main.py
-------
Application Ursina – Bibliothèque d'albums musicaux.

Lancement : python main.py

Contrôles :
  A          → ouvrir la popup « Ajouter un album »
  Échap      → quitter
  Clic sur pochette → sélectionner / afficher les infos de l'album
"""

from ursina import *
from ursina.prefabs.button import Button
import os

from album_library import load_albums, open_add_album_popup

# ─────────────────────────────────────────────────────────────────────────────
#  Configuration de la grille
# ─────────────────────────────────────────────────────────────────────────────
COLS        = 4      # colonnes par ligne
CARD_W      = .22    # largeur d'une carte  (unités Ursina UI)
CARD_H      = .22    # hauteur d'une carte
GAP_X       = .26    # espacement horizontal centre-à-centre
GAP_Y       = .30    # espacement vertical   centre-à-centre
GRID_LEFT   = -.39   # bord gauche de la grille
GRID_TOP    = .32    # bord haut   de la grille


# ─────────────────────────────────────────────────────────────────────────────
#  Application
# ─────────────────────────────────────────────────────────────────────────────
app = Ursina(title="Album Library", borderless=False)

# Fond sombre — méthode correcte dans Ursina
window.color = color.rgb(10, 10, 20)

# ─────────────────────────────────────────────────────────────────────────────
#  État global
# ─────────────────────────────────────────────────────────────────────────────
album_cards: list[Button] = []
selected_album = None
_empty_hint    = None       # Text affiché quand il n'y a aucun album

# ── En-tête ───────────────────────────────────────────────────────────────────
title_text = Text(
    "♫  Album Library",
    parent   = camera.ui,
    origin   = (-.5, .5),
    position = (-.88, .47),
    scale    = 1.5,
    color    = color.rgb(192, 132, 252),
)

hint_text = Text(
    "[A] Ajouter un album",
    parent   = camera.ui,
    origin   = (.5, .5),
    position = (.88, .47),
    scale    = .9,
    color    = color.rgb(120, 120, 160),
)

# ── Panneau d'info (bas) ──────────────────────────────────────────────────────
info_bg = Entity(
    parent    = camera.ui,
    model     = "quad",
    color     = color.rgba(20, 18, 35, 200),
    scale     = (1.8, .12),
    position  = (0, -.44, 1),
)

info_panel = Text(
    "",
    parent   = camera.ui,
    origin   = (0, 0),
    position = (0, -.44),
    scale    = .75,
    color    = color.rgb(226, 224, 240),
)


# ─────────────────────────────────────────────────────────────────────────────
#  Chargement de texture
# ─────────────────────────────────────────────────────────────────────────────

def _load_tex(path: str):
    if path and os.path.isfile(path):
        try:
            return load_texture(path)
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Création d'une carte album
# ─────────────────────────────────────────────────────────────────────────────

def _make_card(album: dict, index: int) -> Button:
    col = index % COLS
    row = index // COLS
    x   = GRID_LEFT + col * GAP_X
    y   = GRID_TOP  - row * GAP_Y

    tex = _load_tex(album.get("cover", ""))

    card = Button(
        parent          = camera.ui,
        text            = "",
        texture         = tex,
        color           = color.white if tex else color.rgb(40, 36, 60),
        highlight_color = color.rgb(192, 132, 252),
        pressed_color   = color.rgb(140, 60, 220),
        scale           = (CARD_W, CARD_H),
        position        = (x, y),
    )

    # Nom sous la pochette
    Text(
        album.get("name", "?"),
        parent   = card,
        origin   = (0, .5),
        position = (0, -.54),
        scale    = 4.2,
        color    = color.rgb(210, 200, 240),
    )

    card.album_data = album

    def _click(a=album, c=card):
        _select(a, c)
    card.on_click = _click

    return card


# ─────────────────────────────────────────────────────────────────────────────
#  Sélection
# ─────────────────────────────────────────────────────────────────────────────

def _select(album: dict, card: Button) -> None:
    global selected_album
    for c in album_cards:
        c.color = color.white if c.texture else color.rgb(40, 36, 60)
    selected_album = album
    card.color     = color.rgb(192, 132, 252)

    tracks    = album.get("tracks", [])
    track_str = "  |  ".join(tracks) if tracks else "— aucune piste"
    info_panel.text = (
        f"♪  {album.get('name','?')}   ·   "
        f"{album.get('artist','?')}   ·   "
        f"{album.get('year','?')}        "
        f"Pistes : {track_str}"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Grille
# ─────────────────────────────────────────────────────────────────────────────

def build_grid() -> None:
    global album_cards, _empty_hint

    # Nettoie
    for card in album_cards:
        destroy(card)
    album_cards.clear()
    info_panel.text = ""

    if _empty_hint:
        destroy(_empty_hint)
        _empty_hint = None

    albums = load_albums()

    if not albums:
        _empty_hint = Text(
            "Aucun album  —  appuyez sur  [A]  pour en ajouter un",
            parent   = camera.ui,
            origin   = (0, 0),
            position = (0, 0),
            scale    = 1.1,
            color    = color.rgb(100, 100, 140),
        )
        return

    for i, album in enumerate(albums):
        album_cards.append(_make_card(album, i))


# ─────────────────────────────────────────────────────────────────────────────
#  Thread-safe rebuild depuis popup tkinter
# ─────────────────────────────────────────────────────────────────────────────
_pending_rebuild = False


def _on_album_added(album: dict) -> None:
    global _pending_rebuild
    _pending_rebuild = True


def update():
    global _pending_rebuild
    if _pending_rebuild:
        _pending_rebuild = False
        build_grid()


# ─────────────────────────────────────────────────────────────────────────────
#  Clavier
# ─────────────────────────────────────────────────────────────────────────────

def input(key):
    if key == "a":
        open_add_album_popup(on_success=_on_album_added)
    elif key == "escape":
        application.quit()


# ─────────────────────────────────────────────────────────────────────────────
#  Démarrage
# ─────────────────────────────────────────────────────────────────────────────
build_grid()
app.run()
