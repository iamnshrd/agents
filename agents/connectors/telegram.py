import os
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
import asyncio
import aiohttp
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramAlerts:
    """
    Класс для отправки алертов в Telegram о торговых операциях
    """
    
    def __init__(self):
        load_dotenv()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.alerts_enabled = os.getenv("TELEGRAM_ALERTS_ENABLED", "false").lower() == "true"
        self.alert_types = os.getenv("TELEGRAM_ALERT_TYPES", "trade,position,risk").split(",")
        # Network resilience
        try:
            self.retry_attempts = int(os.getenv("TELEGRAM_RETRY_ATTEMPTS", "3"))
        except Exception:
            self.retry_attempts = 3
        try:
            self.retry_backoff = float(os.getenv("TELEGRAM_RETRY_BACKOFF_SECS", "1.5"))
        except Exception:
            self.retry_backoff = 1.5
        try:
            self.request_timeout = float(os.getenv("TELEGRAM_TIMEOUT_SECS", "8.0"))
        except Exception:
            self.request_timeout = 8.0
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured. Alerts will be disabled.")
            self.alerts_enabled = False
    
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Отправляет сообщение в Telegram
        """
        if not self.alerts_enabled:
            logger.info(f"Telegram alerts disabled. Message: {message[:100]}...")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)

        for attempt in range(1, self.retry_attempts + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            logger.info("Telegram message sent successfully")
                            return True
                        # Retry on common transient statuses
                        if response.status in {408, 429, 500, 502, 503, 504}:
                            logger.warning(
                                f"Telegram API {response.status}. Retry {attempt}/{self.retry_attempts}"
                            )
                        else:
                            logger.error(
                                f"Failed to send Telegram message: HTTP {response.status}"
                            )
                            return False
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"Telegram send error: {e}. Retry {attempt}/{self.retry_attempts}"
                )

            # backoff before next try
            await asyncio.sleep(self.retry_backoff * attempt)

        logger.error("Telegram message send failed after retries")
        return False

    async def send_message_to(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """Отправляет сообщение на заданный chat_id (для бота-команд)."""
        if not self.bot_token or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    return response.status == 200
        except Exception:
            return False
    
    def format_trade_alert(self, trade_data: Dict) -> str:
        """
        Форматирует алерт о торговой операции
        """
        emoji_map = {
            "BUY": "🟢",
            "SELL": "🔴",
            "profit": "📈",
            "loss": "📉",
            "neutral": "⚖️"
        }
        
        side_emoji = emoji_map.get(trade_data.get("side", ""), "⚡")
        event_title = trade_data.get("event_title", "Unknown Event")
        market_question = trade_data.get("market_question", "Unknown Market")
        side = trade_data.get("side", "UNKNOWN")
        price = trade_data.get("price", 0)
        size = trade_data.get("size", 0)
        confidence = trade_data.get("confidence", 0)
        
        # Определяем тип операции
        if side == "BUY":
            operation = "ПОКУПКА"
        elif side == "SELL":
            operation = "ПРОДАЖА"
        else:
            operation = "ОПЕРАЦИЯ"
        
        # Формируем ссылку на рынок
        market_url = trade_data.get("market_url", "")
        if market_url:
            event_display = f"<a href='{market_url}'>{event_title}</a>"
        else:
            event_display = event_title
        
        # Дополнительные поля портфеля (опционально)
        portfolio_balance = trade_data.get("portfolio_balance_before")
        positions_count = trade_data.get("positions_count_before")

        message = f"""
{side_emoji} <b>{operation}</b> {side_emoji}

📊 <b>Событие:</b> {event_display}
🧭 <b>Сторона:</b> {side}
❓ <b>Вопрос:</b> {market_question}
💰 <b>Цена:</b> ${price:.3f}
📏 <b>Размер:</b> {size*100:.1f}%
🎯 <b>Уверенность:</b> {confidence*100:.1f}%

