"""Funções para estabelecer a conexão TCP entre os dois tabuleiros, seja
hospedando uma partida (abrindo um socket servidor e aguardando um
adversário se conectar) ou entrando em uma partida já hospedada por
outra pessoa (conectando a um IP e porta). Logo após a conexão TCP,
troca os nomes dos jogadores antes de chamar `on_connected`.

`accept()`/`connect()` também são operações bloqueantes, então cada uma
roda na sua própria thread (uma thread por chamada a `host`/`join`);
`on_connected`/`on_error` são chamados NESSA thread (não na thread da
interface) — quem chama este módulo é responsável por repassar o
resultado para a thread principal (por exemplo, com
`widget.after(0, ...)`), já que o Tkinter só pode ser mexido pela
thread principal.
"""

import socket
import threading
from typing import Callable, Optional

from .game_connection import GameConnection

OnConnected = Callable[[GameConnection, str], None]
OnError = Callable[[str], None]


class NetworkSetup:
    _active_server_socket: Optional[socket.socket] = None

    @staticmethod
    def host(port: int, my_name: str, on_connected: OnConnected, on_error: OnError) -> None:
        """Hospeda uma partida: abre a porta e espera um oponente conectar."""

        def run() -> None:
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("", port))
                server.listen(1)
                NetworkSetup._active_server_socket = server
                client_sock, _ = server.accept()  # bloqueia até alguém conectar
                conn = GameConnection(client_sock)
                peer_name = conn.exchange_names(my_name)
                on_connected(conn, peer_name)
            except OSError as e:
                on_error(f"Não foi possível hospedar na porta {port}: {e}")

        threading.Thread(target=run, daemon=True, name="fanorona-host-thread").start()

    @staticmethod
    def cancel_hosting() -> None:
        """Cancela a espera por conexão (usado se o usuário desistir de hospedar)."""
        if NetworkSetup._active_server_socket is not None:
            try:
                NetworkSetup._active_server_socket.close()
            except OSError:
                pass

    @staticmethod
    def join(host: str, port: int, my_name: str, on_connected: OnConnected, on_error: OnError) -> None:
        """Entra em uma partida hospedada em host:port."""

        def run() -> None:
            try:
                sock = socket.create_connection((host, port), timeout=10)
                sock.settimeout(None)  # volta ao modo bloqueante normal após conectar
                conn = GameConnection(sock)
                peer_name = conn.exchange_names(my_name)
                on_connected(conn, peer_name)
            except OSError as e:
                on_error(f"Não foi possível conectar a {host}:{port}: {e}")

        threading.Thread(target=run, daemon=True, name="fanorona-join-thread").start()
