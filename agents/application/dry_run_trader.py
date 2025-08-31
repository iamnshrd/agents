from agents.application.executor import Executor as Agent
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket
from agents.connectors.telegram import TelegramAlertsSync
from agents.utils.trading_config import trading_config
from agents.utils.portfolio import PortfolioManager
from agents.utils.market_dto import normalize_market
from agents.utils.metrics import trades_total, pnl_histogram

import shutil
import logging
from datetime import datetime
from typing import Dict, Any, List
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DryRunTrader:
    """
    Трейдер для режима dry-run с отправкой алертов в Telegram
    """
    
    def __init__(self):
        self.polymarket = Polymarket()
        self.gamma = Gamma()
        self.agent = Agent()
        self.telegram = TelegramAlertsSync()
        # Портфель dry-run
        try:
            initial_balance = float(trading_config.get_available_balance())
        except Exception:
            initial_balance = 100.0
        self.portfolio = PortfolioManager(initial_balance=initial_balance)
        self._market_title_cache: dict[str, tuple[str, float]] = {}
        try:
            from agents.utils.trading_config import trading_config as _tc
            self._title_ttl_secs = float(getattr(_tc, "market_title_ttl_seconds", 3600))
        except Exception:
            self._title_ttl_secs = 3600.0
        
        # Статистика торговли
        self.daily_stats = {
            "total_trades": 0,
            "total_pnl": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
            "start_time": datetime.now(),
            "positions": []
        }
        
        # Проверяем режим
        if not trading_config.is_dry_run():
            logger.warning(f"DryRunTrader initialized in {trading_config.trading_mode} mode. Use regular Trader for live trading.")
        
        # Логируем конфигурацию
        logger.info(f"DryRunTrader initialized in {trading_config.trading_mode} mode")
        logger.info(f"Available balance (cfg): ${trading_config.get_available_balance():.2f}")
        logger.info(f"Portfolio balance (dry-run): ${self.portfolio.get_balance():.2f}")
        logger.info(f"Risk limits: {trading_config.get_risk_limits()}")
        
        # Отправляем уведомление о запуске
        self._send_startup_notification()
    
    def _send_startup_notification(self):
        """Отправляет уведомление о запуске бота"""
        startup_message = f"""
🚀 <b>BOT ЗАПУЩЕН</b>

🔧 <b>Режим:</b> DRY RUN
💰 <b>Баланс (портфель):</b> ${self.portfolio.get_balance():.2f}
📊 <b>Макс. размер позиции:</b> {trading_config.max_position_size*100:.1f}%
⚠️ <b>Риск на сделку:</b> {trading_config.risk_per_trade*100:.1f}%

⏰ <b>Время запуска:</b> {datetime.now().strftime('%H:%M:%S')}
        """
        
        try:
            self.telegram.send_trade_alert({
                "event_title": "Bot Startup",
                "market_question": "Trading bot initialized",
                "side": "INFO",
                "price": 0,
                "size": 0,
                "confidence": 1.0
            })
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    def pre_trade_logic(self) -> None:
        """Подготовка к торговле"""
        self.clear_local_dbs()
        
        # Проверяем лимиты
        if trading_config.should_stop_trading(self.daily_stats):
            logger.warning("Daily limits reached. Stopping trading.")
            self._send_risk_alert({
                "risk_level": "HIGH",
                "description": "Daily trading limits reached",
                "potential_loss": 0
            })
            return
    
    def clear_local_dbs(self) -> None:
        """Очищает локальные базы данных"""
        try:
            shutil.rmtree("local_db_events")
        except:
            pass
        try:
            shutil.rmtree("local_db_markets")
        except:
            pass
    
    def one_best_trade(self) -> None:
        """
        Выполняет одну лучшую торговую операцию в dry-run режиме
        """
        try:
            self.pre_trade_logic()
            
            # Получаем события
            events = self.polymarket.get_all_tradeable_events()
            logger.info(f"1. FOUND {len(events)} EVENTS")
            
            # Фильтруем события (или используем fallback по рынкам)
            if not events:
                logger.warning("No tradeable events returned from API; falling back to direct markets fetch")
                # Prefer CLOB sampling → enrich via Gamma mapping inside helper
                markets = self.polymarket.get_sampling_simplified_markets()
                logger.info(f"3. FOUND {len(markets)} MARKETS (fallback: clob sampling)")
            else:
                filtered_events = self.agent.filter_events_with_rag(events)
                logger.info(f"2. FILTERED {len(filtered_events)} EVENTS")
                if not filtered_events:
                    logger.warning("No events matched filters; skipping trade")
                    return

                # Получаем рынки
                markets = self.agent.map_filtered_events_to_markets(filtered_events)
                logger.info(f"3. FOUND {len(markets)} MARKETS")
                if not markets:
                    logger.warning("No markets mapped from filtered events; skipping trade")
                    return
            
            # Фильтруем рынки (без RAG, чтобы исключить записи в БД)
            filtered_markets = self.agent.filter_markets_simple(markets)
            logger.info(f"4. FILTERED {len(filtered_markets)} MARKETS")
            
            if not filtered_markets:
                logger.warning("No suitable markets found for trading")
                return

            # Pareto-агент отключен по запросу; используем результат фильтра LLM/RAG как есть
            
            # Выбираем лучший рынок
            market = filtered_markets[0]
            best_trade = self.agent.source_best_trade(market)
            logger.info(f"5. CALCULATED TRADE {best_trade}")
            
            # Валидируем и обогащаем данные о сделке
            trade_data = self._prepare_trade_data(market, best_trade)
            # Клампим размер позиции по риск-лимитам
            max_size = float(trading_config.max_position_size)
            max_size = max(0.0, min(max_size, 1.0))
            size_val = float(trade_data.get("size", 0.0))
            clamped_size = max(0.0, min(size_val, max_size))
            trade_data["size"] = clamped_size
            # Расчет нотионала от текущего dry-run баланса (до применения сделки)
            pre_balance = float(self.portfolio.get_balance())
            trade_data["notional"] = round(pre_balance * clamped_size, 6)
            
            # Добавляем портфельные метаданные в алерт (до применения сделки)
            trade_data["portfolio_balance_before"] = pre_balance
            trade_data["positions_count_before"] = len(self.portfolio.positions)
            # Отправляем алерт о сделке
            self._send_trade_alert(trade_data)
            
            # Применяем сделку к портфелю (спишет нотионал, добавит позицию)
            self.portfolio.apply_trade(trade_data)
            
            # Симулируем исполнение сделки
            trade_result = self._simulate_trade_execution(trade_data)
            # Добавляем пост-фактум баланс портфеля
            trade_result["portfolio_balance"] = float(self.portfolio.get_balance())
            
            # Обновляем статистику
            self._update_trading_stats(trade_result)
            try:
                trades_total.labels(mode="dry_run").inc()
                pnl_histogram.observe(float(trade_result.get("pnl", 0.0)))
            except Exception:
                pass
            
            # Отправляем алерт о результате
            self._send_position_alert(trade_result)
            
            # Логируем состояние портфеля
            logger.info(
                f"Portfolio after trade — balance: ${self.portfolio.get_balance():.2f}, positions: {len(self.portfolio.positions)}"
            )
            
            logger.info(f"6. DRY RUN TRADE COMPLETED: {trade_result}")
            
        except Exception as e:
            logger.exception(f"Error in dry run trading: {e}")
            self._send_risk_alert({
                "risk_level": "HIGH",
                "description": f"Trading error: {str(e)}",
                "potential_loss": 0
            })
    
    def _prepare_trade_data(self, market: Any, best_trade: str) -> Dict[str, Any]:
        """Подготавливает данные о сделке для алертов"""
        try:
            # Парсим строку с данными о сделке
            # Пример: "price:0.3, size:0.2, side: BUY"
            trade_parts = best_trade.replace("```", "").replace("`", "").strip().split(",")
            trade_data = {}
            
            for part in trade_parts:
                if ":" in part:
                    key, value = part.strip().split(":", 1)
                    k = key.strip().lower()
                    v = value.strip().strip("'\"")
                    if k == "side":
                        v = v.upper().replace("BUY", "BUY").replace("SELL", "SELL")
                    trade_data[k] = v
            
            # Обогащаем данными о рынке
            event_title = "Unknown Event"
            market_question = "Unknown Question"
            market_id = "Unknown"
            market_url = ""
            try:
                doc = market[0] if isinstance(market, (list, tuple)) else market
                if hasattr(doc, "dict"):
                    md = doc.dict().get("metadata", {})
                    n = normalize_market(md)
                    market_question = n.get("question", market_question)
                    event_title = market_question or event_title
                    market_id = str(n.get("id", market_id))
                    tokens = n.get("clobTokenIds") or []
                    if tokens:
                        market_url = f"https://polymarket.com/market/{tokens[0]}"
                elif isinstance(doc, dict):
                    n = normalize_market(doc)
                    market_question = n.get("question", market_question)
                    event_title = market_question or event_title
                    market_id = str(n.get("id", market_id))
                    tokens = n.get("clobTokenIds") or []
                    if tokens:
                        market_url = f"https://polymarket.com/market/{tokens[0]}"
            except Exception:
                pass

            # Если всё ещё Unknown, пробуем кэш/рефетч по id
            try:
                if (event_title == "Unknown Event" or market_question == "Unknown Question") and market_id and market_id != "Unknown":
                    import time
                    cached = self._market_title_cache.get(market_id)
                    now = time.time()
                    if cached:
                        title, ts = cached
                        if now - ts <= self._title_ttl_secs:
                            market_question = title
                            event_title = title
                        else:
                            cached = None
                    if not cached:
                        # Попытка получения вопроса с Gamma → Polymarket маппинг
                        detail = self.gamma.get_market(int(market_id))
                        mapped = self.polymarket.map_api_to_market(detail)
                        title = mapped.get("question", None) if isinstance(mapped, dict) else None
                        if title:
                            self._market_title_cache[market_id] = (title, now)
                            market_question = title
                            event_title = title
            except Exception:
                pass

            trade_data.update({
                "event_title": event_title,
                "market_question": market_question,
                "market_id": market_id,
                "market_url": market_url,
                "confidence": 0.7,  # Можно получать от AI агента
                "timestamp": datetime.now().isoformat()
            })
            
            # Конвертируем типы
            if "price" in trade_data:
                trade_data["price"] = float(trade_data["price"])
            if "size" in trade_data:
                trade_data["size"] = float(trade_data["size"])
            if "side" in trade_data:
                s = str(trade_data.get("side", "")).upper()
                trade_data["side"] = "BUY" if "BUY" in s else ("SELL" if "SELL" in s else "UNKNOWN")
            
            return trade_data
            
        except Exception as e:
            logger.error(f"Error preparing trade data: {e}")
            return {
                "event_title": "Unknown",
                "market_question": "Unknown",
                "side": "UNKNOWN",
                "price": 0,
                "size": 0,
                "confidence": 0
            }
    
    def _simulate_trade_execution(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Симулирует исполнение сделки"""
        # В dry-run режиме просто симулируем результат
        import random
        
        # Базовые параметры сделки
        base_price = float(trade_data.get("price", 0.5))
        side = str(trade_data.get("side", "UNKNOWN")).upper()
        # Симулируем изменение цены (в реальности зависит от рынка)
        price_change = random.uniform(-0.1, 0.1)  # ±10% изменение цены
        new_price = max(0.01, min(0.99, base_price + price_change))
        # Стоимость позиции
        position_value = float(trade_data.get("size", 0.0)) * float(trading_config.get_available_balance())
        pnl = position_value * price_change
        
        trade_result = {
            "event_title": trade_data.get("event_title", "Unknown"),
            "side": side,
            "entry_price": base_price,
            "exit_price": new_price,
            "size": trade_data.get("size", 0.0),
            "pnl": pnl,
            "price_change": price_change,
            "execution_time": datetime.now().isoformat(),
            "trade_id": f"dry_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        return trade_result
    
    def _update_trading_stats(self, trade_result: Dict[str, Any]):
        """Обновляет статистику торговли"""
        self.daily_stats["total_trades"] += 1
        
        pnl = trade_result.get("pnl", 0)
        self.daily_stats["total_pnl"] += pnl
        
        if pnl > 0:
            self.daily_stats["winning_trades"] += 1
        elif pnl < 0:
            self.daily_stats["losing_trades"] += 1
        
        # Добавляем позицию в список
        self.daily_stats["positions"].append(trade_result)
        
        logger.info(f"Updated stats: {self.daily_stats}")
    
    def _send_trade_alert(self, trade_data: Dict[str, Any]):
        """Отправляет алерт о торговой операции"""
        try:
            self.telegram.send_trade_alert(trade_data)
        except Exception as e:
            logger.error(f"Failed to send trade alert: {e}")
    
    def _send_position_alert(self, position_data: Dict[str, Any]):
        """Отправляет алерт о позиции"""
        try:
            self.telegram.send_position_alert(position_data)
        except Exception as e:
            logger.error(f"Failed to send position alert: {e}")
    
    def _send_risk_alert(self, risk_data: Dict[str, Any]):
        """Отправляет алерт о рисках"""
        try:
            self.telegram.send_risk_alert(risk_data)
        except Exception as e:
            logger.error(f"Failed to send risk alert: {e}")
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Возвращает дневную сводку торговли"""
        if self.daily_stats["total_trades"] == 0:
            return {"message": "No trades executed today"}
        
        win_rate = self.daily_stats["winning_trades"] / self.daily_stats["total_trades"]
        
        summary = {
            "total_trades": self.daily_stats["total_trades"],
            "total_pnl": self.daily_stats["total_pnl"],
            "winning_trades": self.daily_stats["winning_trades"],
            "losing_trades": self.daily_stats["losing_trades"],
            "win_rate": win_rate,
            "start_time": self.daily_stats["start_time"].isoformat(),
            "end_time": datetime.now().isoformat()
        }
        
        return summary
    
    def send_daily_summary(self):
        """Отправляет ежедневную сводку в Telegram"""
        try:
            summary = self.get_daily_summary()
            self.telegram.send_daily_summary(summary)
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
    
    def maintain_positions(self):
        """Простое сопровождение: частично/полностью закрывает позиции по триггерам TP/SL."""
        try:
            positions = self.portfolio.get_positions()
            if not positions:
                return

            # Используем упрощенную модель "текущей цены":
            # в реале — запросить orderbook/mark price. Здесь — переиспользуем симуляцию.
            import random
            for pos in list(positions):
                pos_id = pos.get("id")
                entry = float(pos.get("entry_price", 0.5))

                # Симулированное текущее значение вокруг entry
                current = max(0.01, min(0.99, entry + random.uniform(-0.08, 0.08)))

                # Проверяем SL/TP из конфигурации
                tp = float(trading_config.take_profit_percentage)
                sl = float(trading_config.stop_loss_percentage)

                # Линейная метрика изменения
                if pos.get("side") == "BUY":
                    change = (current - entry)
                else:
                    change = ((1.0 - current) - (1.0 - entry))

                # Триггерим закрытие
                if change >= tp or change <= -sl:
                    closed = self.portfolio.close_position(pos_id, current)
                    if closed:
                        # Отправляем алерт о закрытии
                        closed_alert = {
                            "event_title": pos.get("event_title", "Unknown"),
                            "side": pos.get("side", "?"),
                            "entry_price": closed.get("entry_price", entry),
                            "exit_price": closed.get("exit_price", current),
                            "price_change": change,
                            "size": pos.get("size_fraction", 0),
                            "pnl": closed.get("realized_pnl", 0.0),
                            "market_url": pos.get("market_url", ""),
                            "portfolio_balance": float(self.portfolio.get_balance()),
                        }
                        self._send_position_alert(closed_alert)
                        logger.info(
                            f"Closed position {pos_id}: pnl=${closed_alert['pnl']:.2f}, balance=${self.portfolio.get_balance():.2f}"
                        )
        except Exception as e:
            logger.error(f"Error in maintain_positions: {e}")
    
    def incentive_farm(self):
        """Фарминг стимулов (заглушка для dry-run)"""
        logger.info("Incentive farming not implemented in dry-run mode")
        pass

    def run_session(self, num_trades: int = 10, pause_secs: float = 2.0):
        """Непрерывная сессия: выполняет несколько сделок и сопровождает позиции."""
        import time
        try:
            for i in range(num_trades):
                logger.info(f"[Session] Executing trade {i+1}/{num_trades}")
                self.one_best_trade()
                # Сопровождение позиций после сделки
                self.maintain_positions()
                if i < num_trades - 1:
                    time.sleep(pause_secs)
            # Итоговая сводка
            self.send_daily_summary()
        except Exception as e:
            logger.error(f"Error in run_session: {e}")
            self.send_daily_summary()


if __name__ == "__main__":
    # Создаем и запускаем dry-run трейдера
    trader = DryRunTrader()
    
    try:
        # Выполняем торговую операцию
        trader.one_best_trade()
        
        # Отправляем дневную сводку
        trader.send_daily_summary()
        
    except KeyboardInterrupt:
        logger.info("Dry-run trading interrupted by user")
        trader.send_daily_summary()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        trader.send_daily_summary()
