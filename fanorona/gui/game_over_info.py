from dataclasses import dataclass


@dataclass
class GameOverInfo:
    """Resumo do resultado de uma partida, usado para preencher a tela de fim de jogo."""

    winner_name: str
    reason_text: str
    winner_pieces_remaining: int
    duration_seconds: float
