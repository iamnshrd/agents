import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class PortfolioManager:
    """
    Простой менеджер портфеля для dry-run режима.
    Хранит баланс и открытые позиции в локальном JSON.
    """

    def __init__(self, storage_path: str = "./logs/portfolio.json", initial_balance: float = 100.0):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(exist_ok=True)
        self.current_balance: float = float(initial_balance)
        self.positions: List[Dict[str, Any]] = []
        self.last_updated: str = datetime.now().isoformat()
        self._loaded: bool = False
        self.load()

    def load(self) -> None:
        """Загружает портфель из файла, если он существует."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                self.current_balance = float(data.get("current_balance", self.current_balance))
                self.positions = list(data.get("positions", []))
                self.last_updated = data.get("last_updated", self.last_updated)
                self._loaded = True
            except Exception:
                # Если файл поврежден, сохраняем текущее состояние заново
                self.save()

    def save(self) -> None:
        """Сохраняет текущее состояние портфеля в файл."""
        data = {
            "current_balance": self.current_balance,
            "positions": self.positions,
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_balance(self) -> float:
        return self.current_balance

    def apply_trade(self, trade: Dict[str, Any]) -> None:
        """
        Применяет сделку к портфелю.
        Ожидается формат trade:
          {
            "event_title": str,
            "market_question": str,
            "side": "BUY"|"SELL",
            "price": float,   # цена вероятности [0,1]
            "size": float,    # доля баланса [0,1]
            ...
          }
        В dry-run списываем/зачисляем notional как size * current_balance.
        Кол-во условных контрактов считаем как notional / max(price, 0.01) для BUY
        и notional / max(1-price, 0.01) для SELL (псевдо-симметрия для вероятностного контракта).
        """
        side: str = str(trade.get("side", "")).upper()
        price: float = float(trade.get("price", 0.5))
        size_fraction: float = float(trade.get("size", 0.0))
        if size_fraction <= 0:
            return

        notional: float = max(0.0, min(1.0, size_fraction)) * self.current_balance

        # Рассчитываем условное количество "контрактов" для учета позиции
        if side == "BUY":
            qty = notional / max(price, 0.01)
            self.current_balance -= notional
        elif side == "SELL":
            qty = notional / max(1.0 - price, 0.01)
            self.current_balance -= notional
        else:
            return

        position = {
            "id": f"pos_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "event_title": trade.get("event_title", "Unknown"),
            "market_question": trade.get("market_question", "Unknown"),
            "side": side,
            "entry_price": price,
            "size_fraction": size_fraction,
            "notional": notional,
            "qty": qty,
            "opened_at": datetime.now().isoformat(),
        }
        self.positions.append(position)
        self.save()

    def mark_to_market(self, current_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Примитивный mark-to-market: оценивает нереализованный PnL при текущей цене.
        Если цена не передана, возвращает сводку по позициям без PnL.
        """
        summary = {
            "positions": len(self.positions),
            "unrealized_pnl": 0.0,
            "balance": self.current_balance,
        }
        if current_price is None or not self.positions:
            return summary

        unrealized = 0.0
        for pos in self.positions:
            side = pos.get("side")
            entry = float(pos.get("entry_price", 0.5))
            notional = float(pos.get("notional", 0.0))
            # Линейная аппроксимация для бинарного контракта
            if side == "BUY":
                change = (current_price - entry)
            else:
                change = ((1.0 - current_price) - (1.0 - entry))
            unrealized += notional * change

        summary["unrealized_pnl"] = unrealized
        return summary

    def close_position(self, position_id: str, exit_price: float) -> Optional[Dict[str, Any]]:
        """
        Закрывает позицию по заданной цене, возвращает результат с реализованным PnL.
        """
        for idx, pos in enumerate(self.positions):
            if pos.get("id") == position_id:
                side = pos.get("side")
                entry = float(pos.get("entry_price", 0.5))
                notional = float(pos.get("notional", 0.0))
                # PnL по той же линейной аппроксимации
                if side == "BUY":
                    change = (exit_price - entry)
                else:
                    change = ((1.0 - exit_price) - (1.0 - entry))
                realized = notional * change
                # Возврат нотионала + PnL в баланс
                self.current_balance += notional + realized
                result = {
                    "position_id": position_id,
                    "side": side,
                    "entry_price": entry,
                    "exit_price": float(exit_price),
                    "notional": notional,
                    "realized_pnl": realized,
                    "closed_at": datetime.now().isoformat(),
                }
                # Удаляем позицию
                del self.positions[idx]
                self.save()
                return result
        return None

    def get_positions(self) -> List[Dict[str, Any]]:
        return list(self.positions)


