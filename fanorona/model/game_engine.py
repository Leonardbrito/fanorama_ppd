"""Motor de regras do Fanorona. Controla o tabuleiro, de quem é a vez, a
sequência de capturas de um mesmo turno (chain captures) e a detecção
de fim de jogo.

Esta classe é usada de forma idêntica nos dois lados da conexão (quem
está jogando localmente E quem recebe a jogada pela rede), garantindo
que os dois tabuleiros fiquem sempre sincronizados: cada jogada é
aplicada da mesma forma determinística nos dois lados.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Set

from . import direction as directions
from .board import Board, COLS, ROWS
from .capture_option import CaptureOption, CaptureType
from .color import Color
from .point import Point


class ResultType(Enum):
    INVALID = auto()  # jogada não permitida
    NEEDS_CHOICE = auto()  # há 2 formas de captura possíveis; a GUI deve perguntar ao usuário
    SIMPLE_MOVE_TURN_ENDED = auto()  # movimento simples (sem captura), turno passou
    CAPTURE_CHAIN_CONTINUES = auto()  # capturou e pode continuar a sequência (ou parar, se quiser)
    CAPTURE_CHAIN_ENDED = auto()  # capturou e não há mais continuação possível; turno passou


@dataclass
class Result:
    """Resultado de uma tentativa de jogada."""

    type: ResultType
    options: Optional[List[CaptureOption]] = None  # preenchido apenas quando type == NEEDS_CHOICE
    captured: Optional[List[Point]] = None  # peças capturadas nesta jogada (se houver)
    applied_choice: CaptureType = CaptureType.NONE  # tipo de captura efetivamente aplicado (ou NONE)


class GameEngine:
    def __init__(self, board: Optional[Board] = None, turn_to_play: Color = Color.WHITE) -> None:
        self.board: Board = board if board is not None else Board()
        # Quem hospeda (host) sempre começa jogando de Brancas.
        self.current_turn: Color = turn_to_play
        self.active_piece: Optional[Point] = None  # peça em meio a uma sequência de capturas (ou None)
        self.last_direction = None
        self.visited_this_turn: Set[Point] = set()

        self.game_over: bool = False
        self.winner: Optional[Color] = None
        self.game_over_reason: str = ""

    def is_mid_chain(self) -> bool:
        return self.active_piece is not None

    # -----------------------------------------------------------------
    # Consulta de jogadas legais (usado pela interface gráfica)
    # -----------------------------------------------------------------

    def legal_destinations(self, frm: Point) -> List[Point]:
        """Retorna os destinos possíveis a partir de um ponto, considerando
        se é o primeiro movimento do turno (qualquer casa vazia ligada
        serve) ou uma continuação de captura (só vale se resultar em
        nova captura, sem repetir casa nem repetir a última direção).
        """
        result: List[Point] = []
        if self.game_over:
            return result
        if self.board.piece_at(frm) is not self.current_turn:
            return result
        if self.is_mid_chain() and frm != self.active_piece:
            return result

        for d in self.board.valid_directions_from(frm):
            to = frm.plus(d)
            if not self.board.is_empty(to):
                continue
            if to in self.visited_this_turn:
                continue
            if self.is_mid_chain() and d == self.last_direction:
                continue

            if not self.is_mid_chain():
                # primeira jogada do turno: qualquer casa vazia vale
                result.append(to)
            else:
                # continuação: só vale se capturar algo
                if self._compute_capture_options(frm, to, d):
                    result.append(to)
        return result

    # -----------------------------------------------------------------
    # Execução de jogadas
    # -----------------------------------------------------------------

    def try_move(self, frm: Point, to: Point, choice: Optional[CaptureType]) -> Result:
        """Tenta mover a peça de `frm` para `to`. Se houver ambiguidade
        entre captura por aproximação e por afastamento, `choice` deve
        ser informado (não-None); caso contrário, se houver ambiguidade
        e choice for None, o método retorna NEEDS_CHOICE sem alterar o
        estado do jogo, e deve ser chamado de novo informando a escolha.
        """
        if self.game_over:
            return Result(ResultType.INVALID)
        if not frm.in_bounds() or not to.in_bounds():
            return Result(ResultType.INVALID)
        if self.board.piece_at(frm) is not self.current_turn:
            return Result(ResultType.INVALID)
        if self.is_mid_chain() and frm != self.active_piece:
            return Result(ResultType.INVALID)
        if not self.board.is_empty(to):
            return Result(ResultType.INVALID)

        d = directions.Direction.between(frm, to)
        if not self.board.is_connected(frm, d):
            return Result(ResultType.INVALID)
        if to in self.visited_this_turn:
            return Result(ResultType.INVALID)
        if self.is_mid_chain() and d == self.last_direction:
            return Result(ResultType.INVALID)

        options = self._compute_capture_options(frm, to, d)

        if not options:
            if self.is_mid_chain():
                # continuação obrigatoriamente precisa capturar
                return Result(ResultType.INVALID)
            # movimento simples: só permitido como único movimento do turno
            self.board.move_piece(frm, to)
            self._end_turn()
            return Result(ResultType.SIMPLE_MOVE_TURN_ENDED, captured=[])

        if len(options) == 1:
            chosen = options[0]
        elif choice is None:
            return Result(ResultType.NEEDS_CHOICE, options=options)
        else:
            chosen = next((o for o in options if o.type == choice), None)
            if chosen is None:
                return Result(ResultType.INVALID)

        # aplica o movimento + captura
        self.board.move_piece(frm, to)
        for captured_pt in chosen.captured:
            self.board.clear(captured_pt)

        self.visited_this_turn.add(frm)
        self.visited_this_turn.add(to)
        self.active_piece = to
        self.last_direction = d

        if self._check_win_by_elimination():
            return Result(ResultType.CAPTURE_CHAIN_ENDED, captured=chosen.captured, applied_choice=chosen.type)

        # verifica se há alguma continuação possível a partir da nova posição
        if not self.legal_destinations(to):
            self._end_turn()
            return Result(ResultType.CAPTURE_CHAIN_ENDED, captured=chosen.captured, applied_choice=chosen.type)

        return Result(ResultType.CAPTURE_CHAIN_CONTINUES, captured=chosen.captured, applied_choice=chosen.type)

    def end_chain_voluntarily(self) -> None:
        """Permite ao jogador encerrar voluntariamente uma sequência de capturas."""
        if self.is_mid_chain() and not self.game_over:
            self._end_turn()

    def resign(self, who: Color) -> None:
        """Jogador desiste; o adversário vence imediatamente."""
        if self.game_over:
            return
        self.game_over = True
        self.winner = who.opposite()
        self.game_over_reason = "Desistência"

    # -----------------------------------------------------------------
    # Lógica interna
    # -----------------------------------------------------------------

    def _compute_capture_options(self, frm: Point, to: Point, d) -> List[CaptureOption]:
        options: List[CaptureOption] = []
        mover = self.board.piece_at(frm) or self.current_turn

        approach = self._collect_capture_line(to, d, mover)
        if approach:
            options.append(CaptureOption(CaptureType.APPROACH, approach))

        withdrawal = self._collect_capture_line(frm, d.opposite(), mover)
        if withdrawal:
            options.append(CaptureOption(CaptureType.WITHDRAWAL, withdrawal))

        return options

    def _collect_capture_line(self, start: Point, d, mover: Color) -> List[Point]:
        """A partir de `start`, caminha na direção `d` enquanto encontrar
        peças adversárias consecutivas ligadas por linhas válidas,
        retornando a lista de pontos capturados (pode ser vazia).
        """
        captured: List[Point] = []
        cur = start
        while self.board.is_connected(cur, d):
            nxt = cur.plus(d)
            occupant = self.board.piece_at(nxt)
            if occupant is mover.opposite():
                captured.append(nxt)
                cur = nxt
            else:
                break  # vazio ou peça própria: a linha de captura para aqui
        return captured

    def _end_turn(self) -> None:
        self.current_turn = self.current_turn.opposite()
        self.active_piece = None
        self.last_direction = None
        self.visited_this_turn.clear()

        if self._check_win_by_elimination():
            return

        if not self._has_any_legal_move(self.current_turn):
            self.game_over = True
            self.winner = self.current_turn.opposite()
            self.game_over_reason = "Sem jogadas possíveis"

    def _check_win_by_elimination(self) -> bool:
        if self.board.count_pieces(Color.WHITE) == 0:
            self.game_over = True
            self.winner = Color.BLACK
            self.game_over_reason = "Todas as peças brancas foram capturadas"
            return True
        if self.board.count_pieces(Color.BLACK) == 0:
            self.game_over = True
            self.winner = Color.WHITE
            self.game_over_reason = "Todas as peças pretas foram capturadas"
            return True
        return False

    def _has_any_legal_move(self, color: Color) -> bool:
        for r in range(ROWS):
            for c in range(COLS):
                p = Point(r, c)
                if self.board.piece_at(p) is color and self.legal_destinations(p):
                    return True
        return False
