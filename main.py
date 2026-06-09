"""
main.py
-------
Application Ursina – Bibliothèque d'albums musicaux.

Contrôles :
  A      → ouvrir la popup « Ajouter un album »
  Échap  → quitter
  Clic   → sélectionner un album (affiche le bouton + Musiques)
"""

from ursina import *
from ursina.prefabs.button import Button
import os

from album_library import load_albums, open_add_album_popup, open_add_tracks_popup

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
selected_album = None   # dict de l'album actuellement sélectionné
_empty_hint    = None
_pending       = False  # rebuild grille après ajout album
_pending_info  = None   # album mis à jour (après ajout tracks)

# ─────────────────────────────────────────────────────────────────────────────
#  UI fixe — en-tête
# ─────────────────────────────────────────────────────────────────────────────
Text(
    '♫  Album Library',
    parent   = camera.ui,
    origin   = (-.5, .5),
    position = (-.88, .46),
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
#  Panneau bas — infos album sélectionné
# ─────────────────────────────────────────────────────────────────────────────
info_txt = Text(
    '',
    parent   = camera.ui,
    origin   = (0, 0),
    position = (0, -.42),
    scale    = .75,
    color    = color.light_gray,
)

# Bouton « + Musiques » — caché par défaut, visible quand album sélectionné
btn_add_tracks = Button(
    parent          = camera.ui,
    text            = '♪ + Musiques',
    color           = color.rgb(30, 20, 50) if hasattr(color, 'rgb') else color.dark_gray,
    highlight_color = color.violet,
    pressed_color   = color.magenta,
    scale           = 0.16,
    position        = (.68, -.42),
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
    y   = START_Y  - row * GAP_Y

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
        _select(a, c)
    card.on_click = _on_click

    return card


# ─────────────────────────────────────────────────────────────────────────────
#  Sélection d'un album
# ─────────────────────────────────────────────────────────────────────────────
def _select(album, card):
    global selected_album

    # Réinitialise couleurs
    for c in album_cards:
        c.color = color.white if c.texture else color.dark_gray
    card.color     = color.violet
    selected_album = album

    # Infos en bas
    tracks = album.get('tracks', [])
    if tracks:
        # tracks = liste de dicts {"name":..., "path":...} ou strings (ancien format)
        t_str = '  |  '.join(t['name'] if isinstance(t, dict) else t for t in tracks)
    else:
        t_str = '— aucune piste'

    info_txt.text = (
        f"♪  {album.get('name','?')}   ·   "
        f"{album.get('artist','?')}   ·   "
        f"{album.get('year','?')}        "
        f"Pistes : {t_str}"
    )

    # Affiche le bouton + Musiques
    btn_add_tracks.visible = True

    # Branche le callback du bouton sur l'album courant
    def _open_tracks(a=album):
        open_add_tracks_popup(a, on_success=_on_tracks_added)
    btn_add_tracks.on_click = _open_tracks


# ─────────────────────────────────────────────────────────────────────────────
#  Callback ajout de pistes (thread tkinter → update Ursina)
# ─────────────────────────────────────────────────────────────────────────────
def _on_tracks_added(updated_album):
    """Appelé depuis le thread tkinter après import de pistes."""
    global _pending_info
    _pending_info = updated_album   # traité dans update()


# ─────────────────────────────────────────────────────────────────────────────
#  Grille
# ─────────────────────────────────────────────────────────────────────────────
def build_grid():
    global album_cards, _empty_hint, selected_album

    for c in album_cards:
        destroy(c)
    album_cards.clear()
    selected_album = None
    info_txt.text  = ''
    btn_add_tracks.visible = False

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
#  Rebuild thread-safe dans update()
# ─────────────────────────────────────────────────────────────────────────────
def _on_album_added(album):
    global _pending
    _pending = True


def update():
    global _pending, _pending_info

    # Nouvel album ajouté → reconstruction complète de la grille
    if _pending:
        _pending = False
        build_grid()

    # Pistes ajoutées → met à jour uniquement l'affichage info + la carte concernée
    if _pending_info:
        updated = _pending_info
        _pending_info = None

        # Rafraîchit le panneau d'info si c'est l'album actuellement sélectionné
        if selected_album and selected_album.get('id') == updated.get('id'):
            tracks = updated.get('tracks', [])
            t_str  = '  |  '.join(t['name'] if isinstance(t, dict) else t for t in tracks) if tracks else '— aucune piste'
            info_txt.text = (
                f"♪  {updated.get('name','?')}   ·   "
                f"{updated.get('artist','?')}   ·   "
                f"{updated.get('year','?')}        "
                f"Pistes : {t_str}"
            )
            # Met à jour la référence locale
            for c in album_cards:
                if c.album_data.get('id') == updated.get('id'):
                    c.album_data = updated
                    break


# ─────────────────────────────────────────────────────────────────────────────
#  Input clavier
# ─────────────────────────────────────────────────────────────────────────────
def input(key):
    if key == 'a':
        open_add_album_popup(on_success=_on_album_added)
    elif key == 'escape':
        application.quit()


# ─────────────────────────────────────────────────────────────────────────────
#  Lancement
# ─────────────────────────────────────────────────────────────────────────────
build_grid()
app.run()
