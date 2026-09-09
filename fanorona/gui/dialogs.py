"""Pequenos diálogos modais usados durante a partida.

O jeito idiomático de fazer um diálogo modal no Tkinter é um
`tk.Toplevel` com `grab_set()`: a janela principal fica bloqueada até o
diálogo ser respondido.
"""

import tkinter as tk
from typing import Optional

from . import theme
from ..model.capture_option import CaptureOption, CaptureType


def _center_over(top: tk.Toplevel, owner: tk.Widget) -> None:
    top.update_idletasks()
    ox, oy = owner.winfo_rootx(), owner.winfo_rooty()
    ow, oh = owner.winfo_width(), owner.winfo_height()
    tw, th = top.winfo_width(), top.winfo_height()
    top.geometry(f"+{ox + (ow - tw) // 2}+{oy + (oh - th) // 2}")


def confirm_resign(owner: tk.Widget, peer_name: str) -> bool:
    """Mostra o diálogo "Confirmar desistência". Retorna True se o
    jogador confirmou (equivalente à Tela 3 do protótipo)."""
    result = {"confirmed": False}
    top = tk.Toplevel(owner)
    top.title("Confirmar desistência")
    top.configure(bg=theme.CARD_BG)
    top.resizable(False, False)
    top.transient(owner.winfo_toplevel())

    content = tk.Frame(top, bg=theme.CARD_BG, padx=26, pady=22)
    content.pack()

    tk.Label(content, text="Confirmar desistência", font=theme.DIALOG_TITLE_FONT,
             fg=theme.TEXT, bg=theme.CARD_BG).pack(anchor="w")
    tk.Label(
        content,
        text=f"Tem certeza que deseja desistir da partida? {peer_name} será declarado vencedor.",
        font=theme.BODY_FONT, fg=theme.TEXT_MUTED, bg=theme.CARD_BG,
        wraplength=270, justify="left",
    ).pack(anchor="w", pady=(10, 18))

    buttons = tk.Frame(content, bg=theme.CARD_BG)
    buttons.pack(anchor="e")

    def cancel() -> None:
        result["confirmed"] = False
        top.destroy()

    def confirm() -> None:
        result["confirmed"] = True
        top.destroy()

    theme.secondary_button(buttons, "Cancelar", cancel).pack(side="left", padx=(0, 8))
    theme.primary_button(buttons, "Desistir", confirm).pack(side="left")

    top.protocol("WM_DELETE_WINDOW", cancel)
    _center_over(top, owner.winfo_toplevel())
    top.grab_set()
    owner.wait_window(top)
    return result["confirmed"]


def ask_capture_choice(
    owner: tk.Widget, approach: Optional[CaptureOption], withdrawal: Optional[CaptureOption]
) -> Optional[CaptureType]:
    """Pergunta qual captura aplicar quando o movimento é ambíguo
    (aproximação ou afastamento). Retorna None se o usuário cancelou."""
    result = {"choice": None}
    top = tk.Toplevel(owner)
    top.title("Captura ambígua")
    top.configure(bg=theme.CARD_BG)
    top.resizable(False, False)
    top.transient(owner.winfo_toplevel())

    content = tk.Frame(top, bg=theme.CARD_BG, padx=24, pady=20)
    content.pack()

    tk.Label(
        content, text="Este movimento pode capturar de duas formas. Escolha uma:",
        font=theme.BODY_FONT, fg=theme.TEXT, bg=theme.CARD_BG, wraplength=280, justify="left",
    ).pack(anchor="w", pady=(0, 14))

    def pick(choice: Optional[CaptureType]) -> None:
        result["choice"] = choice
        top.destroy()

    tk.Button(
        content, text=f"Aproximação (captura {len(approach.captured)} peça(s))",
        command=lambda: pick(CaptureType.APPROACH),
        bg=theme.SECONDARY_BG, fg=theme.TEXT, relief="flat", bd=0,
        padx=12, pady=8, font=theme.BODY_FONT, cursor="hand2", anchor="w",
    ).pack(fill="x", pady=(0, 6))

    tk.Button(
        content, text=f"Afastamento (captura {len(withdrawal.captured)} peça(s))",
        command=lambda: pick(CaptureType.WITHDRAWAL),
        bg=theme.SECONDARY_BG, fg=theme.TEXT, relief="flat", bd=0,
        padx=12, pady=8, font=theme.BODY_FONT, cursor="hand2", anchor="w",
    ).pack(fill="x")

    top.protocol("WM_DELETE_WINDOW", lambda: pick(None))
    _center_over(top, owner.winfo_toplevel())
    top.grab_set()
    owner.wait_window(top)
    return result["choice"]
