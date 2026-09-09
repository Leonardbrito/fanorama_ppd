"""Cartão lateral com o histórico de jogadas, no formato:
    "#n Nome C2 → C3 (captura xN)"
"""

import tkinter as tk

from . import theme


class HistoryPanel(tk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=theme.CARD_BG, highlightbackground=theme.CARD_BORDER,
                          highlightthickness=1, bd=0)
        self._counter = 0

        tk.Label(self, text="HISTÓRICO", font=theme.CARD_TITLE_FONT, fg=theme.TEXT_MUTED,
                 bg=theme.CARD_BG).pack(anchor="w", padx=16, pady=(14, 6))

        list_frame = tk.Frame(self, bg=theme.CARD_BG)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(
            list_frame, bg=theme.CARD_BG, fg=theme.TEXT, bd=0, highlightthickness=0,
            font=theme.BODY_FONT, activestyle="none",
            selectbackground=theme.CARD_BG, selectforeground=theme.TEXT,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.configure(command=self.listbox.yview)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def add_entry(self, mover_name: str, from_label: str, to_label: str, captured_count: int) -> None:
        self._counter += 1
        note = f" (captura x{captured_count})" if captured_count > 0 else ""
        self.listbox.insert("end", f"#{self._counter} {mover_name} {from_label} → {to_label}{note}")
        self.listbox.see("end")
