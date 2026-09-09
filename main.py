"""Ponto de entrada do jogo Fanorona.

Para rodar:  python3 main.py
"""

import tkinter as tk

from fanorona.gui.main_app import MainApp


def main() -> None:
    root = tk.Tk()
    MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
