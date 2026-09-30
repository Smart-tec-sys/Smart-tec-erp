"""Navegação Streamlit que preserva a sessão e altera apenas query params."""

from collections.abc import MutableMapping
from typing import Any
from urllib.parse import parse_qsl


def navigate_in_current_session(
    session: MutableMapping[str, Any],
    query_params: MutableMapping[str, Any],
    destination: str,
    extra_params: str = "",
) -> None:
    """Atualiza a rota sem recarregar o documento ou copiar dados de auth."""
    clean_destination = str(destination or "").strip()
    if not clean_destination:
        raise ValueError("destino de navegação é obrigatório")
    query_params.clear()
    query_params["go_to"] = clean_destination
    for key, value in parse_qsl(extra_params.lstrip("?&"), keep_blank_values=True):
        query_params[key] = value
    # `session` é intencionalmente recebido e preservado sem cópia/reset.
    if session is None:
        raise TypeError("sessão Streamlit é obrigatória")
