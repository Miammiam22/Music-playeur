"""
player.py
---------
Lecteur audio basé sur pygame.mixer.
Barre de lecture en bas de l'écran Ursina.

Depuis main.py :
    from player import PlayerBar
    bar = PlayerBar()
    bar.load_album(album_dict)
    bar.show() / bar.hide()
    # dans update() :   bar.update()
    # dans input()  :   bar.handle_click(mouse.x, mouse.y)
"""

import os
import time
import pygame
from ursina import *
from ursina.prefabs.button import Button

# ── Init pygame.mixer ─────────────────────────────────────────────────────────
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()


def _fmt(sec: float) -> str:
    s = max(0, int(sec))
    return f"{s // 60}:{s % 60:02d}"


# ─────────────────────────────────────────────────────────────────────────────
#  MusicPlayer — logique audio pure
# ─────────────────────────────────────────────────────────────────────────────
class MusicPlayer:
    def __init__(self):
        self.tracks      = []
        self.current_idx = 0
        self.playing     = False
        self.paused      = False
        self._t0         = 0.0   # time.time() au début de la lecture
        self._offset     = 0.0   # secondes déjà écoulées avant pause/seek
        self.duration    = 0.0

    @property
    def position(self) -> float:
        if not self.playing or self.paused:
            return self._offset
        return self._offset + (time.time() - self._t0)

    # ── Chemin absolu de la piste courante ────────────────────────────────────
    def _path(self) -> str | None:
        if not self.tracks:
            return None
        t   = self.tracks[self.current_idx]
        raw = t["path"] if isinstance(t, dict) else t
        if not raw:
            return None
        p = os.path.abspath(raw)
        return p if os.path.isfile(p) else None

    @property
    def track_name(self) -> str:
        if not self.tracks:
            return ''
        t = self.tracks[self.current_idx]
        name = t["name"] if isinstance(t, dict) else str(t)
        # Retire l'extension
        return os.path.splitext(name)[0]

    # ── Chargement ────────────────────────────────────────────────────────────
    def load_track(self, idx: int):
        if not self.tracks:
            return
        self.current_idx = idx % len(self.tracks)
        self._offset     = 0.0
        self.playing     = False
        self.paused      = False
        path = self._path()
        if not path:
            print(f"[Player] Fichier introuvable : {self.tracks[self.current_idx]}")
            self.duration = 0.0
            return
        try:
            pygame.mixer.music.load(path)
            self.duration = self._get_duration(path)
        except Exception as e:
            print(f"[Player] Erreur chargement : {e}")
            self.duration = 0.0

    def _get_duration(self, path: str) -> float:
        try:
            from mutagen.mp3 import MP3
            return MP3(path).info.length
        except Exception:
            pass
        try:
            from mutagen import File
            f = File(path)
            if f and hasattr(f.info, 'length'):
                return f.info.length
        except Exception:
            pass
        return 0.0

    # ── Contrôles ─────────────────────────────────────────────────────────────
    def play(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self._t0     = time.time()
            self.paused  = False
            self.playing = True
        else:
            path = self._path()
            if not path:
                return
            try:
                pygame.mixer.music.play(start=self._offset)
                self._t0     = time.time()
                self.playing = True
                self.paused  = False
            except Exception as e:
                print(f"[Player] Erreur play : {e}")

    def pause(self):
        if self.playing and not self.paused:
            self._offset = self.position
            pygame.mixer.music.pause()
            self.paused = True

    def toggle(self):
        if not self.tracks:
            return
        if not self.playing or self.paused:
            self.play()
        else:
            self.pause()

    def seek(self, seconds: float):
        seconds = max(0.0, min(seconds, self.duration or seconds))
        was_playing = self.playing and not self.paused
        self._offset = seconds
        try:
            pygame.mixer.music.play(start=seconds)
            self._t0     = time.time()
            self.playing = True
            self.paused  = False
        except Exception as e:
            print(f"[Player] Erreur seek : {e}")
            return
        if not was_playing:
            pygame.mixer.music.pause()
            self.paused = True

    def next_track(self):
        if not self.tracks:
            return
        self.load_track(self.current_idx + 1)
        self.play()

    def prev_track(self):
        if not self.tracks:
            return
        if self.position > 3:
            self.seek(0)
        else:
            self.load_track(self.current_idx - 1)
            self.play()

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = False
        self.paused  = False
        self._offset = 0.0

    def is_finished(self) -> bool:
        return self.playing and not self.paused and not pygame.mixer.music.get_busy()


# ─────────────────────────────────────────────────────────────────────────────
#  PlayerBar — UI Ursina
# ─────────────────────────────────────────────────────────────────────────────
class PlayerBar:
    # Coordonnées de la barre (espace camera.ui : ±0.9 environ)
    Y          = -.40          # centre vertical de la barre
    H          = .10           # hauteur totale du fond
    PROG_Y     = -.455         # centre de la ligne de progression
    PROG_W     = .52           # largeur de la zone de progression
    PROG_H     = .008          # épaisseur de la ligne
    PROG_X     = .08           # décalage horizontal centre progression

    def __init__(self):
        self.player     = MusicPlayer()
        self._visible   = False
        self._album     = None
        self._list_open = False
        self._track_btns = []

        # ── Fond ──────────────────────────────────────────────────────────────
        self._bg = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.rgba(0.071, 0.055, 0.118, 0.922),
            scale    = (1.82, self.H),
            position = (0, self.Y, .5),
            visible  = False,
        )

        # ── Séparateur haut ───────────────────────────────────────────────────
        self._sep = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.rgba(0.471, 0.314, 0.784, 0.471),
            scale    = (1.82, .002),
            position = (0, self.Y + self.H / 2, .4),
            visible  = False,
        )

        # ── Pochette miniature ────────────────────────────────────────────────
        self._thumb = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.dark_gray,
            scale    = .078,
            position = (-.83, self.Y, .3),
            visible  = False,
        )

        # ── Nom de la piste ───────────────────────────────────────────────────
        self._lbl_track = Text(
            '',
            parent   = camera.ui,
            origin   = (-.5, 0),
            position = (-.72, self.Y + .022),
            scale    = .85,
            color    = color.white,
        )
        self._lbl_track.visible = False

        # ── Artiste · Album ───────────────────────────────────────────────────
        self._lbl_artist = Text(
            '',
            parent   = camera.ui,
            origin   = (-.5, 0),
            position = (-.72, self.Y - .010),
            scale    = .65,
            color    = color.rgba(0.706, 0.627, 0.824, 0.863),
        )
        self._lbl_artist.visible = False

        # ── Boutons avec icônes PNG (assets/icons/) ──────────────────────────
        def _load_icon(name):
            path = os.path.join('assets', 'icons', name)
            if os.path.isfile(path):
                try:
                    return load_texture(path)
                except Exception:
                    pass
            return None

        # Tailles normales et hover pour l'animation scale
        _scales = {
            'prev': .055, 'play': .068, 'next': .055, 'list': .050,
        }
        _hover_mult = 1.18   # grossit de 18% au hover

        _tex_prev  = _load_icon('prev.png')
        _tex_play  = _load_icon('play.png')
        _tex_next  = _load_icon('next.png')
        _tex_list  = _load_icon('list.png')
        _tex_pause = _load_icon('pause.png')
        self._tex_play  = _tex_play
        self._tex_pause = _tex_pause

        # Couleur de base : blanc pour que la texture PNG s'affiche correctement.
        # highlight/pressed : légère teinte jaune-verte de la palette (#D8D365)
        # highlight_color = color.white → Ursina ne change rien au hover
        # On gère tout manuellement dans update() via b.hovered
        _bc = dict(
            parent          = camera.ui,
            text            = '',
            color           = color.white,
            highlight_color = color.white,
            pressed_color   = color.white,
        )

        def _make_btn(tex, fallback, sz, pos):
            b = Button(texture=tex, scale=sz, position=pos, **_bc)
            if not tex:
                b.text  = fallback
                b.color = color.light_gray
            return b

        self._btn_prev = _make_btn(_tex_prev, '<<', _scales['prev'],
                                   (self.PROG_X - .12, self.Y + .018))
        self._btn_play = _make_btn(_tex_play, '> ', _scales['play'],
                                   (self.PROG_X,       self.Y + .018))
        self._btn_next = _make_btn(_tex_next, '>>', _scales['next'],
                                   (self.PROG_X + .12, self.Y + .018))
        self._btn_list = _make_btn(_tex_list, '=',  _scales['list'],
                                   (self.PROG_X - .26, self.Y + .018))

        # Stocke les tailles de base pour l'animation
        self._btn_prev._base_scale = _scales['prev']
        self._btn_play._base_scale = _scales['play']
        self._btn_next._base_scale = _scales['next']
        self._btn_list._base_scale = _scales['list']
        self._hover_mult = _hover_mult

        for b in (self._btn_prev, self._btn_play, self._btn_next, self._btn_list):
            b.visible = False

        self._btn_prev.on_click = self._on_prev
        self._btn_play.on_click = self._on_play_pause
        self._btn_next.on_click = self._on_next
        self._btn_list.on_click = self._toggle_list

        # ── Temps écoulé ──────────────────────────────────────────────────────
        self._lbl_elapsed = Text(
            '0:00',
            parent   = camera.ui,
            origin   = (.5, 0),
            position = (self.PROG_X - self.PROG_W / 2 - .025, self.PROG_Y),
            scale    = .65,
            color    = color.light_gray,
        )
        self._lbl_elapsed.visible = False

        # ── Durée totale ──────────────────────────────────────────────────────
        self._lbl_total = Text(
            '--:--',
            parent   = camera.ui,
            origin   = (-.5, 0),
            position = (self.PROG_X + self.PROG_W / 2 + .025, self.PROG_Y),
            scale    = .65,
            color    = color.light_gray,
        )
        self._lbl_total.visible = False

        # ── Track fond (gris) ─────────────────────────────────────────────────
        self._track_bg = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.rgba(0.275, 0.235, 0.392, 0.706),
            scale    = (self.PROG_W, self.PROG_H),
            position = (self.PROG_X, self.PROG_Y, .3),
            visible  = False,
        )

        # ── Progression violette ──────────────────────────────────────────────
        self._prog = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.violet,
            scale    = (0.0001, self.PROG_H),
            position = (self.PROG_X - self.PROG_W / 2, self.PROG_Y, .2),
            visible  = False,
        )

        # ── Curseur rond ──────────────────────────────────────────────────────
        self._cursor = Entity(
            parent   = camera.ui,
            model    = 'circle',
            color    = color.white,
            scale    = .014,
            position = (self.PROG_X - self.PROG_W / 2, self.PROG_Y, .1),
            visible  = False,
        )

        # ── Panneau liste des pistes ──────────────────────────────────────────
        self._list_bg = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.rgba(0.086, 0.067, 0.149, 0.941),
            scale    = (.50, .001),
            position = (self.PROG_X - .19, self.Y, .6),
            visible  = False,
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  Chargement
    # ─────────────────────────────────────────────────────────────────────────
    def load_album(self, album: dict):
        self._album = album
        raw = album.get('tracks', [])
        self.player.tracks = [
            t if isinstance(t, dict) else {'name': t, 'path': t}
            for t in raw
        ]
        self._refresh_list_data()
        if self.player.tracks:
            self.player.load_track(0)
            self._update_labels()
        self._update_thumb()

    def _update_thumb(self):
        cover = (self._album or {}).get('cover', '')
        if cover and os.path.isfile(cover):
            try:
                self._thumb.texture = load_texture(cover)
                self._thumb.color   = color.white
                return
            except Exception:
                pass
        self._thumb.texture = None
        self._thumb.color   = color.dark_gray

    def _update_labels(self):
        self._lbl_track.text  = self.player.track_name[:32]
        artist = (self._album or {}).get('artist', '')
        album_name = (self._album or {}).get('name', '')
        self._lbl_artist.text = f"{artist}  ·  {album_name}"

    # ─────────────────────────────────────────────────────────────────────────
    #  Visibilité
    # ─────────────────────────────────────────────────────────────────────────
    def _all(self):
        return [
            self._bg, self._sep, self._thumb,
            self._lbl_track, self._lbl_artist,
            self._btn_prev, self._btn_play, self._btn_next, self._btn_list,
            self._lbl_elapsed, self._lbl_total,
            self._track_bg, self._prog, self._cursor,
        ]

    def show(self):
        self._visible = True
        for e in self._all():
            e.visible = True

    def hide(self):
        self._visible   = False
        self._list_open = False
        for e in self._all():
            e.visible = False
        self._list_bg.visible = False
        self._close_list()

    # ─────────────────────────────────────────────────────────────────────────
    #  Liste des pistes
    # ─────────────────────────────────────────────────────────────────────────
    def _refresh_list_data(self):
        self._close_list()
        self._list_open = False

    def _toggle_list(self):
        if self._list_open:
            self._close_list()
        else:
            self._open_list()

    def _open_list(self):
        self._list_open = True
        tracks  = self.player.tracks
        if not tracks:
            return
        n       = len(tracks)
        row_h   = .050
        pad     = .010
        total_h = n * row_h + pad * 2
        cx      = self.PROG_X - .19
        # La liste s'ouvre AU-DESSUS de la barre, avec un gap pour ne pas empiéter
        bar_top = self.Y + self.H / 2
        gap     = .015
        cy      = bar_top + gap + total_h / 2

        self._list_bg.scale    = (.50, total_h)
        self._list_bg.position = (cx, bar_top + gap + total_h / 2 - total_h / 2, .6)
        self._list_bg.visible  = True

        for i, t in enumerate(tracks):
            name  = t['name'] if isinstance(t, dict) else str(t)
            label = os.path.splitext(name)[0]
            label = label[:30] + '…' if len(label) > 30 else label
            is_cur = (i == self.player.current_idx)
            y_pos  = (bar_top + gap + total_h) - pad - row_h * i - row_h / 2

            btn = Button(
                parent          = camera.ui,
                text            = ('> ' if is_cur else '  ') + label,
                color           = color.rgba(0.431, 0.314, 0.706, 0.784) if is_cur
                                  else color.rgba(0.125, 0.102, 0.204, 0.863),
                highlight_color = color.rgba(0.588, 0.431, 0.863, 0.863),
                pressed_color   = color.violet,
                scale           = (.49, row_h * .88),
                position        = (cx, y_pos, .5),
                text_origin     = (-.5, 0),
            )

            def _play(idx=i):
                self.player.load_track(idx)
                self.player.play()
                self._btn_play.texture = (self._tex_pause if self._tex_pause else None) or self._btn_play.texture; self._btn_play.text = '' if self._tex_pause else '||'
                self._update_labels()
                self._close_list()
                self._list_open = False

            btn.on_click = _play
            self._track_btns.append(btn)

    def _close_list(self):
        self._list_bg.visible = False
        for b in self._track_btns:
            destroy(b)
        self._track_btns.clear()
        self._list_open = False

    # ─────────────────────────────────────────────────────────────────────────
    #  Callbacks boutons
    # ─────────────────────────────────────────────────────────────────────────
    def _on_play_pause(self):
        self.player.toggle()
        is_playing = self.player.playing and not self.player.paused
        if self._tex_play and self._tex_pause:
            self._btn_play.texture = self._tex_pause if is_playing else self._tex_play
        else:
            self._btn_play.text = '||' if is_playing else '> '

    def _on_next(self):
        self.player.next_track()
        self._btn_play.texture = (self._tex_pause if self._tex_pause else None) or self._btn_play.texture; self._btn_play.text = '' if self._tex_pause else '||'
        self._update_labels()
        if self._list_open:
            self._close_list()
            self._open_list()

    def _on_prev(self):
        self.player.prev_track()
        self._btn_play.texture = (self._tex_pause if self._tex_pause else None) or self._btn_play.texture; self._btn_play.text = '' if self._tex_pause else '||'
        self._update_labels()
        if self._list_open:
            self._close_list()
            self._open_list()

    # ─────────────────────────────────────────────────────────────────────────
    #  Clic sur la barre de progression → seek
    # ─────────────────────────────────────────────────────────────────────────
    def handle_click(self, mx: float, my: float):
        if not self._visible:
            return
        left  = self.PROG_X - self.PROG_W / 2
        right = self.PROG_X + self.PROG_W / 2
        top   = self.PROG_Y + .018
        bot   = self.PROG_Y - .018
        if left <= mx <= right and bot <= my <= top:
            ratio = (mx - left) / self.PROG_W
            ratio = max(0.0, min(1.0, ratio))
            if self.player.duration:
                self.player.seek(ratio * self.player.duration)
                self._btn_play.texture = (self._tex_pause if self._tex_pause else None) or self._btn_play.texture; self._btn_play.text = '' if self._tex_pause else '||' if not self.player.paused else '▶'

    # ─────────────────────────────────────────────────────────────────────────
    #  update() — appelé chaque frame depuis main.py
    # ─────────────────────────────────────────────────────────────────────────
    def update(self):
        if not self._visible:
            return

        p   = self.player
        pos = p.position
        dur = p.duration

        # Passage automatique à la piste suivante
        if p.is_finished() and p.tracks:
            nxt = p.current_idx + 1
            if nxt < len(p.tracks):
                p.load_track(nxt)
                p.play()
                self._update_labels()
                self._btn_play.texture = (self._tex_pause if self._tex_pause else None) or self._btn_play.texture; self._btn_play.text = '' if self._tex_pause else '||'
                if self._list_open:
                    self._close_list()
                    self._open_list()
            else:
                p.stop()
                self._btn_play.texture = (self._tex_play if self._tex_play else None) or self._btn_play.texture; self._btn_play.text = '' if self._tex_play else '> '

        # Temps
        self._lbl_elapsed.text = _fmt(pos)
        self._lbl_total.text   = _fmt(dur) if dur else '--:--'

        # Barre de progression
        ratio    = min(pos / dur, 1.0) if dur else 0.0
        left     = self.PROG_X - self.PROG_W / 2
        prog_w   = max(0.0001, ratio * self.PROG_W)
        self._prog.scale_x = prog_w
        self._prog.x       = left + prog_w / 2
        self._cursor.x     = left + ratio * self.PROG_W

        # ── Animation hover : scale fluide, pas de clignotement ────────────
        # On gère entièrement la couleur et le scale — Ursina ne touche à rien.
        SPEED = 12
        import ursina as _ursina
        _dt = _ursina.time.dt
        for b in (self._btn_prev, self._btn_play, self._btn_next, self._btn_list):
            if not b.visible:
                continue
            base   = getattr(b, '_base_scale', 0.055)
            target = base * self._hover_mult if b.hovered else base
            new_s  = b.scale_x + (target - b.scale_x) * min(1.0, SPEED * _dt)
            b.scale = new_s
            # Couleur : blanc normal → jaune-vert palette au hover, sans clignotement
            target_col = color.Color(60/360, 0.25, 1.0, 1.0) if b.hovered else color.white
            r = b.color[0] + (target_col[0] - b.color[0]) * min(1.0, SPEED * _dt)
            g = b.color[1] + (target_col[1] - b.color[1]) * min(1.0, SPEED * _dt)
            bl = b.color[2] + (target_col[2] - b.color[2]) * min(1.0, SPEED * _dt)
            b.color = color.Color(r, g, bl, 1.0)
