"""Controla a janela principal: troca entre as telas de conexão, jogo e
fim de jogo, e mantém a fila de eventos de rede sendo lida
continuamente, repassando cada evento para a tela de jogo ativa.
"""

import queue
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from . import theme
from .connect_screen import ConnectScreen
from .game_over_screen import GameOverScreen
from .game_screen import GameScreen
from ..model.color import Color
from ..model.game_engine import GameEngine
from ..net.game_connection import GameConnection

POLL_INTERVAL_MS = 50  # frequência com que a fila de eventos de rede é verificada


class MainApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Fanorona — RMI/RPC")
        self.root.configure(bg=theme.APP_BG)
        self.root.resizable(False, False)

        self.connection: Optional[GameConnection] = None
        self.my_color: Optional[Color] = None
        self.my_name: str = ""
        self.peer_name: str = ""

        self.event_queue: "queue.Queue" = queue.Queue()
        self.active_game_screen: Optional[GameScreen] = None
        self.current_frame: Optional[tk.Frame] = None

        self._show_connect_screen()
        self.root.after(POLL_INTERVAL_MS, self._poll_events)

    # -----------------------------------------------------------------
    # Navegação entre telas
    # -----------------------------------------------------------------

    def _show_connect_screen(self) -> None:
        self._swap(ConnectScreen(self.root, on_connected=self._start_game), 420, 560)

    def _start_game(self, connection: GameConnection, my_color: Color, my_name: str, peer_name: str) -> None:
        self.connection = connection
        self.my_color = my_color
        self.my_name = my_name
        self.peer_name = peer_name
        connection.start(self.event_queue)
        self._launch_new_game()

    def _launch_new_game(self) -> None:
        engine = GameEngine()
        screen = GameScreen(
            self.root, engine, self.connection, self.my_color, self.my_name, self.peer_name,
            on_game_over=self._show_game_over,
        )
        self.active_game_screen = screen
        self._swap(screen, 980, 640)

    def _show_game_over(self, info) -> None:
        self.active_game_screen = None
        screen = GameOverScreen(self.root, info, on_exit=self._exit_to_connect, on_rematch=self._rematch)
        self._swap(screen, 440, 520)

    def _rematch(self) -> None:
        self.connection.send_rematch()
        self._launch_new_game()

    def _exit_to_connect(self) -> None:
        self.active_game_screen = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self._show_connect_screen()

    def _swap(self, new_frame: tk.Frame, width: int, height: int) -> None:
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = new_frame
        self.root.geometry(f"{width}x{height}")
        new_frame.pack(fill="both", expand=True)

    # -----------------------------------------------------------------
    # Fila de eventos de rede: repassa cada evento para a tela de jogo ativa
    # -----------------------------------------------------------------

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.root.after(POLL_INTERVAL_MS, self._poll_events)

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]

        if kind == "move" and self.active_game_screen is not None:
            _, frm, to, choice = event
            self.active_game_screen.apply_remote_move(frm, to, choice)
        elif kind == "endturn" and self.active_game_screen is not None:
            self.active_game_screen.apply_remote_end_turn()
        elif kind == "chat" and self.active_game_screen is not None:
            self.active_game_screen.apply_remote_chat(event[1])
        elif kind == "resign" and self.active_game_screen is not None:
            self.active_game_screen.apply_remote_resign()
        elif kind == "rematch":
            self._launch_new_game()
        elif kind == "disconnected":
            self.active_game_screen = None
            if self.connection is not None:
                self.connection.close()  # libera o servidor RPC (e a porta) antes de poder hospedar de novo
                self.connection = None
            messagebox.showwarning("Conexão perdida", event[1])
            self._show_connect_screen()
