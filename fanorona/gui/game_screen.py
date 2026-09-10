"""Tela principal exibida durante a partida. Liga três peças:
  - GameEngine: as regras do jogo (fonte da verdade local);
  - GameConnection: envia jogadas e chat pela rede (o recebimento é
    repassado pelo MainApp, que mantém a fila de eventos de rede viva
    entre partidas e chama os métodos apply_remote_* abaixo);
  - BoardCanvas / HistoryPanel / ChatPanel: a interface visual.

Fluxo de uma jogada local: clique -> valida no engine -> se válido,
aplica no tabuleiro local e ENVIA a jogada resolvida pela rede.
Fluxo de uma jogada remota: mensagem chega -> aplica no engine local da
MESMA forma (determinística) -> atualiza a tela. Assim os dois
tabuleiros permanecem sempre sincronizados.
"""

import time
import tkinter as tk
from typing import Callable, Optional

from . import dialogs, theme
from .board_canvas import BoardCanvas
from .chat_panel import ChatPanel
from .game_over_info import GameOverInfo
from .history_panel import HistoryPanel
from ..model.capture_option import CaptureType
from ..model.color import Color
from ..model.game_engine import GameEngine, ResultType
from ..model.point import Point
from ..net.game_connection import GameConnection


class GameScreen(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        engine: GameEngine,
        connection: GameConnection,
        my_color: Color,
        my_name: str,
        peer_name: str,
        on_game_over: Callable[[GameOverInfo], None],
    ) -> None:
        super().__init__(master, bg=theme.APP_BG)
        self.engine = engine
        self.connection = connection
        self.my_color = my_color
        self.my_name = my_name
        self.peer_name = peer_name
        self.on_game_over = on_game_over

        self.selected: Optional[Point] = None
        self.game_over_notified = False
        self.start_time = time.time()

        self.header_frame = self._build_header()
        self.chain_banner = self._build_chain_banner()

        body = tk.Frame(self, bg=theme.APP_BG)
        body.pack(fill="both", expand=True, padx=20, pady=(18, 20))

        center = tk.Frame(body, bg=theme.APP_BG)
        center.pack(side="left", fill="both", expand=True)

        board_card = theme.card(center, padx=16, pady=16)
        board_card.pack()
        self.board_canvas = BoardCanvas(board_card, on_point_clicked=self._handle_point_clicked)
        self.board_canvas.pack()
        self.board_canvas.set_engine(engine)

        sidebar = tk.Frame(body, bg=theme.APP_BG, width=260)
        sidebar.pack(side="right", fill="y", padx=(18, 0))
        sidebar.pack_propagate(False)

        self.history_panel = HistoryPanel(sidebar)
        self.history_panel.configure(height=170)
        self.history_panel.pack(fill="x")
        self.history_panel.pack_propagate(False)

        self.chat_panel = ChatPanel(sidebar, on_send=self._send_chat)
        self.chat_panel.pack(fill="both", expand=True, pady=(14, 0))

        self._refresh_status()

    def _build_header(self) -> tk.Frame:
        header = tk.Frame(self, bg=theme.CARD_BG)
        header.pack(fill="x")
        tk.Frame(header, bg=theme.CARD_BORDER, height=1).pack(side="bottom", fill="x")

        inner = tk.Frame(header, bg=theme.CARD_BG)
        inner.pack(fill="x", padx=22, pady=14)

        identity = tk.Frame(inner, bg=theme.CARD_BG)
        identity.pack(side="left")
        tk.Label(identity, text="FANORONA", font=theme.HEADER_FONT, fg=theme.TEXT, bg=theme.CARD_BG).pack(anchor="w")
        tk.Label(identity, text=f"Você é {self.my_name}", font=theme.SUBTITLE_FONT, fg=theme.TEXT_MUTED,
                 bg=theme.CARD_BG).pack(anchor="w")

        turn_frame = tk.Frame(inner, bg=theme.CARD_BG)
        turn_frame.pack(side="left", expand=True)
        self.turn_dot = tk.Label(turn_frame, text="●", fg=theme.PIECE_DARK, bg=theme.CARD_BG, font=("Helvetica", 11))
        self.turn_dot.pack(side="left")
        self.turn_label = tk.Label(turn_frame, text="", font=theme.BOLD_BODY_FONT, fg=theme.TEXT, bg=theme.CARD_BG)
        self.turn_label.pack(side="left", padx=(6, 0))

        theme.outline_button(inner, "Desistir", self._on_resign_button).pack(side="right")

        return header

    def _build_chain_banner(self) -> tk.Frame:
        banner = tk.Frame(self, bg=theme.ACCENT_SOFT)
        inner = tk.Frame(banner, bg=theme.ACCENT_SOFT)
        inner.pack(fill="x", padx=14, pady=8)
        tk.Label(inner, text="Continue capturando ou termine a jogada.", bg=theme.ACCENT_SOFT,
                 fg=theme.ACCENT_DARK, font=theme.SMALL_FONT).pack(side="left")
        theme.text_button(inner, "Terminar jogada", self._on_end_turn_button, bg=theme.ACCENT_SOFT).pack(side="right")
        return banner

    # -----------------------------------------------------------------
    # Interação local (mouse / botões)
    # -----------------------------------------------------------------

    def _handle_point_clicked(self, p: Point) -> None:
        if self.engine.game_over:
            return
        # [TOUR 1/10] Todo clique passa por aqui primeiro: se não é minha vez, nem processa.
        if self.engine.current_turn is not self.my_color:
            return  # não é sua vez

        occupant = self.engine.board.piece_at(p)

        if self.selected is None:
            if occupant is self.my_color and (not self.engine.is_mid_chain() or p == self.engine.active_piece):
                self._select(p)
            return

        if p == self.selected:
            if not self.engine.is_mid_chain():
                self._deselect()
            return

        legal = self.engine.legal_destinations(self.selected)
        if p in legal:
            self._attempt_move(self.selected, p)
            return

        if occupant is self.my_color and not self.engine.is_mid_chain():
            self._select(p)

    def _select(self, p: Point) -> None:
        self.selected = p
        self.board_canvas.set_selected(p)
        # [TOUR 2/10] Seleção é só local/visual: o model calcula os destinos possíveis
        # aqui embaixo — nada disso vai pra rede ainda.
        self.board_canvas.set_highlighted(self.engine.legal_destinations(p))

    def _deselect(self) -> None:
        self.selected = None
        self.board_canvas.set_selected(None)
        self.board_canvas.set_highlighted([])

    def _attempt_move(self, frm: Point, to: Point) -> None:
        # [TOUR 3/10] Aqui a jogada é validada e aplicada de verdade no meu tabuleiro local.
        result = self.engine.try_move(frm, to, None)

        if result.type == ResultType.NEEDS_CHOICE:
            approach = next((o for o in result.options if o.type == CaptureType.APPROACH), None)
            withdrawal = next((o for o in result.options if o.type == CaptureType.WITHDRAWAL), None)
            choice = dialogs.ask_capture_choice(self, approach, withdrawal)
            if choice is None:
                # usuário cancelou a escolha: mantém seleção atual, nada muda no engine
                return
            result = self.engine.try_move(frm, to, choice)

        self._apply_local_result(frm, to, result)

    # [TOUR 4/10] Em todo branch aceito abaixo, send_move() enfileira pra rede ANTES do
    # redraw() — meu tabuleiro já muda na tela antes de eu me preocupar com o outro lado.
    def _apply_local_result(self, frm: Point, to: Point, result) -> None:
        if result.type == ResultType.INVALID:
            self.bell()
            return

        if result.type == ResultType.SIMPLE_MOVE_TURN_ENDED:
            self.connection.send_move(frm, to, CaptureType.NONE)
            self.board_canvas.set_last_move(frm, to)
            self._log_move(self.my_name, frm, to, len(result.captured or []))
            self._deselect()
        elif result.type == ResultType.CAPTURE_CHAIN_CONTINUES:
            self.connection.send_move(frm, to, result.applied_choice)
            self.board_canvas.set_last_move(frm, to)
            self._log_move(self.my_name, frm, to, len(result.captured or []))
            self._select(self.engine.active_piece)
        elif result.type == ResultType.CAPTURE_CHAIN_ENDED:
            self.connection.send_move(frm, to, result.applied_choice)
            self.board_canvas.set_last_move(frm, to)
            self._log_move(self.my_name, frm, to, len(result.captured or []))
            self._deselect()

        self.board_canvas.redraw()
        self._refresh_status()
        self._check_game_over()

    def _on_end_turn_button(self) -> None:
        if self.engine.game_over:
            return
        if self.engine.current_turn is self.my_color and self.engine.is_mid_chain():
            self.engine.end_chain_voluntarily()
            self.connection.send_end_turn()
            self._deselect()
            self.board_canvas.redraw()
            self._refresh_status()

    def _on_resign_button(self) -> None:
        if self.engine.game_over:
            return
        if dialogs.confirm_resign(self, self.peer_name):
            self._do_resign()

    def _do_resign(self) -> None:
        self.engine.resign(self.my_color)
        self.connection.send_resign()
        self._deselect()
        self.board_canvas.redraw()
        self._refresh_status()
        self._check_game_over()

    # -----------------------------------------------------------------
    # Estado / status
    # -----------------------------------------------------------------

    def _refresh_status(self) -> None:
        turn = self.engine.current_turn
        name = self.my_name if turn is self.my_color else self.peer_name
        self.turn_label.configure(text=f"Vez de {name}")
        self.turn_dot.configure(fg=theme.PIECE_DARK if turn is Color.WHITE else theme.PIECE_GOLD)

        show_chain = (
            not self.engine.game_over and self.engine.current_turn is self.my_color and self.engine.is_mid_chain()
        )
        if show_chain:
            self.chain_banner.pack(fill="x", after=self.header_frame)
        else:
            self.chain_banner.pack_forget()

    def _check_game_over(self) -> None:
        if not self.engine.game_over or self.game_over_notified:
            return
        self.game_over_notified = True

        winner = self.engine.winner
        winner_name = self.my_name if winner is self.my_color else self.peer_name
        loser_name = self.peer_name if winner is self.my_color else self.my_name

        reason = self.engine.game_over_reason
        if reason == "Desistência":
            reason_text = f"{loser_name} desistiu da partida."
        elif reason == "Sem jogadas possíveis":
            reason_text = f"{loser_name} não possui mais jogadas possíveis."
        else:
            reason_text = "Vitória por captura de todas as peças adversárias."

        info = GameOverInfo(
            winner_name=winner_name,
            reason_text=reason_text,
            winner_pieces_remaining=self.engine.board.count_pieces(winner),
            duration_seconds=time.time() - self.start_time,
        )
        self.on_game_over(info)

    def _notate(self, p: Point) -> str:
        col_letter = chr(ord("A") + p.col)
        row_number = p.row + 1
        return f"{col_letter}{row_number}"

    def _log_move(self, mover_name: str, frm: Point, to: Point, captured_count: int) -> None:
        self.history_panel.add_entry(mover_name, self._notate(frm), self._notate(to), captured_count)

    def _send_chat(self, text: str) -> None:
        self.connection.send_chat(text)
        self.chat_panel.append_message(self.my_name, text, True)

    # -----------------------------------------------------------------
    # Eventos recebidos pela rede (repassados pelo MainApp)
    # -----------------------------------------------------------------

    # [TOUR 10/10] Chegada pela rede: mesmíssimo try_move, agora reprocessando a jogada
    # que já foi decidida do outro lado — não é sincronizar estado, é replicar a decisão.
    def apply_remote_move(self, frm: Point, to: Point, choice: CaptureType) -> None:
        effective = None if choice == CaptureType.NONE else choice
        result = self.engine.try_move(frm, to, effective)
        self.board_canvas.set_last_move(frm, to)
        self._log_move(self.peer_name, frm, to, len(result.captured or []))
        self.board_canvas.redraw()
        self._refresh_status()
        self._check_game_over()

    def apply_remote_end_turn(self) -> None:
        self.engine.end_chain_voluntarily()
        self._deselect()
        self.board_canvas.redraw()
        self._refresh_status()

    def apply_remote_chat(self, message: str) -> None:
        self.chat_panel.append_message(self.peer_name, message, False)

    def apply_remote_resign(self) -> None:
        self.engine.resign(self.my_color.opposite())
        self.board_canvas.redraw()
        self._refresh_status()
        self._check_game_over()
