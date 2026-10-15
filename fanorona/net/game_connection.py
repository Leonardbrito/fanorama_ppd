"""Comunicação entre os dois tabuleiros usando RPC (XML-RPC, biblioteca
padrão `xmlrpc` do Python). Não há sockets nem protocolo de texto escrito
à mão: cada tabuleiro é, ao mesmo tempo, SERVIDOR e CLIENTE.

  * Como SERVIDOR, expõe os métodos da classe `_GameService` (register,
    move, end_turn, resign, rematch, chat, ping, bye). É o adversário quem
    chama esses métodos, e a execução acontece AQUI.
  * Como CLIENTE, mantém um `ServerProxy` (o "stub" do RMI) que representa
    o servidor do adversário. Escrever `proxy.move(1, 2, 2, 3, "NONE")` faz
    a biblioteca montar o XML, mandar por HTTP, executar `move` na outra
    máquina e devolver a resposta.

    Jogador A                               Jogador B
    [servidor RPC: move, chat, ...]  <----  [proxy de A]
    [proxy de B]  ---------------------->   [servidor RPC: move, chat, ...]

Correspondência com as antigas mensagens de texto:

    HELLO nome      ->  register(porta, nome)
    MOVE fr fc ...  ->  move(fr, fc, tr, tc, choice)   (choice = NONE, APPROACH ou WITHDRAWAL)
    ENDTURN         ->  end_turn()
    RESIGN          ->  resign()
    REMATCH         ->  rematch()
    CHAT texto      ->  chat(texto)
    (novo)          ->  ping()  /  bye()

CONCORRÊNCIA:

  * Servidor (`_ThreadedXMLRPCServer`): roda numa thread própria
    (`serve_forever`) e atende cada chamada recebida em mais uma thread.
    Cada método exposto só coloca um evento numa `queue.Queue` e retorna.
    Os eventos NÃO mexem na tela direto: o Tkinter não é thread-safe, então
    quem aplica os eventos é a janela principal (`gui/main_app.py`),
    esvaziando a fila via `root.after(...)` na thread principal.

  * Cliente (`_write_loop`): chamar um método remoto bloqueia até a
    resposta chegar. Por isso os métodos `send_*` NÃO chamam o adversário
    diretamente: só enfileiram a chamada em `_outgoing` e retornam. Uma
    única thread de escrita tira da fila e faz as chamadas RPC uma a uma,
    o que também garante que as jogadas cheguem NA ORDEM.

  * Detecção de queda: RPC não mantém conexão aberta. Quando a fila de saída
    fica parada por `PING_INTERVAL_S` segundos, a thread de escrita chama
    `ping()` no adversário; se qualquer chamada falhar, vira o evento
    "disconnected". Ao sair da partida normalmente, `close()` avisa com `bye()`.

Cada evento colocado na fila de entrada é uma tupla começando com um nome:
    ("move", from_point, to_point, capture_type)
    ("endturn",)
    ("resign",)
    ("rematch",)
    ("chat", mensagem)
    ("disconnected", motivo)
"""

import http.client
import queue
import socketserver
import threading
import xmlrpc.client
from typing import Optional
from xmlrpc.server import SimpleXMLRPCServer

from ..model.capture_option import CaptureType
from ..model.point import Point

PING_INTERVAL_S = 3     # sem nada a enviar por este tempo -> chama ping() no adversário
CALL_TIMEOUT_S = 10     # tempo máximo esperando a resposta de uma chamada remota

# Erros que uma chamada remota pode levantar (rede fora do ar, HTTP/XML-RPC inválido, Fault...).
RPC_ERRORS = (OSError, xmlrpc.client.Error, http.client.HTTPException)

# Sentinela colocada na fila de saída para avisar a thread de escrita
# que ela deve parar (não pode ser confundida com uma chamada real,
# já que todas as chamadas reais são tuplas).
_STOP = object()

# Guarda o IP de quem está fazendo a chamada atual (uma thread por requisição).
_request_ctx = threading.local()


