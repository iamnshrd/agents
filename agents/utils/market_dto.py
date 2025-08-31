from __future__ import annotations

from typing import Any, Dict, List


def _to_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        # stringified list
        import ast

        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return [value]


def normalize_market(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes a market object from any source (Gamma/CLOB/metadata) to a unified dict.

    Fields:
      id: int
      question: str
      description: str
      outcomes: list[str]
      outcomePrices: list[float]
      clobTokenIds: list[str]
    """
    # Accept both snake_case and camelCase
    id_val = raw.get("id")
    try:
        mid = int(id_val) if id_val is not None else 0
    except Exception:
        mid = 0

    question = (
        raw.get("question")
        or raw.get("title")
        or raw.get("market_question")
        or ""
    )
    description = raw.get("description") or ""

    outcomes = _to_list(raw.get("outcomes") or raw.get("outcome"))
    outcome_prices = [
        float(x)
        for x in _to_list(raw.get("outcomePrices") or raw.get("outcome_prices"))
        if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace(".", "", 1).isdigit())
    ]
    clob_token_ids = [str(x) for x in _to_list(raw.get("clobTokenIds") or raw.get("clob_token_ids"))]

    return {
        "id": mid,
        "question": question,
        "description": description,
        "outcomes": outcomes,
        "outcomePrices": outcome_prices,
        "clobTokenIds": clob_token_ids,
    }


