"""
main.py
-------
Application Ursina – Bibliothèque d'albums musicaux.

Contrôles :
  A      → ajouter un album
  Échap  → quitter
  Clic pochette → sélectionner / désélectionner
  Clic re-sélection → désélectionne
"""

from ursina import *
from ursina.prefabs.button import Button
import os

from album_library import load_albums, open_add_album_popup, open_add_tracks_popup
from player import PlayerBar

# ─────────────────────────────────────────────────────────────────────────────
#  Config grille
# ─────────────────────────────────────────────────────────────────────────────
COLS       = 4
CARD_SCALE = 0.18
GAP_X      = 0.22
GAP_Y      = 0.26
START_X    = -0.33
START_Y    = 0.28

# ─────────────────────────────────────────────────────────────────────────────
#  App
# ─────────────────────────────────────────────────────────────────────────────
app = Ursina(title='Album Library', borderless=False)
window.color = color._16

# ─────────────────────────────────────────────────────────────────────────────
#  État global
# ─────────────────────────────────────────────────────────────────────────────
album_cards    = []
selected_album = None
selected_card  = None
_empty_hint    = None
_pending       = False
_pending_info  = None

# ─────────────────────────────────────────────────────────────────────────────
#  Lecteur (barre en bas)
# ─────────────────────────────────────────────────────────────────────────────
player_bar = PlayerBar()

# ─────────────────────────────────────────────────────────────────────────────
#  UI fixe — en-tête
# ─────────────────────────────────────────────────────────────────────────────
# Icône logo à gauche du titre (optionnel, si assets/icons/logo.png existe)
_logo_path = os.path.join('assets', 'icons', 'logo.png')
if os.path.isfile(_logo_path):
    Entity(
        parent   = camera.ui,
        model    = 'quad',
        texture  = load_texture(_logo_path),
        color    = color.white,
        scale    = .045,
        position = (-.88, .46),
    )
Text(
    'Album Library',
    parent   = camera.ui,
    origin   = (-.5, .5),
    position = (-.83, .46),
    scale    = 1.4,
    color    = color.violet,
)

Text(
    '[A] Ajouter un album',
    parent   = camera.ui,
    origin   = (.5, .5),
    position = (.88, .46),
    scale    = .85,
    color    = color.gray,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Bouton « + Musiques » — visible seulement quand album sélectionné
# ─────────────────────────────────────────────────────────────────────────────
btn_add_tracks = Button(
    parent          = camera.ui,
    text            = '+ Musiques',
    color           = color.dark_gray,
    highlight_color = color.violet,
    pressed_color   = color.magenta,
    scale           = 0.14,
    position        = (.74, -.36),
    visible         = False,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Texture
# ─────────────────────────────────────────────────────────────────────────────
def _tex(path):
    if path and os.path.isfile(path):
        try:
            return load_texture(path)
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Carte album
# ─────────────────────────────────────────────────────────────────────────────
def _make_card(album, idx):
    col = idx % COLS
    row = idx // COLS
    x   = START_X + col * GAP_X
    y   = START_Y - row * GAP_Y

    tex = _tex(album.get('cover', ''))

    card = Button(
        parent          = camera.ui,
        text            = '',
        texture         = tex,
        color           = color.white if tex else color.dark_gray,
        highlight_color = color.violet,
        pressed_color   = color.magenta,
        scale           = CARD_SCALE,
        position        = (x, y),
    )

    Text(
        album.get('name', '?'),
        parent   = card,
        origin   = (0, .5),
        position = (0, -.6),
        scale    = 4,
        color    = color.light_gray,
    )

    card.album_data = album

    def _on_click(a=album, c=card):
        _toggle_select(a, c)
    card.on_click = _on_click

    return card


# ─────────────────────────────────────────────────────────────────────────────
#  Sélection / Désélection
# ─────────────────────────────────────────────────────────────────────────────
def _deselect():
    """Désélectionne l'album courant, cache la barre et le bouton musiques."""
    global selected_album, selected_card
    for c in album_cards:
        c.color = color.white if c.texture else color.dark_gray
    selected_album = None
    selected_card  = None
    btn_add_tracks.visible = False
    player_bar.hide()


def _toggle_select(album, card):
    """Sélectionne l'album, ou le désélectionne si déjà sélectionné."""
    global selected_album, selected_card

    # Déjà sélectionné → désélectionne
    if selected_album and selected_album.get('id') == album.get('id'):
        _deselect()
        return

    # Sélectionne le nouvel album
    for c in album_cards:
        c.color = color.white if c.texture else color.dark_gray
    card.color     = color.violet
    selected_album = album
    selected_card  = card

    # Bouton + Musiques
    btn_add_tracks.visible = True

    def _open_tracks(a=album):
        open_add_tracks_popup(a, on_success=_on_tracks_added)
    btn_add_tracks.on_click = _open_tracks

    # Lecteur : charge l'album et affiche la barre
    player_bar.load_album(album)
    player_bar.show()


# ─────────────────────────────────────────────────────────────────────────────
#  Callbacks thread-safe
# ─────────────────────────────────────────────────────────────────────────────
def _on_album_added(album):
    global _pending
    _pending = True


def _on_tracks_added(updated_album):
    global _pending_info
    _pending_info = updated_album


# ─────────────────────────────────────────────────────────────────────────────
#  Grille
# ─────────────────────────────────────────────────────────────────────────────
def build_grid():
    global album_cards, _empty_hint, selected_album, selected_card

    for c in album_cards:
        destroy(c)
    album_cards.clear()
    selected_album = None
    selected_card  = None
    btn_add_tracks.visible = False
    player_bar.hide()

    if _empty_hint:
        destroy(_empty_hint)
        _empty_hint = None

    albums = load_albums()

    if not albums:
        _empty_hint = Text(
            "Aucun album  —  appuyez sur  [A]  pour commencer",
            parent   = camera.ui,
            origin   = (0, 0),
            position = (0, 0),
            scale    = 1.0,
            color    = color.gray,
        )
        return

    for i, album in enumerate(albums):
        album_cards.append(_make_card(album, i))


# ─────────────────────────────────────────────────────────────────────────────
#  update() — chaque frame
# ─────────────────────────────────────────────────────────────────────────────
def update():
    global _pending, _pending_info

    # Rebuild grille complet
    if _pending:
        _pending = False
        build_grid()
        return

    # Rafraîchit pistes d'un album sans rebuild
    if _pending_info:
        updated       = _pending_info
        _pending_info = None
        for c in album_cards:
            if c.album_data.get('id') == updated.get('id'):
                c.album_data = updated
                break
        # Recharge le lecteur si c'est l'album en cours
        if selected_album and selected_album.get('id') == updated.get('id'):
            selected_album = updated
            player_bar.load_album(updated)

    # Met à jour la barre de lecture chaque frame
    player_bar.update()


# ─────────────────────────────────────────────────────────────────────────────
#  Input — clavier + clic barre de progression
# ─────────────────────────────────────────────────────────────────────────────
def input(key):
    if key == 'a':
        open_add_album_popup(on_success=_on_album_added)
    elif key == 'escape':
        application.quit()
    elif key == 'left mouse down':
        # Seek sur la barre de progression
        player_bar.handle_click(mouse.x, mouse.y)


# ─────────────────────────────────────────────────────────────────────────────
#  Lancement
# ─────────────────────────────────────────────────────────────────────────────
build_grid()
app.run()
