import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from decimal import Decimal, ROUND_DOWN

logger = logging.getLogger(__name__)

class TradingConfig:
    """
    Класс для управления конфигурацией торговли
    """
    
    def __init__(self):
        load_dotenv()
        self._load_config()
    
    def _load_config(self):
        """Загружает конфигурацию из переменных окружения"""
        
        # Режим торговли
        self.trading_mode = os.getenv("TRADING_MODE", "dry_run").lower()
        
        # Баланс для dry-run режима (в центах)
        self.dry_run_balance = int(os.getenv("DRY_RUN_BALANCE", "10000"))
        
        # Параметры позиций
        self.max_position_size = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
        self.risk_per_trade = float(os.getenv("RISK_PER_TRADE", "0.02"))
        
        # Управление рисками
        self.stop_loss_percentage = float(os.getenv("STOP_LOSS_PERCENTAGE", "0.05"))
        self.take_profit_percentage = float(os.getenv("TAKE_PROFIT_PERCENTAGE", "0.15"))
        self.max_daily_trades = int(os.getenv("MAX_DAILY_TRADES", "10"))
        self.max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "0.1"))
        
        # AI модель
        self.default_llm_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-3.5-turbo-16k")
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "15000"))
        
        # Логирование
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "./logs/trading.log")
        
        # Отладка
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Tavily MCP Configuration
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.tavily_server_url = os.getenv("TAVILY_MCP_SERVER_URL", "https://mcp.tavily.com/mcp/")
        self.tavily_search_depth = os.getenv("TAVILY_SEARCH_DEPTH", "basic")
        self.tavily_max_results = int(os.getenv("TAVILY_MAX_RESULTS", "10"))
        self.tavily_domains = os.getenv("TAVILY_INCLUDE_DOMAINS", "polymarket.com,predictit.org").split(",")
        
        # The Verge News MCP Configuration
        self.verge_news_api_key = os.getenv("SMITHERY_API_KEY", "970828f0-e3a7-4778-a72f-2cc44656511d")
        self.verge_news_server_url = os.getenv("VERGE_NEWS_MCP_URL", "https://server.smithery.ai/@manimohans/verge-news-mcp/mcp")
        
        logger.info(f"Trading config loaded: mode={self.trading_mode}, balance=${self.dry_run_balance/100:.2f}")
    
    def is_dry_run(self) -> bool:
        """Проверяет, включен ли режим dry-run"""
        return self.trading_mode == "dry_run"
    
    def is_live_trading(self) -> bool:
        """Проверяет, включен ли режим реальной торговли"""
        return self.trading_mode == "live"
    
    def is_paper_trading(self) -> bool:
        """Проверяет, включен ли режим paper trading"""
        return self.trading_mode == "paper"
    
    def get_available_balance(self) -> Decimal:
        """Возвращает доступный баланс для торговли"""
        if self.is_dry_run():
            return Decimal(self.dry_run_balance) / Decimal(100)  # Конвертируем из центов
        else:
            # В реальном режиме получаем баланс из кошелька
            # TODO: Реализовать получение реального баланса
            return Decimal("0")
    
    def calculate_position_size(self, confidence: float, risk_amount: Optional[float] = None) -> Decimal:
        """
        Рассчитывает размер позиции на основе уверенности и риска
        
        Args:
            confidence: Уверенность в прогнозе (0.0 - 1.0)
            risk_amount: Сумма риска в долларах (опционально)
        
        Returns:
            Размер позиции как доля от баланса
        """
        if risk_amount is None:
            risk_amount = self.risk_per_trade
        
        # Базовый размер позиции
        base_size = Decimal(str(risk_amount))
        
        # Корректируем размер на основе уверенности
        confidence_multiplier = Decimal(str(confidence))
        adjusted_size = base_size * confidence_multiplier
        
        # Ограничиваем максимальным размером позиции
        max_size = Decimal(str(self.max_position_size))
        final_size = min(adjusted_size, max_size)
        
        # Округляем до 4 знаков после запятой
        return final_size.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
    
    def validate_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидирует торговую операцию и добавляет информацию о режиме
        
        Args:
            trade_data: Данные о торговой операции
        
        Returns:
            Валидированные данные с дополнительной информацией
        """
        # Добавляем информацию о режиме торговли
        trade_data["trading_mode"] = self.trading_mode
        trade_data["is_dry_run"] = self.is_dry_run()
        
        # В dry-run режиме не проверяем реальный баланс
        if self.is_dry_run():
            trade_data["available_balance"] = self.get_available_balance()
            trade_data["max_position_value"] = trade_data["available_balance"] * Decimal(str(self.max_position_size))
        
        # Добавляем временные метки
        from datetime import datetime
        trade_data["timestamp"] = datetime.now().isoformat()
        
        return trade_data
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """Возвращает лимиты по рискам"""
        return {
            "stop_loss_percentage": self.stop_loss_percentage,
            "take_profit_percentage": self.take_profit_percentage,
            "max_daily_trades": self.max_daily_trades,
            "max_daily_loss": self.max_daily_loss,
            "max_position_size": self.max_position_size,
            "risk_per_trade": self.risk_per_trade
        }
    
    def should_stop_trading(self, daily_stats: Dict[str, Any]) -> bool:
        """
        Проверяет, нужно ли остановить торговлю на основе дневной статистики
        
        Args:
            daily_stats: Статистика за день
        
        Returns:
            True если торговлю нужно остановить
        """
        daily_trades = daily_stats.get("total_trades", 0)
        daily_pnl = daily_stats.get("total_pnl", 0)
        available_balance = self.get_available_balance()
        
        # Проверяем лимит по количеству сделок
        if daily_trades >= self.max_daily_trades:
            logger.warning(f"Daily trade limit reached: {daily_trades}/{self.max_daily_trades}")
            return True
        
        # Проверяем лимит по убыткам
        if available_balance > 0:
            daily_loss_percentage = abs(min(daily_pnl, 0)) / available_balance
            if daily_loss_percentage >= self.max_daily_loss:
                logger.warning(f"Daily loss limit reached: {daily_loss_percentage*100:.2f}%")
                return True
        
        return False
    
    def reload_config(self):
        """Перезагружает конфигурацию из файла"""
        logger.info("Reloading trading configuration...")
        self._load_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Возвращает краткую сводку конфигурации"""
        return {
            "trading_mode": self.trading_mode,
            "available_balance": float(self.get_available_balance()),
            "risk_limits": self.get_risk_limits(),
            "ai_model": {
                "model": self.default_llm_model,
                "temperature": self.llm_temperature,
                "max_tokens": self.max_tokens
            },
            "environment": self.environment,
            "debug_mode": self.debug_mode,
            "tavily": self.get_tavily_config(),
            "verge_news": self.get_verge_news_config()
        }
    
    def get_tavily_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию Tavily MCP"""
        return {
            "api_key_configured": bool(self.tavily_api_key),
            "server_url": self.tavily_server_url,
            "search_depth": self.tavily_search_depth,
            "max_results": self.tavily_max_results,
            "include_domains": self.tavily_domains
        }
    
    def is_tavily_available(self) -> bool:
        """Проверяет, доступен ли Tavily MCP"""
        return bool(self.tavily_api_key)
    
    def get_verge_news_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию The Verge News MCP"""
        return {
            "api_key_configured": bool(self.verge_news_api_key),
            "server_url": self.verge_news_server_url,
            "source": "The Verge",
            "available_tools": ["get-daily-news", "get-weekly-news", "search-news"]
        }
    
    def is_verge_news_available(self) -> bool:
        """Проверяет, доступен ли The Verge News MCP"""
        return bool(self.verge_news_api_key)

# Глобальный экземпляр конфигурации
trading_config = TradingConfig()