class _TimeoutTransport(xmlrpc.client.Transport):
    """Transporte HTTP do ServerProxy com timeout (o padrão espera para sempre)."""

    def __init__(self, timeout: float) -> None:
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


class _ThreadedXMLRPCServer(socketserver.ThreadingMixIn, SimpleXMLRPCServer):
    """Servidor XML-RPC que atende cada requisição em uma thread."""

    daemon_threads = True

    def finish_request(self, request, client_address):
        # Roda na thread da requisição: guarda o IP do chamador para o
        # `register` descobrir como chamar de volta (sem ele precisar informar).
        _request_ctx.client_ip = client_address[0]
        super().finish_request(request, client_address)


class _GameService:
    """Métodos que o ADVERSÁRIO pode chamar em mim (a parte "servidor").

    Só métodos públicos são expostos pelo xmlrpc (nomes com `_` ficam
    privados). Cada um converte a chamada em um evento da fila.
    """

    def __init__(self, conn: "GameConnection") -> None:
        self._conn = conn

    def register(self, port: int, name: str) -> str:
        """Apresentação inicial: quem entra informa a porta do próprio servidor
        e o nome; recebe de volta o nome de quem hospeda."""
        return self._conn._on_register(_request_ctx.client_ip, int(port), str(name))

    def move(self, fr: int, fc: int, tr: int, tc: int, choice: str) -> bool:
        self._conn._emit(("move", Point(int(fr), int(fc)), Point(int(tr), int(tc)), CaptureType[choice]))
        return True

    def end_turn(self) -> bool:
        self._conn._emit(("endturn",))
        return True

    def resign(self) -> bool:
        self._conn._emit(("resign",))
        return True

    def rematch(self) -> bool:
        self._conn._emit(("rematch",))
        return True

    def chat(self, message: str) -> bool:
        self._conn._emit(("chat", str(message)))
        return True

    def ping(self) -> bool:
        return True

    def bye(self) -> bool:
        self._conn._on_peer_left()
        return True


