import os
from datetime import datetime
from typing import List, Dict, Any


class ParetoAgent:
    """
    Реализация правил из enhanced_agents/pareto.md для приоритизации элементов.

    Ожидает элементы как словари с произвольными полями. Для рынков Polymarket
    использует эвристики по полям: spread, funded, rewardsMinSize, rewardsMaxSpread, end.
    """

    def __init__(self, top_fraction: float | None = None) -> None:
        try:
            env_fraction = float(os.getenv("PARETO_TOP_FRACTION", "0.2"))
        except Exception:
            env_fraction = 0.2
        self.top_fraction = top_fraction if top_fraction is not None else env_fraction

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _days_until(self, end_iso: str | None) -> float:
        if not end_iso:
            return 30.0
        try:
            end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
            delta = (end_dt - datetime.utcnow()).total_seconds() / 86400.0
            return max(0.0, delta)
        except Exception:
            return 30.0

    def _score_market(self, m: Dict[str, Any]) -> float:
        spread = self._coerce_float(m.get("spread"), 0.15)
        funded = 1.0 if bool(m.get("funded", False)) else 0.0
        rewards_min = self._coerce_float(m.get("rewardsMinSize"), 0.0)
        rewards_max_spread = self._coerce_float(m.get("rewardsMaxSpread"), 0.2)
        days = self._days_until(m.get("end"))

        # Эвристики из pareto.md
        value = max(0.0, 1.0 - min(spread, 0.99)) + 0.1 * funded + min(0.1, rewards_min / 1000.0)
        confidence = max(0.1, 1.0 - min(spread, 0.99))
        risk = min(0.9, (spread + rewards_max_spread) / 2.0)
        effort = 0.1
        time_cost = min(1.0, days / 30.0)

        priority = (value * confidence * (1.0 - risk)) / (1.0 + effort + time_cost)
        return priority

    def select_top_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            return items
        scored = [(self._score_market(it), it) for it in items]
        scored.sort(key=lambda x: x[0], reverse=True)
        k = max(1, int(len(scored) * self.top_fraction))
        return [it for _, it in scored[:k]]


