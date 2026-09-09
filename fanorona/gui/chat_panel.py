"""Cartão de chat: histórico de mensagens + campo de envio.

Usamos um único `tk.Text` e "tags" (um recurso do Text do Tkinter para
estilizar trechos específicos): cada mensagem ganha uma tag com cor de
fundo e alinhamento próprios, dando um efeito parecido de balão de chat.
"""

import tkinter as tk
from typing import Callable, Optional

from . import theme


class ChatPanel(tk.Frame):
    def __init__(self, master: tk.Misc, on_send: Optional[Callable[[str], None]] = None) -> None:
        super().__init__(master, bg=theme.CARD_BG, highlightbackground=theme.CARD_BORDER,
                          highlightthickness=1, bd=0)
        self.on_send = on_send
        self._msg_counter = 0

        tk.Label(self, text="CHAT", font=theme.CARD_TITLE_FONT, fg=theme.TEXT_MUTED,
                 bg=theme.CARD_BG).pack(anchor="w", padx=16, pady=(14, 6))

        # A barra de digitar precisa ser empacotada (com side="bottom") ANTES da
        # área de histórico: no Tkinter, quem é empacotado primeiro reserva seu
        # espaço primeiro. Se a área de histórico (que usa expand=True) fosse
        # empacotada antes, ela tomaria todo o espaço vertical disponível e a
        # barra de digitar ficaria com altura zero — invisível, mas ainda "existindo".
        bottom = tk.Frame(self, bg=theme.CARD_BG)
        bottom.pack(side="bottom", fill="x", padx=16, pady=14)

        self.input_var = tk.StringVar()
        entry = tk.Entry(bottom, textvariable=self.input_var, font=theme.BODY_FONT, relief="solid", bd=1)
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        entry.bind("<Return>", lambda e: self._send())

        send_button = tk.Button(
            bottom, text="→", command=self._send, bg=theme.ACCENT, fg="white",
            activebackground=theme.ACCENT_DARK, activeforeground="white",
            relief="flat", bd=0, font=theme.BUTTON_FONT, width=3, cursor="hand2",
        )
        send_button.pack(side="right", padx=(6, 0))

        text_frame = tk.Frame(self, bg=theme.CARD_BG)
        text_frame.pack(fill="both", expand=True, padx=16)

        scrollbar = tk.Scrollbar(text_frame, orient="vertical")
        self.text = tk.Text(
            text_frame, bg=theme.CARD_BG, fg=theme.TEXT, bd=0, wrap="word", state="disabled",
            font=theme.BODY_FONT, spacing3=6, yscrollcommand=scrollbar.set, cursor="arrow",
        )
        scrollbar.configure(command=self.text.yview)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _send(self) -> None:
        text = self.input_var.get().strip()
        if text and self.on_send is not None:
            self.on_send(text)
            self.input_var.set("")

    def append_message(self, sender: str, message: str, own: bool) -> None:
        self.text.configure(state="normal")

        tag = f"bubble{self._msg_counter}"
        self._msg_counter += 1
        align = "right" if own else "left"
        bg = theme.ACCENT_SOFT if own else theme.SECONDARY_BG

        self.text.insert("end", f"{sender}\n", ("sender", f"{tag}_sender"))
        body_start = self.text.index("end-1c")
        self.text.insert("end", f"{message}\n\n")
        body_end = self.text.index("end-1c")

        self.text.tag_configure("sender", foreground=theme.TEXT_MUTED, font=theme.SMALL_FONT)
        self.text.tag_configure(f"{tag}_sender", justify=align)
        self.text.tag_add(tag, body_start, body_end)
        self.text.tag_configure(
            tag, background=bg, justify=align, lmargin1=8, lmargin2=8, rmargin=8, spacing1=2, spacing3=4,
        )

        self.text.configure(state="disabled")
        self.text.see("end")
