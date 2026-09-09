"""Chamado de "direction" em vez de "dir" para não conflitar com a função
embutida `dir()` do Python.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Direction:
    """Direção de movimento no tabuleiro (deltaRow, deltaCol).

    Cada componente vale -1, 0 ou +1 (não podem ser ambos 0).
    """

    dr: int
    dc: int

    def opposite(self) -> "Direction":
        """Retorna a direção oposta (usada na captura por afastamento)."""
        return Direction(-self.dr, -self.dc)

    def is_diagonal(self) -> bool:
        """Se a direção é diagonal (usa as linhas "X" das células do tabuleiro)."""
        return self.dr != 0 and self.dc != 0

    @staticmethod
    def between(frm, to) -> "Direction":
        """Direção de `frm` para `to` (assume que são vizinhos diretos)."""

        def sign(x: int) -> int:
            return (x > 0) - (x < 0)

        return Direction(sign(to.row - frm.row), sign(to.col - frm.col))


N = Direction(-1, 0)
S = Direction(1, 0)
W = Direction(0, -1)
E = Direction(0, 1)
NW = Direction(-1, -1)
NE = Direction(-1, 1)
SW = Direction(1, -1)
SE = Direction(1, 1)

ALL = [N, S, W, E, NW, NE, SW, SE]
