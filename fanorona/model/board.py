"""TOPOLOGIA:
Todas as intersecções vizinhas na horizontal e na vertical são sempre
ligadas por uma linha. As ligações diagonais existem apenas em metade
das "células" do tabuleiro, alternando em padrão de tabuleiro de xadrez
(é isso que forma o desenho característico de "X" alternados do
Fanorona). Essa alternância é calculada em `is_connected`.
"""

from typing import List, Optional

from . import direction as directions
from .color import Color
from .point import Point

ROWS = 5
COLS = 9


class Board:
    """Tabuleiro de Fanorona: 5 linhas x 9 colunas (45 intersecções),
    22 peças para cada jogador na posição inicial clássica e a casa
    central vazia.
    """

    def __init__(self) -> None:
        self._grid: List[List[Optional[Color]]] = [[None] * COLS for _ in range(ROWS)]
        self._setup_initial_position()

    def _setup_initial_position(self) -> None:
        """Monta a posição inicial padrão do Fanorona (22 peças por jogador)."""
        # As duas linhas mais próximas de cada jogador começam completas.
        for c in range(COLS):
            self._grid[0][c] = Color.WHITE
            self._grid[1][c] = Color.WHITE
            self._grid[3][c] = Color.BLACK
            self._grid[4][c] = Color.BLACK

        # Linha central (2): metade branca, metade preta, centro vazio.
        for c in range(4):
            self._grid[2][c] = Color.WHITE
        self._grid[2][4] = None
        for c in range(5, COLS):
            self._grid[2][c] = Color.BLACK

    def piece_at(self, p: Point) -> Optional[Color]:
        return self._grid[p.row][p.col]

    def is_empty(self, p: Point) -> bool:
        return self.piece_at(p) is None

    def set(self, p: Point, color: Optional[Color]) -> None:
        self._grid[p.row][p.col] = color

    def clear(self, p: Point) -> None:
        self._grid[p.row][p.col] = None

    def move_piece(self, frm: Point, to: Point) -> None:
        """Move uma peça (sem lógica de captura) de `frm` para `to`."""
        color = self.piece_at(frm)
        self.clear(frm)
        self.set(to, color)

    def count_pieces(self, color: Color) -> int:
        """Conta quantas peças de uma cor ainda existem no tabuleiro."""
        return sum(1 for row in self._grid for cell in row if cell is color)

    def is_connected(self, frm: Point, d) -> bool:
        """Verifica se existe uma linha (aresta) do tabuleiro ligando o
        ponto `frm` ao ponto vizinho `frm + d`. Não verifica ocupação,
        apenas a existência geométrica da linha.
        """
        to = frm.plus(d)
        if not frm.in_bounds() or not to.in_bounds():
            return False

        if not d.is_diagonal():
            # Linhas horizontais e verticais sempre existem entre vizinhos.
            return True

        # Linha diagonal: existe apenas se a "célula" associada a essa
        # diagonal tiver paridade par (linha + coluna da célula par).
        cell_row = frm.row - 1 if d.dr == -1 else frm.row
        cell_col = frm.col - 1 if d.dc == -1 else frm.col

        if cell_row < 0 or cell_row > ROWS - 2 or cell_col < 0 or cell_col > COLS - 2:
            return False
        return (cell_row + cell_col) % 2 == 0

    def valid_directions_from(self, p: Point):
        """Retorna todas as direções válidas (linhas existentes) a partir de um ponto."""
        return [d for d in directions.ALL if self.is_connected(p, d)]