class GameConnection:
    def __init__(self, my_name: str) -> None:
        self.my_name = my_name
        self.peer_name = ""
        self._peer: Optional[xmlrpc.client.ServerProxy] = None  # proxy para o servidor do adversário
        self._server: Optional[_ThreadedXMLRPCServer] = None
        self._server_lock = threading.Lock()

        self._peer_ready = threading.Event()  # host: alguém chamou register (ou foi cancelado)
        self._cancelled = False
        self._closed = False
        self._peer_gone = False  # o adversário já avisou que saiu (bye)

        self._event_queue: Optional["queue.Queue"] = None
        self._pending: list = []  # eventos que chegaram antes de start()
        self._events_lock = threading.Lock()

        self._outgoing: "queue.Queue" = queue.Queue()
        self._writer_thread: Optional[threading.Thread] = None

    # -----------------------------------------------------------------
    # Estabelecer a conexão (usado por NetworkSetup)
    # -----------------------------------------------------------------

    def listen(self, port: int) -> None:
        """Sobe o servidor RPC desta máquina (porta 0 = o sistema escolhe uma livre)."""
        server = _ThreadedXMLRPCServer(("", port), logRequests=False, allow_none=True)
        server.register_instance(_GameService(self))
        self._server = server
        threading.Thread(target=server.serve_forever, daemon=True, name="fanorona-rpc-server").start()

    @property
    def listen_port(self) -> int:
        return self._server.server_address[1]

    def wait_for_peer(self) -> Optional[str]:
        """Host: bloqueia até o adversário chamar `register`. Devolve o nome
        dele, ou None se a espera foi cancelada."""
        self._peer_ready.wait()
        return None if self._cancelled else self.peer_name

    def connect_to(self, host: str, port: int) -> str:
        """Quem entra: cria o proxy para o servidor do host e chama `register`,
        informando a porta do próprio servidor para o host poder chamar de volta.
        Devolve o nome do host."""
        self._peer = self._make_proxy(host, port)
        self.peer_name = self._peer.register(self.listen_port, self.my_name) or "Adversário"
        return self.peer_name

    def cancel(self) -> None:
        """Host: desiste de esperar o adversário."""
        self._cancelled = True
        self._peer_ready.set()
        self._shutdown_server()

    @staticmethod
    def _make_proxy(host: str, port: int) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(
            f"http://{host}:{port}", transport=_TimeoutTransport(CALL_TIMEOUT_S), allow_none=True
        )

    def _on_register(self, client_ip: str, port: int, name: str) -> str:
        """Executado quando o adversário chama `register` aqui (lado do host)."""
        if self._peer is not None or self._cancelled:
            raise RuntimeError("Esta partida já tem dois jogadores.")
        self._peer = self._make_proxy(client_ip, port)
        self.peer_name = name.strip() or "Adversário"
        self._peer_ready.set()
        return self.my_name

    # -----------------------------------------------------------------
    # Partida em andamento
    # -----------------------------------------------------------------

    def start(self, event_queue: "queue.Queue") -> None:
        """Passa a entregar os eventos recebidos em `event_queue` e inicia a
        thread de escrita (a que faz as chamadas RPC para o adversário)."""
        with self._events_lock:
            self._event_queue = event_queue
            for event in self._pending:
                event_queue.put(event)
            self._pending.clear()
        self._writer_thread = threading.Thread(target=self._write_loop, daemon=True, name="fanorona-rpc-writer")
        self._writer_thread.start()

    def _emit(self, event: tuple) -> None:
        with self._events_lock:
            if self._event_queue is None:
                self._pending.append(event)
            else:
                self._event_queue.put(event)

    def _on_peer_left(self) -> None:
        """O adversário chamou `bye` (saiu da partida de propósito)."""
        self._peer_gone = True
        self._report_disconnected()
        self._outgoing.put(_STOP)

    def _report_disconnected(self) -> None:
        if not self._closed:
            self._closed = True
            self._emit(("disconnected", "Conexão perdida com o adversário."))

    def _write_loop(self) -> None:
        try:
            while True:
                try:
                    call = self._outgoing.get(timeout=PING_INTERVAL_S)
                except queue.Empty:
                    call = ("ping",)  # fila parada: confere se o adversário continua lá
                if call is _STOP:
                    self._say_goodbye()
                    return
                method, *args = call
                try:
                    # Chamada remota: `self._peer.move(...)` executa `move` no adversário.
                    getattr(self._peer, method)(*args)
                except RPC_ERRORS:
                    self._report_disconnected()
                    return
        finally:
            self._shutdown_server()

    def _say_goodbye(self) -> None:
        if self._peer is None or self._peer_gone:
            return
        try:
            self._peer.bye()
        except RPC_ERRORS:
            pass  # o adversário já saiu ou caiu; nada a fazer

    # -----------------------------------------------------------------
    # Envio: cada send_* apenas enfileira a chamada; quem faz a chamada RPC
    # de fato é a thread de escrita (_write_loop).
    # -----------------------------------------------------------------

    def send_move(self, frm: Point, to: Point, choice: Optional[CaptureType]) -> None:
        choice_name = "NONE" if choice is None else choice.name
        self._enqueue(("move", frm.row, frm.col, to.row, to.col, choice_name))

    def send_end_turn(self) -> None:
        self._enqueue(("end_turn",))

    def send_resign(self) -> None:
        self._enqueue(("resign",))

    def send_rematch(self) -> None:
        self._enqueue(("rematch",))

    def send_chat(self, message: str) -> None:
        self._enqueue(("chat", message))

    def _enqueue(self, call: tuple) -> None:
        if not self._closed:
            self._outgoing.put(call)

    def close(self) -> None:
        self._closed = True
        self._outgoing.put(_STOP)  # a thread de escrita avisa com bye() e encerra o servidor
        if self._writer_thread is None:  # start() nunca foi chamado: ninguém mais vai encerrar o servidor
            self._shutdown_server()

    def _shutdown_server(self) -> None:
        with self._server_lock:
            server, self._server = self._server, None
        if server is not None:
            server.shutdown()      # para o serve_forever
            server.server_close()  # libera a porta
