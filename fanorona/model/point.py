from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """Representa uma intersecção (casa) do tabuleiro pela linha (row) e coluna (col)."""

    row: int
    col: int

    def in_bounds(self) -> bool:
        """Verifica se o ponto está dentro dos limites do tabuleiro."""
        # Import atrasado (dentro da função) para evitar import circular:
        # board.py também precisa conhecer Point, então não podemos importar
        # Board no topo deste arquivo.
        from .board import ROWS, COLS

        return 0 <= self.row < ROWS and 0 <= self.col < COLS

    def plus(self, direction) -> "Point":
        """Retorna o ponto resultante de somar uma direção a este ponto."""
        return Point(self.row + direction.dr, self.col + direction.dc)

    def minus(self, direction) -> "Point":
        """Retorna o ponto resultante de subtrair uma direção deste ponto."""
        return Point(self.row - direction.dr, self.col - direction.dc)