{f"💼 <b>Баланс портфеля:</b> ${float(portfolio_balance):.2f}" if portfolio_balance is not None else ""}
{f"📚 <b>Открытых позиций:</b> {int(positions_count)}" if positions_count is not None else ""}

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
🔧 <b>Режим:</b> DRY RUN
        """
        
        return message.strip()
    
    def format_position_alert(self, position_data: Dict) -> str:
        """
        Форматирует алерт о позиции
        """
        pnl = position_data.get("pnl", 0)
        pnl_emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "⚖️"
        side = position_data.get("side", "?")
        entry = position_data.get("entry_price", 0)
        exitp = position_data.get("exit_price", 0)
        delta = position_data.get("price_change", 0)

        # Формируем ссылку на рынок
        market_url = position_data.get("market_url", "")
        event_title = position_data.get('event_title', 'Unknown')
        if market_url:
            event_display = f"<a href='{market_url}'>{event_title}</a>"
        else:
            event_display = event_title

        # Доп. поле баланса (опционально)
        portfolio_balance = position_data.get("portfolio_balance")

        message = f"""
{pnl_emoji} <b>ПОЗИЦИЯ</b>

🎯 <b>Событие:</b> {event_display}
🧭 <b>Сторона:</b> {side}
💵 <b>Вход:</b> ${entry:.3f} → <b>Выход:</b> ${exitp:.3f}
📊 <b>Изм. цены:</b> {delta:+.3%}
📏 <b>Размер:</b> {position_data.get('size', 0)*100:.1f}%
💰 <b>PnL:</b> {pnl_emoji} ${pnl:.2f}

{f"💼 <b>Баланс портфеля:</b> ${float(portfolio_balance):.2f}" if portfolio_balance is not None else ""}

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
🔧 <b>Режим:</b> DRY RUN
        """

        return message.strip()
    
    def format_risk_alert(self, risk_data: Dict) -> str:
        """
        Форматирует алерт о рисках
        """
        risk_level = risk_data.get("risk_level", "MEDIUM")
        risk_emoji = {
            "LOW": "🟢",
            "MEDIUM": "🟡", 
            "HIGH": "🔴",
            "CRITICAL": "🚨"
        }.get(risk_level, "⚡")
        
        message = f"""
{risk_emoji} <b>РИСК АЛЕРТ</b> {risk_emoji}

⚠️ <b>Уровень:</b> {risk_level}
📊 <b>Описание:</b> {risk_data.get('description', 'No description')}
💰 <b>Возможные потери:</b> ${risk_data.get('potential_loss', 0):.2f}

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
        """
        
        return message.strip()
    
    def format_news_alert(self, news_data: Dict) -> str:
        """
        Форматирует алерт о новостях
        """
        relevance = news_data.get("relevance", 0)
        relevance_emoji = "🔥" if relevance > 0.8 else "⚡" if relevance > 0.6 else "📰"
        
        message = f"""
{relevance_emoji} <b>ВАЖНАЯ НОВОСТЬ</b> {relevance_emoji}

📰 <b>Заголовок:</b> {news_data.get('title', 'No title')[:100]}...
🔗 <b>Источник:</b> {news_data.get('source', 'Unknown')}
📊 <b>Релевантность:</b> {relevance*100:.1f}%
📅 <b>Дата:</b> {news_data.get('published_at', 'Unknown')}

⏰ <b>Получено:</b> {datetime.now().strftime('%H:%M:%S')}
        """
        
        return message.strip()
    
    async def send_trade_alert(self, trade_data: Dict) -> bool:
        """Отправляет алерт о торговой операции"""
        if "trade" not in self.alert_types:
            return False
        message = self.format_trade_alert(trade_data)
        return await self.send_message(message)
    
    async def send_position_alert(self, position_data: Dict) -> bool:
        """Отправляет алерт о позиции"""
        if "position" not in self.alert_types:
            return False
        message = self.format_position_alert(position_data)
        return await self.send_message(message)
    
    async def send_risk_alert(self, risk_data: Dict) -> bool:
        """Отправляет алерт о рисках"""
        if "risk" not in self.alert_types:
            return False
        message = self.format_risk_alert(risk_data)
        return await self.send_message(message)
    
    async def send_news_alert(self, news_data: Dict) -> bool:
        """Отправляет алерт о новостях"""
        if "news" not in self.alert_types:
            return False
        message = self.format_news_alert(news_data)
        return await self.send_message(message)
    
    async def send_daily_summary(self, summary_data: Dict) -> bool:
        """
        Отправляет ежедневный отчет о торговле
        """
        total_trades = summary_data.get("total_trades", 0)
        total_pnl = summary_data.get("total_pnl", 0)
        win_rate = summary_data.get("win_rate", 0)
        
        pnl_emoji = "📈" if total_pnl > 0 else "📉" if total_pnl < 0 else "⚖️"
        
        message = f"""
