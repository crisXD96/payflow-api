"""Verifica que el dashboard y la API usen las mismas reglas de monedas y transiciones.

El frontend es un HTML estático sin build, así que replica algunas tablas del backend.
Estos tests fallan en cuanto una copia se desalinea de la otra.
"""

import re

from app.config import FRONTEND_DIR
from app.currencies import _THREE_DECIMALS, _ZERO_DECIMALS, ACTIVE_CURRENCIES
from app.models import VALID_TRANSITIONS

HTML = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


def _js_codes(const_name: str) -> set[str]:
    """Extrae los códigos de moneda de una constante JS `const NAME = '...' ... .split(' ')`."""
    match = re.search(rf"const {const_name}\s*=\s*(.*?)\.split\(' '\)", HTML, re.DOTALL)
    assert match, f"No se encontró {const_name} en frontend/index.html"
    return set(re.findall(r"\b[A-Z]{3}\b", match.group(1)))


def test_active_currencies_match_backend() -> None:
    """El selector de moneda ofrece exactamente las monedas que acepta la API."""
    assert _js_codes("ACTIVE_CURRENCIES") == ACTIVE_CURRENCIES


def test_currency_decimals_match_backend() -> None:
    """El dashboard valida y muestra los mismos decimales que valida la API."""
    assert _js_codes("ZERO_DECIMALS") == _ZERO_DECIMALS
    assert _js_codes("THREE_DECIMALS") == _THREE_DECIMALS


def test_popular_currencies_are_active() -> None:
    """Las monedas populares existen en la lista activa."""
    match = re.search(r"const POPULAR\s*=\s*\[(.*?)\]", HTML)
    assert match
    assert set(re.findall(r"'([A-Z]{3})'", match.group(1))) <= ACTIVE_CURRENCIES


def test_action_buttons_match_valid_transitions() -> None:
    """Los botones de acción de cada estado son exactamente las transiciones válidas de la API."""
    block = re.search(r"const ACTIONS\s*=\s*\{(.*?)\n\s*\};", HTML, re.DOTALL)
    assert block, "No se encontró ACTIONS en frontend/index.html"
    js_actions: dict[str, set[str]] = {}
    for state, body in re.findall(r"(\w+): \[(.*?)\]", block.group(1), re.DOTALL):
        js_actions[state] = set(re.findall(r"status: '(\w+)'", body))
    expected = {state: set(targets) for state, targets in VALID_TRANSITIONS.items() if targets}
    assert js_actions == expected
