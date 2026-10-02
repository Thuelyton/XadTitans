"""Cena de Carregamento de Partidas PGN do XadTitans.

Lista arquivos PGN no diretório de dados e permite carregar uma partida
ou exibe mensagem caso nenhum PGN seja encontrado.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from xadtitans.audio import AudioManager
from xadtitans.config import COLOR_BG, WINDOW_HEIGHT, WINDOW_WIDTH
from xadtitans.i18n import t
from xadtitans.storage.pgn import list_pgn_files, load_game, reconstruct_board
from xadtitans.ui.widgets.button import Button

if TYPE_CHECKING:
    from xadtitans.ui.scene_manager import SceneManager


class LoadScene:
    """Tela de seleção e carregamento de arquivos PGN."""

    def __init__(
        self,
        scene_manager: SceneManager | None = None,
        audio: AudioManager | None = None,
    ) -> None:
        self.scene_manager = scene_manager
        self.audio = audio or AudioManager()

        self._title_font = pygame.font.SysFont("arial", 38, bold=True)
        self._msg_font = pygame.font.SysFont("arial", 20)
        self._item_font = pygame.font.SysFont("arial", 18)

        self.pgn_files: list[Path] = list_pgn_files()
        self.file_buttons: list[tuple[Path, Button]] = []
        self._build_file_list()

        btn_w, btn_h = 200, 44
        self.btn_back = Button(
            rect=(WINDOW_WIDTH // 2 - btn_w // 2, WINDOW_HEIGHT - 70, btn_w, btn_h),
            text=t("common.back"),
            callback=self._go_back,
        )

    def _build_file_list(self) -> None:
        self.pgn_files = list_pgn_files()
        self.file_buttons.clear()

        btn_w, btn_h = 440, 40
        start_y = 170
        spacing = 48
        center_x = WINDOW_WIDTH // 2 - btn_w // 2

        for idx, pgn_path in enumerate(self.pgn_files[:8]):  # Exibe até 8 arquivos
            rect = (center_x, start_y + idx * spacing, btn_w, btn_h)
            filename = pgn_path.name
            btn = Button(
                rect=rect,
                text=filename,
                callback=lambda p=pgn_path: self._load_pgn_file(p),
                font=self._item_font,
            )
            self.file_buttons.append((pgn_path, btn))

    def _load_pgn_file(self, path: Path) -> None:
        self.audio.play("click")
        pgn_game = load_game(path)
        if pgn_game is None:
            return

        final_board = reconstruct_board(pgn_game)

        if self.scene_manager is not None:
            from xadtitans.ui.scenes.game_scene import GameScene

            game_scene = GameScene(audio=self.audio)
            game_scene.game.board = final_board
            game_scene._sync_view()
            # Partidas vindas de PGN não gravam autosave — o botão
            # Carregar continua significando apenas PGN.
            game_scene._autosave_enabled = False
            self.scene_manager.switch(game_scene)

    def _go_back(self) -> None:
        self.audio.play("click")
        if self.scene_manager is not None:
            self.scene_manager.pop()

    # ── ciclo de vida ─────────────────────────────────────

    def on_enter(self) -> None:
        self._build_file_list()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._go_back()
            return

        for _, btn in self.file_buttons:
            if btn.handle_event(event):
                return

        if self.btn_back.handle_event(event):
            return

    def update(self, dt: float) -> None:
        pos = pygame.mouse.get_pos()
        for _, btn in self.file_buttons:
            btn.update_hover(pos)
        self.btn_back.update_hover(pos)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BG)

        # Título
        title_surf = self._title_font.render(t("load.title"), True, (255, 215, 0))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 70))
        surface.blit(title_surf, title_rect)

        if not self.pgn_files:
            msg_surf = self._msg_font.render(t("load.no_pgns"), True, (240, 100, 100))
            msg_rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, 250))
            surface.blit(msg_surf, msg_rect)
        else:
            hdr_surf = self._msg_font.render(t("load.select_pgn"), True, (240, 240, 240))
            surface.blit(hdr_surf, (WINDOW_WIDTH // 2 - 220, 130))

            for _, btn in self.file_buttons:
                btn.draw(surface)

        self.btn_back.draw(surface)
