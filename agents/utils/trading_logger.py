import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class TradingLogger:
    """
    Расширенный логгер для торговых операций
    """
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Основной логгер
        self.logger = self._setup_main_logger()
        
        # Логгер для торговых операций
        self.trade_logger = self._setup_trade_logger()
        
        # Логгер для ошибок
        self.error_logger = self._setup_error_logger()
        
        # Логгер для производительности
        self.performance_logger = self._setup_performance_logger()
    
    def _setup_main_logger(self) -> logging.Logger:
        """Настраивает основной логгер"""
        logger = logging.getLogger("trading_main")
        logger.setLevel(logging.INFO)
        
        # Файловый хендлер
        main_handler = logging.FileHandler(self.log_dir / "trading.log")
        main_handler.setLevel(logging.INFO)
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        main_handler.setFormatter(formatter)
        
        logger.addHandler(main_handler)
        
        return logger
    
    def _setup_trade_logger(self) -> logging.Logger:
        """Настраивает логгер для торговых операций"""
        logger = logging.getLogger("trading_operations")
        logger.setLevel(logging.INFO)
        
        # Файловый хендлер для сделок
        trade_handler = logging.FileHandler(self.log_dir / "trades.log")
        trade_handler.setLevel(logging.INFO)
        
        # Форматтер для сделок
        formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        trade_handler.setFormatter(formatter)
        
        logger.addHandler(trade_handler)
        
        return logger
    
    def _setup_error_logger(self) -> logging.Logger:
        """Настраивает логгер для ошибок"""
        logger = logging.getLogger("trading_errors")
        logger.setLevel(logging.ERROR)
        
        # Файловый хендлер для ошибок
        error_handler = logging.FileHandler(self.log_dir / "errors.log")
        error_handler.setLevel(logging.ERROR)
        
        # Форматтер для ошибок
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s\n'
        )
        error_handler.setFormatter(formatter)
        
        logger.addHandler(error_handler)
        
        return logger
    
    def _setup_performance_logger(self) -> logging.Logger:
        """Настраивает логгер для производительности"""
        logger = logging.getLogger("trading_performance")
        logger.setLevel(logging.INFO)
        
        # Файловый хендлер для производительности
        perf_handler = logging.FileHandler(self.log_dir / "performance.log")
        perf_handler.setLevel(logging.INFO)
        
        # Форматтер для производительности
        formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        perf_handler.setFormatter(formatter)
        
        logger.addHandler(perf_handler)
        
        return logger
    
    def log_trade(self, trade_data: Dict[str, Any], trade_type: str = "execution"):
        """
        Логирует торговую операцию
        
        Args:
            trade_data: Данные о сделке
            trade_type: Тип операции (execution, signal, etc.)
        """
        try:
            # Создаем запись о сделке
            trade_record = {
                "timestamp": datetime.now().isoformat(),
                "type": trade_type,
                "data": trade_data
            }
            
            # Логируем в основной лог
            self.logger.info(f"Trade {trade_type}: {trade_data.get('event_title', 'Unknown')}")
            
            # Логируем детали в торговый лог
            self.trade_logger.info(json.dumps(trade_record, indent=2))
            
            # Сохраняем в JSON файл для анализа
            self._save_trade_to_json(trade_record)
            
        except Exception as e:
            self.error_logger.error(f"Error logging trade: {e}")
    
    def log_position_update(self, position_data: Dict[str, Any]):
        """Логирует обновление позиции"""
        try:
            position_record = {
                "timestamp": datetime.now().isoformat(),
                "type": "position_update",
                "data": position_data
            }
            
            self.logger.info(f"Position updated: {position_data.get('event_title', 'Unknown')}")
            self.trade_logger.info(json.dumps(position_record, indent=2))
            
        except Exception as e:
            self.error_logger.error(f"Error logging position: {e}")
    
    def log_risk_alert(self, risk_data: Dict[str, Any]):
        """Логирует алерт о рисках"""
        try:
            risk_record = {
                "timestamp": datetime.now().isoformat(),
                "type": "risk_alert",
                "data": risk_data
            }
            
            self.logger.warning(f"Risk alert: {risk_data.get('risk_level', 'Unknown')} - {risk_data.get('description', 'No description')}")
            self.trade_logger.info(json.dumps(risk_record, indent=2))
            
        except Exception as e:
            self.error_logger.error(f"Error logging risk alert: {e}")
    
    def log_performance(self, performance_data: Dict[str, Any]):
        """Логирует данные о производительности"""
        try:
            perf_record = {
                "timestamp": datetime.now().isoformat(),
                "type": "performance",
                "data": performance_data
            }
            
            self.performance_logger.info(json.dumps(perf_record, indent=2))
            
        except Exception as e:
            self.error_logger.error(f"Error logging performance: {e}")
    
    def log_error(self, error: Exception, context: str = ""):
        """Логирует ошибку"""
        try:
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "type": "error",
                "context": context,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": self._get_traceback(error)
            }
            
            self.error_logger.error(f"Error in {context}: {error}")
            self.logger.error(f"Error in {context}: {error}")
            
            # Сохраняем детали ошибки
            self._save_error_to_json(error_record)
            
        except Exception as e:
            # Fallback логирование
            print(f"Critical error in logging: {e}")
    
    def log_daily_summary(self, summary_data: Dict[str, Any]):
        """Логирует ежедневную сводку"""
        try:
            summary_record = {
                "timestamp": datetime.now().isoformat(),
                "type": "daily_summary",
                "data": summary_data
            }
            
            self.logger.info(f"Daily summary: {summary_data.get('total_trades', 0)} trades, PnL: ${summary_data.get('total_pnl', 0):.2f}")
            self.trade_logger.info(json.dumps(summary_record, indent=2))
            
        except Exception as e:
            self.error_logger.error(f"Error logging daily summary: {e}")
    
    def _save_trade_to_json(self, trade_record: Dict[str, Any]):
        """Сохраняет сделку в JSON файл"""
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            trades_file = self.log_dir / f"trades_{date_str}.json"
            
            trades = []
            if trades_file.exists():
                with open(trades_file, 'r') as f:
                    trades = json.load(f)
            
            trades.append(trade_record)
            
            with open(trades_file, 'w') as f:
                json.dump(trades, f, indent=2)
                
        except Exception as e:
            self.error_logger.error(f"Error saving trade to JSON: {e}")
    
    def _save_error_to_json(self, error_record: Dict[str, Any]):
        """Сохраняет ошибку в JSON файл"""
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            errors_file = self.log_dir / f"errors_{date_str}.json"
            
            errors = []
            if errors_file.exists():
                with open(errors_file, 'r') as f:
                    errors = json.load(f)
            
            errors.append(error_record)
            
            with open(errors_file, 'w') as f:
                json.dump(errors, f, indent=2)
                
        except Exception as e:
            print(f"Critical error saving error to JSON: {e}")
    
    def _get_traceback(self, error: Exception) -> str:
        """Получает traceback ошибки"""
        import traceback
        try:
            return ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        except:
            return str(error)
    
    def get_trades_for_date(self, date_str: str) -> list:
        """Получает все сделки за определенную дату"""
        try:
            trades_file = self.log_dir / f"trades_{date_str}.json"
            if trades_file.exists():
                with open(trades_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.error_logger.error(f"Error reading trades for date {date_str}: {e}")
            return []
    
    def get_errors_for_date(self, date_str: str) -> list:
        """Получает все ошибки за определенную дату"""
        try:
            errors_file = self.log_dir / f"errors_{date_str}.json"
            if errors_file.exists():
                with open(errors_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.error_logger.error(f"Error reading errors for date {date_str}: {e}")
            return []
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Очищает старые логи"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date:
                    log_file.unlink()
                    self.logger.info(f"Removed old log file: {log_file}")
            
            for json_file in self.log_dir.glob("*.json"):
                if json_file.stat().st_mtime < cutoff_date:
                    json_file.unlink()
                    self.logger.info(f"Removed old JSON file: {json_file}")
                    
        except Exception as e:
            self.error_logger.error(f"Error cleaning up old logs: {e}")

# Глобальный экземпляр логгера
trading_logger = TradingLogger()
