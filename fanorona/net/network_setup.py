"""Funções para estabelecer a conexão RPC entre os dois tabuleiros, seja
hospedando uma partida (subindo o servidor RPC e aguardando o adversário
se registrar) ou entrando em uma partida já hospedada por outra pessoa
(chamando `register` no servidor dele pelo IP e porta).

  * host: sobe o servidor RPC na porta escolhida e espera alguém chamar
    `register`. Dentro de `register` o host descobre o IP de quem chamou
    e cria o proxy de volta.
  * join: sobe o PRÓPRIO servidor RPC (numa porta livre escolhida pelo
    sistema) e chama `register` no host, informando essa porta. A partir
    daí os dois lados conseguem chamar um ao outro.

Esperar o adversário e chamar `register` são operações bloqueantes, então
cada uma roda na sua própria thread (uma thread por chamada a `host`/`join`);
`on_connected`/`on_error` são chamados NESSA thread (não na thread da
interface) — quem chama este módulo é responsável por repassar o
resultado para a thread principal (por exemplo, com
`widget.after(0, ...)`), já que o Tkinter só pode ser mexido pela
thread principal.
"""

import threading
from typing import Callable, Optional

from .game_connection import RPC_ERRORS, GameConnection

OnConnected = Callable[[GameConnection, str], None]
OnError = Callable[[str], None]


class NetworkSetup:
    _hosting: Optional[GameConnection] = None

    @staticmethod
    def host(port: int, my_name: str, on_connected: OnConnected, on_error: OnError) -> None:
        """Hospeda uma partida: sobe o servidor RPC e espera um oponente se registrar."""

        def run() -> None:
            conn = GameConnection(my_name)
            try:
                conn.listen(port)
                NetworkSetup._hosting = conn
                peer_name = conn.wait_for_peer()  # bloqueia até alguém chamar register()
                if peer_name is None:
                    return  # cancelado pelo usuário
                NetworkSetup._hosting = None
                on_connected(conn, peer_name)
            except OSError as e:
                NetworkSetup._hosting = None
                on_error(f"Não foi possível hospedar na porta {port}: {e}")

        threading.Thread(target=run, daemon=True, name="fanorona-host-thread").start()

    @staticmethod
    def cancel_hosting() -> None:
        """Cancela a espera por conexão (usado se o usuário desistir de hospedar)."""
        conn, NetworkSetup._hosting = NetworkSetup._hosting, None
        if conn is not None:
            conn.cancel()

    @staticmethod
    def join(host: str, port: int, my_name: str, on_connected: OnConnected, on_error: OnError) -> None:
        """Entra em uma partida hospedada em host:port."""

        def run() -> None:
            conn = GameConnection(my_name)
            try:
                conn.listen(0)  # meu servidor, em qualquer porta livre
                peer_name = conn.connect_to(host, port)  # RPC: host.register(minha_porta, meu_nome)
                on_connected(conn, peer_name)
            except RPC_ERRORS as e:
                conn.close()
                on_error(f"Não foi possível conectar a {host}:{port}: {e}")

        threading.Thread(target=run, daemon=True, name="fanorona-join-thread").start()
