"""Script de validação da lógica do motor via console — não depende do
Tkinter, então pode ser rodado mesmo sem a interface gráfica instalada:

    python3 test_game_engine.py
"""

from fanorona.model.board import Board, COLS, ROWS
from fanorona.model import direction as directions
from fanorona.model.capture_option import CaptureType
from fanorona.model.color import Color
from fanorona.model.game_engine import GameEngine, ResultType
from fanorona.model.point import Point


def print_board(b: Board) -> None:
    for r in range(ROWS):
        row = []
        for c in range(COLS):
            color = b.piece_at(Point(r, c))
            row.append("." if color is None else ("B" if color is Color.WHITE else "P"))
        print(" ".join(row))
    print()


def empty_board() -> Board:
    b = Board()
    for r in range(ROWS):
        for c in range(COLS):
            b.clear(Point(r, c))
    return b


def check(label: str, condition: bool) -> None:
    print(("[OK]   " if condition else "[FALHOU]") + " " + label)


def main() -> None:
    initial = GameEngine()
    print("=== Posicao inicial ===")
    print_board(initial.board)
    check("22 pecas brancas", initial.board.count_pieces(Color.WHITE) == 22)
    check("22 pecas pretas", initial.board.count_pieces(Color.BLACK) == 22)
    check("centro (2,4) vazio", initial.board.is_empty(Point(2, 4)))
    check("linha sempre conectada (2,0)-E", initial.board.is_connected(Point(2, 0), directions.E))

    # ---------- captura por aproximacao ----------
    print("\n=== Captura por aproximacao ===")
    b1 = empty_board()
    b1.set(Point(2, 1), Color.WHITE)
    b1.set(Point(2, 3), Color.BLACK)
    b1.set(Point(2, 4), Color.BLACK)
    e1 = GameEngine(b1, Color.WHITE)
    print_board(b1)
    r1 = e1.try_move(Point(2, 1), Point(2, 2), None)
    print(f"Resultado: {r1.type} capturadas={r1.captured}")
    check("capturou 2 pecas por aproximacao", r1.captured is not None and len(r1.captured) == 2)
    check("(2,3) e (2,4) vazios apos captura", b1.is_empty(Point(2, 3)) and b1.is_empty(Point(2, 4)))
    print_board(b1)

    # ---------- captura por afastamento ----------
    print("\n=== Captura por afastamento ===")
    b2 = empty_board()
    b2.set(Point(2, 3), Color.WHITE)
    b2.set(Point(2, 2), Color.BLACK)
    b2.set(Point(2, 1), Color.BLACK)
    e2 = GameEngine(b2, Color.WHITE)
    print_board(b2)
    r2 = e2.try_move(Point(2, 3), Point(2, 4), None)
    print(f"Resultado: {r2.type} capturadas={r2.captured}")
    check("capturou 2 pecas por afastamento", r2.captured is not None and len(r2.captured) == 2)
    print_board(b2)

    # ---------- ambiguidade: precisa escolher ----------
    print("\n=== Ambiguidade (precisa escolher aproximacao/afastamento) ===")
    b3 = empty_board()
    b3.set(Point(2, 3), Color.WHITE)
    b3.set(Point(2, 2), Color.BLACK)
    b3.set(Point(2, 5), Color.BLACK)
    e3 = GameEngine(b3, Color.WHITE)
    r3 = e3.try_move(Point(2, 3), Point(2, 4), None)
    print(f"Resultado sem escolha: {r3.type} opcoes={0 if r3.options is None else len(r3.options)}")
    check("retornou NEEDS_CHOICE com 2 opcoes", r3.type == ResultType.NEEDS_CHOICE and len(r3.options) == 2)
    r3b = e3.try_move(Point(2, 3), Point(2, 4), CaptureType.APPROACH)
    check("apos escolher APPROACH, captura (2,5)", r3b.captured is not None and Point(2, 5) in r3b.captured)
    check("(2,2) NAO foi capturada (escolha foi aproximacao)", not b3.is_empty(Point(2, 2)))

    # ---------- diagonal: linha existe apenas em metade das celulas ----------
    print("\n=== Topologia diagonal ===")
    b4 = Board()
    diag_cell_00 = b4.is_connected(Point(0, 0), directions.SE)
    diag_cell_01 = b4.is_connected(Point(0, 1), directions.SE)
    print(f"Diagonal SE a partir de (0,0): {diag_cell_00}")
    print(f"Diagonal SE a partir de (0,1): {diag_cell_01}")
    check("padrao alternado de diagonais (uma true outra false)", diag_cell_00 != diag_cell_01)

    # ---------- sequencia de capturas (chain) ----------
    # Passo 1: (0,0) -> (0,1), captura (0,2) na direcao Leste (E).
    # Passo 2: (0,1) -> (1,1), captura (2,1) na direcao Sul (S) -- direcao diferente da anterior.
    print("\n=== Sequencia de capturas (chain) ===")
    b5 = empty_board()
    b5.set(Point(0, 0), Color.WHITE)
    b5.set(Point(0, 2), Color.BLACK)
    b5.set(Point(2, 1), Color.BLACK)
    e5 = GameEngine(b5, Color.WHITE)
    r5a = e5.try_move(Point(0, 0), Point(0, 1), None)
    print(f"Passo1: {r5a.type} capturadas={r5a.captured}")
    check("passo1 captura (0,2) e cadeia continua", r5a.type == ResultType.CAPTURE_CHAIN_CONTINUES)
    check("peca ativa e (0,1)", e5.active_piece is not None and e5.active_piece == Point(0, 1))

    destinos = e5.legal_destinations(Point(0, 1))
    print(f"Destinos legais apos passo1: {destinos}")
    check(
        "nao pode voltar para (0,0) (repetiria direcao W = oposta a E, mas o real motivo e' 'ja visitado')",
        Point(0, 0) not in destinos,
    )
    check("pode continuar para (1,1) (nova direcao S, captura (2,1))", Point(1, 1) in destinos)

    r5b = e5.try_move(Point(0, 1), Point(1, 1), None)
    print(f"Passo2: {r5b.type} capturadas={r5b.captured}")
    check(
        "passo2 captura (2,1) e cadeia termina (sem mais capturas possiveis)",
        r5b.type == ResultType.CAPTURE_CHAIN_ENDED and Point(2, 1) in r5b.captured,
    )
    # Neste cenario as duas unicas pecas pretas foram capturadas, entao o jogo
    # termina por eliminacao total antes mesmo de passar o turno.
    check("jogo terminou por eliminacao total das pretas", e5.game_over and e5.winner == Color.WHITE)

    print("\nTodos os testes executados.")


if __name__ == "__main__":
    main()