📊 <b>ЕЖЕДНЕВНЫЙ ОТЧЕТ</b>

📈 <b>Всего сделок:</b> {total_trades}
💰 <b>Общий PnL:</b> {pnl_emoji} ${total_pnl:.2f}
🎯 <b>Процент успешных:</b> {win_rate*100:.1f}%
📅 <b>Дата:</b> {datetime.now().strftime('%Y-%m-%d')}

🔧 <b>Режим:</b> DRY RUN
        """
        
        return await self.send_message(message.strip())

# Синхронные обертки для совместимости
class TelegramAlertsSync:
    """Синхронная обертка для TelegramAlerts"""
    
    def __init__(self):
        self.async_client = TelegramAlerts()
    
    def send_trade_alert(self, trade_data: Dict) -> bool:
        """Синхронная отправка алерта о торговой операции"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_client.send_trade_alert(trade_data))
        finally:
            loop.close()
    
    def send_position_alert(self, position_data: Dict) -> bool:
        """Синхронная отправка алерта о позиции"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_client.send_position_alert(position_data))
        finally:
            loop.close()
    
    def send_risk_alert(self, risk_data: Dict) -> bool:
        """Синхронная отправка алерта о рисках"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_client.send_risk_alert(risk_data))
        finally:
            loop.close()
    
    def send_news_alert(self, news_data: Dict) -> bool:
        """Синхронная отправка алерта о новостях"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_client.send_news_alert(news_data))
        finally:
            loop.close()
    
    def send_daily_summary(self, summary_data: Dict) -> bool:
        """Синхронная отправка ежедневного отчета"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_client.send_daily_summary(summary_data))
        finally:
            loop.close()

    def send_message_to(self, chat_id: str, message: str) -> bool:
        """Синхронная отправка произвольного сообщения на chat_id"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_client.send_message_to(chat_id, message))
        finally:
            loop.close()


# Простой long-polling бот (без внешних зависимостей), обрабатывает /positions и /portfolio
async def telegram_bot_poll(loop_interval: float = 2.0):
    """Стартует цикл чтения апдейтов и обрабатывает простые команды.
    Требуются TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID (для ограничения доступа опционально).
    """
    import aiohttp
    import asyncio
    from agents.utils.portfolio import PortfolioManager

    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        return
    allowed_chat = os.getenv("TELEGRAM_CHAT_ID")
    base = f"https://api.telegram.org/bot{token}"
    offset = None
    pm = PortfolioManager()

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                params = {"timeout": 30}
                if offset:
                    params["offset"] = offset
                async with session.get(base + "/getUpdates", params=params) as resp:
                    data = await resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat = msg.get("chat", {})
                    chat_id = str(chat.get("id")) if chat.get("id") is not None else None
                    text = (msg.get("text") or "").strip()
                    if not chat_id or not text:
                        continue
                    if allowed_chat and chat_id != str(allowed_chat):
                        continue

                    if text.startswith("/positions"):
                        positions = pm.get_positions()
                        if not positions:
                            out = "Нет открытых позиций"
                        else:
                            lines = []
                            for p in positions[:20]:
                                lines.append(
                                    f"{p.get('id')} | {p.get('side')} | {p.get('event_title','?')} | entry={float(p.get('entry_price',0)):.3f} | notional=${float(p.get('notional',0)):.2f}"
                                )
                            out = "\n".join(lines)
                        await TelegramAlerts().send_message_to(chat_id, out)

                    if text.startswith("/portfolio"):
                        bal = pm.get_balance()
                        mtm = pm.mark_to_market()
                        out = (
                            f"Баланс: ${bal:.2f}\n"
                            f"Позиции: {mtm.get('positions',0)}\n"
                            f"Нереализованный PnL: ${mtm.get('unrealized_pnl',0.0):.2f}"
                        )
                        await TelegramAlerts().send_message_to(chat_id, out)
            except Exception as e:
                logger.error(f"Telegram bot poll error: {e}")
            await asyncio.sleep(loop_interval)
