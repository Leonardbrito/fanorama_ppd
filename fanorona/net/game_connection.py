"""Envolve um socket já conectado (servidor/host ou cliente) e implementa
um protocolo de texto simples, uma mensagem por linha:

    HELLO nome                -> identificação inicial (troca de nomes, antes de start())
    MOVE fr fc tr tc CHOICE    -> jogada (CHOICE = NONE, APPROACH ou WITHDRAWAL)
    ENDTURN                    -> jogador encerrou voluntariamente a sequência de capturas
    RESIGN                     -> jogador desistiu da partida
    REMATCH                    -> jogador pediu revanche (reinicia a partida dos dois lados)
    CHAT texto...              -> mensagem de bate-papo (resto da linha)

CONCORRÊNCIA — duas threads por conexão, uma para cada sentido:

  * Thread de LEITURA (`_read_loop`): fica bloqueada em `readline()`
    esperando dados chegarem do socket. Como isso bloquearia a interface
    inteira se rodasse na thread principal, ela roda numa thread própria,
    criada em `start()`. Cada mensagem recebida vira um evento colocado
    numa `queue.Queue` (nunca é aplicado direto na tela dali).

  * Thread de ESCRITA (`_write_loop`): os métodos `send_*` NÃO escrevem
    no socket diretamente — eles só colocam a linha numa fila de saída
    (`_outgoing`) e retornam na hora. Quem realmente escreve no socket é
    essa thread separada, também criada em `start()`, que fica em loop
    tirando linhas da fila e mandando pela rede. Isso evita que a
    interface trave caso o envio demore (buffer do socket cheio, rede
    lenta etc.) e mantém envio e recepção completamente independentes
    um do outro.

Por que os eventos recebidos não atualizam a tela diretamente: o
Tkinter (como a maioria das bibliotecas gráficas) não é thread-safe —
só a thread principal pode mexer nos widgets. Por isso a thread de
leitura só empilha eventos numa `queue.Queue`; quem efetivamente aplica
cada evento na tela é a janela principal (veja `gui/main_app.py`),
retirando da fila periodicamente via `root.after(...)`, que sempre roda
na thread principal.

Cada evento colocado na fila de entrada é uma tupla começando com um nome:
    ("move", from_point, to_point, capture_type)
    ("endturn",)
    ("resign",)
    ("rematch",)
    ("chat", mensagem)
    ("disconnected", motivo)
"""

import queue
import socket
import threading
from typing import Optional

from ..model.capture_option import CaptureType
from ..model.point import Point

# Sentinela colocada na fila de saída para avisar a thread de escrita
# que ela deve parar (não pode ser confundida com uma mensagem real,
# já que todas as mensagens reais são strings).
_STOP = object()


def _sanitize(text: str) -> str:
    """Remove quebras de linha para não corromper o protocolo baseado em linhas."""
    return text.replace("\n", " ").replace("\r", " ")


class GameConnection:
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        # makefile com newline="\n" e um só espaço de nomes evita surpresas
        # de tradução de fim de linha entre plataformas.
        self._reader = sock.makefile("r", encoding="utf-8", newline="\n")
        self._writer = sock.makefile("w", encoding="utf-8", newline="\n")
        self._closed = False
        self._outgoing: "queue.Queue" = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._writer_thread: Optional[threading.Thread] = None

    def exchange_names(self, my_name: str) -> str:
        """Troca de identificação inicial: envia o próprio nome e bloqueia
        até receber o nome do adversário. É a única parte do protocolo
        feita de forma síncrona (faz sentido, já que é uma etapa única de
        "aperto de mão" antes da partida começar) — deve ser chamada antes
        de `start()`, na mesma thread que estabeleceu a conexão (fora da
        thread principal da interface).
        """
        self._writer.write(f"HELLO {_sanitize(my_name)}\n")
        self._writer.flush()
        line = self._reader.readline()
        if not line:
            raise ConnectionError("Conexão encerrada durante a identificação.")
        line = line.strip()
        if not line.startswith("HELLO "):
            raise ConnectionError("Protocolo inesperado durante a identificação.")
        peer_name = line[len("HELLO "):].strip()
        return peer_name or "Adversário"

    def start(self, event_queue: "queue.Queue") -> None:
        """Inicia as duas threads da conexão: uma só lê do socket, a
        outra só escreve — rodando em paralelo, sem uma bloquear a outra.
        """
        self._reader_thread = threading.Thread(
            target=self._read_loop, args=(event_queue,), daemon=True, name="fanorona-net-reader"
        )
        self._writer_thread = threading.Thread(
            target=self._write_loop, daemon=True, name="fanorona-net-writer"
        )
        self._reader_thread.start()
        self._writer_thread.start()

    def _read_loop(self, event_queue: "queue.Queue") -> None:
        try:
            for line in self._reader:
                self._dispatch(line, event_queue)
        except OSError:
            pass  # conexão caiu; tratado abaixo
        finally:
            if not self._closed:
                self._closed = True
                event_queue.put(("disconnected", "Conexão perdida com o adversário."))

    def _write_loop(self) -> None:
        while True:
            line = self._outgoing.get()  # bloqueia até ter algo para enviar
            if line is _STOP:
                return
            try:
                self._writer.write(line + "\n")
                self._writer.flush()
            except OSError:
                return  # conexão caiu; a thread de leitura já vai reportar

    def _dispatch(self, line: str, event_queue: "queue.Queue") -> None:
        trimmed = line.strip()
        if not trimmed:
            return

        if trimmed.startswith("MOVE "):
            parts = trimmed.split(" ")
            if len(parts) < 6:
                return
            try:
                fr, fc, tr, tc = (int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
                choice = CaptureType[parts[5]]
                event_queue.put(("move", Point(fr, fc), Point(tr, tc), choice))
            except (ValueError, KeyError):
                pass  # linha mal formada: ignora
        elif trimmed == "ENDTURN":
            event_queue.put(("endturn",))
        elif trimmed == "RESIGN":
            event_queue.put(("resign",))
        elif trimmed == "REMATCH":
            event_queue.put(("rematch",))
        elif trimmed.startswith("CHAT "):
            event_queue.put(("chat", trimmed[len("CHAT "):]))

    # -----------------------------------------------------------------
    # Envio: cada send_* apenas enfileira a linha; quem escreve de fato
    # no socket é a thread de escrita (_write_loop).
    # -----------------------------------------------------------------

    def send_move(self, frm: Point, to: Point, choice: Optional[CaptureType]) -> None:
        choice_name = "NONE" if choice is None else choice.name
        self._enqueue(f"MOVE {frm.row} {frm.col} {to.row} {to.col} {choice_name}")

    def send_end_turn(self) -> None:
        self._enqueue("ENDTURN")

    def send_resign(self) -> None:
        self._enqueue("RESIGN")

    def send_rematch(self) -> None:
        self._enqueue("REMATCH")

    def send_chat(self, message: str) -> None:
        self._enqueue(f"CHAT {_sanitize(message)}")

    def _enqueue(self, line: str) -> None:
        if not self._closed:
            self._outgoing.put(line)

    def close(self) -> None:
        self._closed = True
        self._outgoing.put(_STOP)  # acorda a thread de escrita para ela poder terminar
        try:
            # shutdown() age direto no socket do sistema operacional e por
            # isso consegue interromper na hora um recv()/readline() que
            # esteja bloqueado na thread de leitura; só chamar close() não
            # seria suficiente aqui, porque o socket ainda tem referências
            # abertas pelos objetos de arquivo criados via makefile().
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass
