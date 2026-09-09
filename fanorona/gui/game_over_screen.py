"""Tela final exibida quando a partida termina: vencedor, motivo,
estatísticas (peças restantes do vencedor, duração) e as ações
Sair / Jogar novamente.
"""

import tkinter as tk
from typing import Callable

from . import theme
from .game_over_info import GameOverInfo


class GameOverScreen(tk.Frame):
    def __init__(
        self, master: tk.Misc, info: GameOverInfo, on_exit: Callable[[], None], on_rematch: Callable[[], None]
    ) -> None:
        super().__init__(master, bg=theme.APP_BG)

        card = theme.card(self, padx=34, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        medal = tk.Canvas(card, width=48, height=48, bg=theme.CARD_BG, highlightthickness=0)
        medal.create_oval(2, 2, 46, 46, fill=theme.ACCENT_SOFT, outline="")
        medal.create_text(24, 24, text="★", fill=theme.ACCENT_DARK, font=("Helvetica", 18))
        medal.pack(pady=(0, 10))

        tk.Label(card, text="FIM DE JOGO", font=theme.EYEBROW_FONT, fg=theme.ACCENT_DARK,
                 bg=theme.CARD_BG).pack()
        tk.Label(card, text=f"{info.winner_name} venceu!", font=theme.BIG_TITLE_FONT, fg=theme.TEXT,
                 bg=theme.CARD_BG).pack(pady=(6, 6))
        tk.Label(card, text=info.reason_text, font=theme.SUBTITLE_FONT, fg=theme.TEXT_MUTED,
                 bg=theme.CARD_BG, wraplength=250, justify="center").pack(pady=(0, 18))

        tk.Frame(card, bg=theme.CARD_BORDER, height=1).pack(fill="x", pady=(0, 18))

        stats = tk.Frame(card, bg=theme.CARD_BG)
        stats.pack(pady=(0, 22))
        self._stat_block(stats, "PEÇAS RESTANTES", str(info.winner_pieces_remaining)).pack(side="left", padx=22)
        self._stat_block(stats, "DURAÇÃO", self._format_duration(info.duration_seconds)).pack(side="left", padx=22)

        buttons = tk.Frame(card, bg=theme.CARD_BG)
        buttons.pack(fill="x")
        theme.secondary_button(buttons, "Sair", on_exit).pack(side="left", expand=True, fill="x", padx=(0, 6))
        theme.primary_button(buttons, "Jogar novamente", on_rematch).pack(
            side="left", expand=True, fill="x", padx=(6, 0)
        )

    def _stat_block(self, parent: tk.Widget, label: str, value: str) -> tk.Frame:
        block = tk.Frame(parent, bg=theme.CARD_BG)
        tk.Label(block, text=label, font=theme.CARD_TITLE_FONT, fg=theme.TEXT_MUTED, bg=theme.CARD_BG).pack()
        tk.Label(block, text=value, font=theme.STAT_VALUE_FONT, fg=theme.TEXT, bg=theme.CARD_BG).pack(pady=(4, 0))
        return block

    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes = int(seconds // 60)
        return "<1 min" if minutes < 1 else f"{minutes} min"
