"""Desenha o tabuleiro (linhas e peças) num `tk.Canvas` e converte
cliques do mouse em intersecções (Point). Em vez de desenhar linha por
linha a cada atualização, criamos formas (`create_line`, `create_oval`)
que o Canvas mantém — para "redesenhar" simplesmente apagamos tudo
(`delete("all")`) e recriamos.
"""

import tkinter as tk
from typing import Callable, List, Optional

from . import theme
from ..model.board import COLS, ROWS
from ..model import direction as directions
from ..model.color import Color
from ..model.game_engine import GameEngine
from ..model.point import Point

MARGIN = 38
SPACING = 58
PIECE_RADIUS = 17
POINT_RADIUS = 3

_LAST_MOVE_COLOR = "#9A9280"


class BoardCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc, on_point_clicked: Optional[Callable[[Point], None]] = None) -> None:
        width = MARGIN * 2 + SPACING * (COLS - 1)
        height = MARGIN * 2 + SPACING * (ROWS - 1)
        super().__init__(master, width=width, height=height, bg=theme.BOARD_BG, highlightthickness=0)

        self.engine: Optional[GameEngine] = None
        self.selected: Optional[Point] = None
        self.highlighted: List[Point] = []
        self.last_from: Optional[Point] = None
        self.last_to: Optional[Point] = None
        self.on_point_clicked = on_point_clicked

        self.bind("<Button-1>", self._handle_click)

    def set_engine(self, engine: GameEngine) -> None:
        self.engine = engine
        self.redraw()

    def set_selected(self, point: Optional[Point]) -> None:
        self.selected = point
        self.redraw()

    def set_highlighted(self, points: List[Point]) -> None:
        self.highlighted = points
        self.redraw()

    def set_last_move(self, frm: Point, to: Point) -> None:
        self.last_from = frm
        self.last_to = to
        self.redraw()

    def _px(self, col: int) -> int:
        return MARGIN + col * SPACING

    def _py(self, row: int) -> int:
        return MARGIN + row * SPACING

    def _pixel_to_point(self, x: int, y: int) -> Optional[Point]:
        for r in range(ROWS):
            for c in range(COLS):
                dx = x - self._px(c)
                dy = y - self._py(r)
                if dx * dx + dy * dy <= PIECE_RADIUS * PIECE_RADIUS:
                    return Point(r, c)
        return None

    def _handle_click(self, event: tk.Event) -> None:
        p = self._pixel_to_point(event.x, event.y)
        if p is not None and self.on_point_clicked is not None:
            self.on_point_clicked(p)

    def redraw(self) -> None:
        self.delete("all")
        if self.engine is None:
            return
        self._draw_lines()
        self._draw_last_move_marker()
        self._draw_points()
        self._draw_highlights()
        self._draw_pieces()

    def _draw_lines(self) -> None:
        board = self.engine.board
        for r in range(ROWS):
            for c in range(COLS):
                p = Point(r, c)
                # desenha apenas para leste e sul (e diagonais correspondentes),
                # evitando desenhar cada linha duas vezes
                for d in (directions.E, directions.S, directions.SE, directions.SW):
                    if board.is_connected(p, d):
                        q = p.plus(d)
                        self.create_line(
                            self._px(c), self._py(r), self._px(q.col), self._py(q.row),
                            fill=theme.BOARD_LINE, width=1.4,
                        )

    def _draw_points(self) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                if self.engine.board.is_empty(Point(r, c)):
                    x, y = self._px(c), self._py(r)
                    self.create_oval(
                        x - POINT_RADIUS, y - POINT_RADIUS, x + POINT_RADIUS, y + POINT_RADIUS,
                        fill=theme.BOARD_LINE, outline="",
                    )

    def _draw_last_move_marker(self) -> None:
        if self.last_from is None or self.last_to is None:
            return
        self.create_line(
            self._px(self.last_from.col), self._py(self.last_from.row),
            self._px(self.last_to.col), self._py(self.last_to.row),
            fill=_LAST_MOVE_COLOR, width=3.5,
        )

    def _draw_highlights(self) -> None:
        if self.selected is not None:
            x, y = self._px(self.selected.col), self._py(self.selected.row)
            r = PIECE_RADIUS + 4
            self.create_oval(x - r, y - r, x + r, y + r, outline=theme.ACCENT_DARK, width=2.6)
        for p in self.highlighted:
            x, y = self._px(p.col), self._py(p.row)
            self.create_oval(x - 7, y - 7, x + 7, y + 7, fill=theme.ACCENT, outline="")

    def _draw_pieces(self) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                color = self.engine.board.piece_at(Point(r, c))
                if color is None:
                    continue
                x, y = self._px(c), self._py(r)
                fill = theme.PIECE_DARK if color is Color.WHITE else theme.PIECE_GOLD
                self.create_oval(
                    x - PIECE_RADIUS, y - PIECE_RADIUS, x + PIECE_RADIUS, y + PIECE_RADIUS,
                    fill=fill, outline=theme.CARD_BG, width=1.5,
                )
