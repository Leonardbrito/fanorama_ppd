from dataclasses import dataclass
from enum import Enum
from typing import List

from .point import Point


class CaptureType(Enum):
    """Tipo de captura: nenhuma, por aproximação ou por afastamento."""

    NONE = "NONE"
    APPROACH = "APPROACH"
    WITHDRAWAL = "WITHDRAWAL"


@dataclass
class CaptureOption:
    """Uma possível forma de captura resultante de um movimento.

    APPROACH: a peça se move em direção às peças adversárias.
    WITHDRAWAL: a peça se move para longe de peças adversárias coladas
    à sua posição de origem.
    """

    type: CaptureType
    captured: List[Point]  # pontos onde havia peças adversárias capturadas
