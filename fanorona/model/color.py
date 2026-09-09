from enum import Enum


class Color(Enum):
    """Cor de uma peça/jogador no Fanorona."""

    WHITE = "WHITE"
    BLACK = "BLACK"

    def opposite(self) -> "Color":
        """Retorna a cor adversária."""
        return Color.BLACK if self is Color.WHITE else Color.WHITE
