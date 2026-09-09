"""Paleta de cores e fontes usadas em toda a interface, e alguns
componentes pequenos e reutilizáveis (cartão, rótulo apagado).
"""

import tkinter as tk

APP_BG = "#F4F1EA"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#E3DDCF"
TEXT = "#2B2722"
TEXT_MUTED = "#938C7C"
ACCENT = "#C1863D"
ACCENT_DARK = "#A36E2E"
ACCENT_SOFT = "#F4E4C8"
SECONDARY_BG = "#ECE8DF"

PIECE_DARK = "#2E2B26"
PIECE_GOLD = ACCENT
BOARD_LINE = "#5B5448"
BOARD_BG = "#FBFAF7"

# Se a família de fonte pedida não existir no sistema, o Tkinter cai
# graciosamente numa fonte padrão.
TITLE_FONT = ("Georgia", 26, "bold")
HEADER_FONT = ("Georgia", 17, "bold")
BIG_TITLE_FONT = ("Georgia", 20, "bold")
DIALOG_TITLE_FONT = ("Helvetica", 14, "bold")
SUBTITLE_FONT = ("Helvetica", 11)
LABEL_FONT = ("Helvetica", 10)
BODY_FONT = ("Helvetica", 11)
BOLD_BODY_FONT = ("Helvetica", 11, "bold")
SMALL_FONT = ("Helvetica", 9)
BUTTON_FONT = ("Helvetica", 10, "bold")
EYEBROW_FONT = ("Helvetica", 9, "bold")
CARD_TITLE_FONT = ("Helvetica", 9, "bold")
STAT_VALUE_FONT = ("Helvetica", 14, "bold")


def card(parent, **kwargs) -> tk.Frame:
    """Um "cartão" com fundo branco e borda sutil (sem cantos
    arredondados — o Tkinter não desenha bordas arredondadas em widgets
    comuns sem recorrer a um Canvas próprio).
    """
    return tk.Frame(parent, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, bd=0, **kwargs)


def muted_label(parent, text: str, bg: str = APP_BG) -> tk.Label:
    return tk.Label(parent, text=text, fg=TEXT_MUTED, bg=bg, font=SUBTITLE_FONT)


def primary_button(parent, text: str, command, bg_when_idle: str = None) -> tk.Button:
    """Botão "cheio", cor de destaque (ex.: Conectar, Desistir no modal, Jogar novamente)."""
    return tk.Button(
        parent, text=text, command=command,
        bg=ACCENT, fg="white", activebackground=ACCENT_DARK, activeforeground="white",
        relief="flat", bd=0, padx=16, pady=8, font=BUTTON_FONT, cursor="hand2",
    )


def outline_button(parent, text: str, command) -> tk.Button:
    """Botão contornado (ex.: Desistir no cabeçalho do jogo)."""
    return tk.Button(
        parent, text=text, command=command,
        bg=CARD_BG, fg=ACCENT_DARK, activebackground=SECONDARY_BG, activeforeground=ACCENT_DARK,
        relief="solid", bd=1, highlightbackground=ACCENT, padx=16, pady=6, font=BUTTON_FONT, cursor="hand2",
    )


def secondary_button(parent, text: str, command) -> tk.Button:
    """Botão neutro (ex.: Cancelar, Sair)."""
    return tk.Button(
        parent, text=text, command=command,
        bg=SECONDARY_BG, fg=TEXT, activebackground=CARD_BORDER, activeforeground=TEXT,
        relief="flat", bd=0, padx=16, pady=8, font=BUTTON_FONT, cursor="hand2",
    )


def text_button(parent, text: str, command, bg: str = CARD_BG) -> tk.Button:
    """Botão "de texto", sem fundo destacado (ex.: Terminar jogada)."""
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=ACCENT_DARK, activebackground=bg, activeforeground=ACCENT_DARK,
        relief="flat", bd=0, padx=6, pady=4, font=BUTTON_FONT, cursor="hand2",
    )
