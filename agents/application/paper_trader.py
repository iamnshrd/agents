from __future__ import annotations

import logging
import random
import shutil
from datetime import datetime
from typing import Any, Dict

from agents.application.executor import Executor as Agent
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket
from agents.connectors.telegram import TelegramAlertsSync
from agents.utils.trading_config import trading_config
from agents.utils.trading_logger import trading_logger
from agents.utils.metrics import trades_total, pnl_histogram
from agents.utils.portfolio import PortfolioManager
from agents.utils.market_dto import normalize_market


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PaperTrader:
    """
    Бумажный трейдинг (paper): как dry-run, но с комиссиями, проскальзыванием и частичным исполнением.
    Состояние портфеля хранится отдельно в JSON.
    """

    def __init__(self,
                 commission_bps: float = None,
                 slippage_bps: float = None,
                 min_fill: float = 0.6,
                 max_fill: float = 1.0) -> None:
        self.polymarket = Polymarket()
        self.gamma = Gamma()
        self.agent = Agent()
        self.telegram = TelegramAlertsSync()

        try:
            initial_balance = float(trading_config.get_available_balance())
        except Exception:
            initial_balance = 100.0
        # Отдельный файл состояния для paper режима
        self.portfolio = PortfolioManager(storage_path="./logs/paper_portfolio.json",
                                          initial_balance=initial_balance)

        # Исполнение
        self.commission_bps = float(commission_bps if commission_bps is not None else 10.0)
        self.slippage_bps = float(slippage_bps if slippage_bps is not None else 20.0)
        self.min_fill = max(0.1, min(float(min_fill), 1.0))
        self.max_fill = max(self.min_fill, min(float(max_fill), 1.0))

        self.daily_stats = {
            "total_trades": 0,
            "total_pnl": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
            "start_time": datetime.now(),
            "positions": [],
        }

        logger.info(f"PaperTrader initialized: commission={self.commission_bps} bps, slippage={self.slippage_bps} bps")
        self._send_startup_notification()

    def _send_startup_notification(self) -> None:
        try:
            self.telegram.send_trade_alert({
                "event_title": "Paper Bot Startup",
                "market_question": "Paper trading initialized",
                "side": "INFO",
                "price": 0.0,
                "size": 0.0,
                "confidence": 1.0,
            })
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")

    def pre_trade(self) -> None:
        # Чистим временные локальные БД
        for d in ("local_db_events", "local_db_markets"):
            try:
                shutil.rmtree(d)
            except Exception:
                pass

    def one_best_trade(self) -> None:
        try:
            self.pre_trade()

            events = self.polymarket.get_all_tradeable_events()
            logger.info(f"1. FOUND {len(events)} EVENTS")
            if not events:
                logger.warning("No tradeable events; fallback to markets")
                markets = self.polymarket.get_sampling_simplified_markets()
                logger.info(f"3. FOUND {len(markets)} MARKETS (fallback)")
            else:
                filtered_events = self.agent.filter_events_with_rag(events)
                logger.info(f"2. FILTERED {len(filtered_events)} EVENTS")
                if not filtered_events:
                    logger.warning("No events after filter")
                    return
                markets = self.agent.map_filtered_events_to_markets(filtered_events)
                logger.info(f"3. FOUND {len(markets)} MARKETS")
                if not markets:
                    logger.warning("No markets mapped from events")
                    return

            filtered_markets = self.agent.filter_markets_simple(markets)
            logger.info(f"4. FILTERED {len(filtered_markets)} MARKETS")
            if not filtered_markets:
                logger.warning("No suitable markets for paper trade")
                return

            market = filtered_markets[0]
            best_trade = self.agent.source_best_trade(market)
            logger.info(f"5. CALCULATED TRADE {best_trade}")

            trade = self._prepare_trade(market, best_trade)
            # Кламп и расчет нотионала
            max_size = max(0.0, min(float(trading_config.max_position_size), 1.0))
            trade["size"] = max(0.0, min(float(trade.get("size", 0.0)), max_size))
            pre_balance = float(self.portfolio.get_balance())
            trade["notional"] = round(pre_balance * trade["size"], 6)
            trade["portfolio_balance_before"] = pre_balance
            trade["positions_count_before"] = len(self.portfolio.positions)

            # Алерт до исполнения
            self._send_trade_alert(trade)

            # Исполнение с комиссиями/проскальзыванием/частичным заполнением
            exec_result = self._execute_trade(trade)
            # Логирование сделки
            try:
                trading_logger.log_trade(exec_result, trade_type="paper_execution")
            except Exception:
                pass

            # Апдейт статистики и алерт
            self._update_stats(exec_result)
            try:
                trades_total.labels(mode="paper").inc()
                pnl_histogram.observe(float(exec_result.get("pnl", 0.0)))
            except Exception:
                pass
            self._send_position_alert(exec_result)

            logger.info(
                f"Paper trade done: pnl=${exec_result.get('pnl', 0):.2f}, balance=${self.portfolio.get_balance():.2f}"
            )

        except Exception as e:
            logger.exception(f"Error in paper trade: {e}")

    def run_session(self, num_trades: int = 5, pause_secs: float = 2.0) -> None:
        import time
        for i in range(num_trades):
            logger.info(f"[Paper] Executing trade {i+1}/{num_trades}")
            self.one_best_trade()
            if i < num_trades - 1:
                time.sleep(pause_secs)

    def _prepare_trade(self, market: Any, best_trade: str) -> Dict[str, Any]:
        # Парсинг best_trade
        parts = best_trade.replace("```", "").replace("`", "").strip().split(",")
        data: Dict[str, Any] = {}
        for p in parts:
            if ":" in p:
                k, v = p.strip().split(":", 1)
                k = k.strip().lower()
                v = v.strip().strip("'\"")
                if k == "side":
                    v = v.upper()
                data[k] = v

        # Нормализация рынка
        event_title = "Unknown Event"
        market_question = "Unknown Question"
        market_id = "Unknown"
        market_url = ""
        try:
            doc = market[0] if isinstance(market, (list, tuple)) else market
            raw = doc.dict().get("metadata", {}) if hasattr(doc, "dict") else (doc if isinstance(doc, dict) else {})
            n = normalize_market(raw)
            market_question = n.get("question", market_question)
            event_title = market_question or event_title
            market_id = str(n.get("id", market_id))
            tokens = n.get("clobTokenIds") or []
            if tokens:
                market_url = f"https://polymarket.com/market/{tokens[0]}"
        except Exception:
            pass

        # Типы
        if "price" in data:
            data["price"] = float(data["price"])  # type: ignore[index]
        if "size" in data:
            data["size"] = float(data["size"])  # type: ignore[index]
        if "side" in data:
            s = str(data.get("side", "")).upper()
            data["side"] = "BUY" if "BUY" in s else ("SELL" if "SELL" in s else "UNKNOWN")

        data.update({
            "event_title": event_title,
            "market_question": market_question,
            "market_id": market_id,
            "market_url": market_url,
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.7,
        })
        return data

    def _execute_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Модель исполнения: проскальзывание, комиссия, частичный fill, псевдо-MTM выход."""
        side = str(trade.get("side", "UNKNOWN")).upper()
        size = float(trade.get("size", 0.0))
        base_price = float(trade.get("price", 0.5))
        notional = float(trade.get("notional", 0.0))
        if size <= 0.0 or notional <= 0.0 or side not in ("BUY", "SELL"):
            return {
                "event_title": trade.get("event_title", "Unknown"),
                "side": side,
                "entry_price": base_price,
                "exit_price": base_price,
                "size": size,
                "pnl": 0.0,
                "price_change": 0.0,
                "execution_time": datetime.now().isoformat(),
                "trade_id": f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "market_url": trade.get("market_url", ""),
            }

        # Проскальзывание
        slip = self.slippage_bps / 10000.0
        exec_price = min(0.99, base_price + slip) if side == "BUY" else max(0.01, base_price - slip)

        # Частичное исполнение
        fill_fraction = random.uniform(self.min_fill, self.max_fill)
        exec_notional = notional * fill_fraction

        # Комиссия (на вход и выход, считаем один раз на вход для упрощения)
        fee = exec_notional * (self.commission_bps / 10000.0)

        # Применяем к портфелю: используем входную цену и exec_notional
        # Создаём временную сделку для PortfolioManager, затем корректируем notional по факту fill
        apply_trade = dict(trade)
        apply_trade["price"] = exec_price
        apply_trade["size"] = size * fill_fraction
        self.portfolio.apply_trade(apply_trade)

        # Псевдо-выход (MTM) — случайное изменение вокруг exec_price
        price_change = random.uniform(-0.08, 0.08)
        exit_price = max(0.01, min(0.99, exec_price + price_change if side == "BUY" else exec_price - price_change))

        # PnL линейно на exec_notional, минус комиссия
        pnl = exec_notional * ((exit_price - exec_price) if side == "BUY" else ((1.0 - exit_price) - (1.0 - exec_price))) - fee

        # Возвращаем в баланс: закрываем только что открытую позицию немедленно
        # Находим последнюю позицию и закрываем по exit_price
        last_pos = self.portfolio.positions[-1] if self.portfolio.positions else None
        if last_pos:
            self.portfolio.close_position(last_pos.get("id"), exit_price)

        result = {
            "event_title": trade.get("event_title", "Unknown"),
            "side": side,
            "entry_price": exec_price,
            "exit_price": exit_price,
            "size": size * fill_fraction,
            "pnl": pnl,
            "price_change": (exit_price - exec_price) if side == "BUY" else ((1.0 - exit_price) - (1.0 - exec_price)),
            "execution_time": datetime.now().isoformat(),
            "trade_id": f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "market_url": trade.get("market_url", ""),
            "commission_paid": fee,
            "fill_fraction": fill_fraction,
            "portfolio_balance": float(self.portfolio.get_balance()),
        }
        return result

    def _update_stats(self, trade_result: Dict[str, Any]) -> None:
        self.daily_stats["total_trades"] += 1
        pnl = float(trade_result.get("pnl", 0.0))
        self.daily_stats["total_pnl"] += pnl
        if pnl > 0:
            self.daily_stats["winning_trades"] += 1
        elif pnl < 0:
            self.daily_stats["losing_trades"] += 1
        self.daily_stats["positions"].append(trade_result)

    def _send_trade_alert(self, trade_data: Dict[str, Any]) -> None:
        try:
            self.telegram.send_trade_alert(trade_data)
        except Exception as e:
            logger.error(f"Failed to send trade alert: {e}")

    def _send_position_alert(self, position_data: Dict[str, Any]) -> None:
        try:
            self.telegram.send_position_alert(position_data)
        except Exception as e:
            logger.error(f"Failed to send position alert: {e}")


if __name__ == "__main__":
    t = PaperTrader()
    t.run_session(num_trades=3, pause_secs=1)


