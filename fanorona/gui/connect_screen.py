"""Tela inicial: hospedar uma partida (aguardando conexão de um
adversário) ou entrar numa partida hospedada em outra máquina.

Quem hospeda sempre joga com as peças Brancas (começa a partida); quem
entra joga com as Pretas.
"""

import tkinter as tk
from typing import Callable

from . import theme
from ..model.color import Color
from ..net.network_setup import NetworkSetup

# Assinatura do callback chamado quando a conexão é estabelecida:
#   on_connected(connection, my_color, my_name, peer_name)
OnConnected = Callable


class ConnectScreen(tk.Frame):
    def __init__(self, master: tk.Misc, on_connected: OnConnected) -> None:
        super().__init__(master, bg=theme.APP_BG)
        self.on_connected = on_connected
        self.mode = "HOST"

        card = theme.card(self, padx=32, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="FANORONA", font=theme.TITLE_FONT, fg=theme.TEXT, bg=theme.CARD_BG).pack(pady=(0, 4))
        theme.muted_label(card, "Conecte-se para iniciar a partida", bg=theme.CARD_BG).pack(pady=(0, 20))

        tabs = tk.Frame(card, bg=theme.CARD_BG)
        tabs.pack(fill="x", pady=(0, 18))
        self.host_tab = tk.Button(tabs, text="Hospedar partida", command=lambda: self._set_mode("HOST"),
                                   relief="flat", bd=0, padx=10, pady=8, font=theme.BUTTON_FONT, cursor="hand2")
        self.join_tab = tk.Button(tabs, text="Entrar em partida", command=lambda: self._set_mode("JOIN"),
                                   relief="flat", bd=0, padx=10, pady=8, font=theme.BUTTON_FONT, cursor="hand2")
        self.host_tab.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.join_tab.pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.name_var = tk.StringVar(value="Leo")
        self._field(card, "Seu nome", self.name_var)

        self.ip_var = tk.StringVar(value="localhost")
        self.ip_row = self._field(card, "Endereço IP", self.ip_var)

        self.port_var = tk.StringVar(value="5000")
        self.port_row = self._field(card, "Porta", self.port_var)

        self.connect_button = theme.primary_button(card, "Conectar", self._do_connect)
        self.connect_button.pack(fill="x", pady=(10, 10))

        self.status_var = tk.StringVar(value=" ")
        self.status_label = tk.Label(
            card, textvariable=self.status_var, fg=theme.TEXT_MUTED, bg=theme.CARD_BG,
            font=theme.SMALL_FONT, wraplength=280, justify="center",
        )
        self.status_label.pack()

        self.cancel_button = theme.text_button(card, "Cancelar", self._do_cancel, bg=theme.CARD_BG)

        self._set_mode("HOST")

    def _field(self, parent: tk.Widget, label_text: str, var: tk.StringVar) -> tk.Frame:
        row = tk.Frame(parent, bg=theme.CARD_BG)
        row.pack(fill="x", pady=(0, 12))
        tk.Label(row, text=label_text, fg=theme.TEXT_MUTED, bg=theme.CARD_BG, font=theme.LABEL_FONT).pack(anchor="w")
        entry = tk.Entry(row, textvariable=var, font=theme.BODY_FONT, relief="solid", bd=1, highlightthickness=0)
        entry.pack(fill="x", pady=(4, 0), ipady=4)
        return row

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        if mode == "HOST":
            self.host_tab.configure(bg=theme.ACCENT, fg="white", activebackground=theme.ACCENT_DARK)
            self.join_tab.configure(bg=theme.SECONDARY_BG, fg=theme.TEXT, activebackground=theme.CARD_BORDER)
            self.ip_row.pack_forget()
        else:
            self.join_tab.configure(bg=theme.ACCENT, fg="white", activebackground=theme.ACCENT_DARK)
            self.host_tab.configure(bg=theme.SECONDARY_BG, fg=theme.TEXT, activebackground=theme.CARD_BORDER)
            self.ip_row.pack(fill="x", pady=(0, 12), before=self.port_row)
        self.status_var.set(" ")

    def _do_connect(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            self.status_var.set("Informe seu nome.")
            return
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            self.status_var.set("Porta inválida.")
            return

        if self.mode == "HOST":
            self._set_busy(True, "Aguardando outro jogador para iniciar…")

            def on_connected(conn, peer_name):
                # chamado na thread de rede: repassa para a thread principal do Tk
                self.after(0, lambda: self._finish(conn, Color.WHITE, name, peer_name))

            def on_error(message):
                self.after(0, lambda: self._set_busy(False, message))

            NetworkSetup.host(port, name, on_connected, on_error)
        else:
            host = self.ip_var.get().strip()
            if not host:
                self.status_var.set("Informe o endereço IP.")
                return
            self._set_busy(True, f"Conectando a {host}:{port}…")

            def on_connected(conn, peer_name):
                self.after(0, lambda: self._finish(conn, Color.BLACK, name, peer_name))

            def on_error(message):
                self.after(0, lambda: self._set_busy(False, message))

            NetworkSetup.join(host, port, name, on_connected, on_error)

    def _finish(self, connection, color, name, peer_name) -> None:
        self._set_busy(False, " ")
        self.on_connected(connection, color, name, peer_name)

    def _do_cancel(self) -> None:
        NetworkSetup.cancel_hosting()
        self._set_busy(False, "Cancelado.")

    def _set_busy(self, busy: bool, status: str) -> None:
        state = "disabled" if busy else "normal"
        self.connect_button.configure(state=state)
        self.host_tab.configure(state=state)
        self.join_tab.configure(state=state)
        self.status_var.set(status)
        if busy and self.mode == "HOST":
            self.cancel_button.pack(pady=(4, 0))
        else:
            self.cancel_button.pack_forget()
