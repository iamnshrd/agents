import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import statistics

class PerformanceAnalyzer:
    """
    Анализатор производительности торговли
    """
    
    def __init__(self, logs_dir: str = "./logs"):
        self.logs_dir = Path(logs_dir)
        self.trading_logger = None
        
        # Импортируем логгер если доступен
        try:
            from agents.utils.trading_logger import trading_logger
            self.trading_logger = trading_logger
        except ImportError:
            pass
    
    def analyze_daily_performance(self, date_str: str) -> Dict[str, Any]:
        """
        Анализирует производительность за определенный день
        
        Args:
            date_str: Дата в формате YYYY-MM-DD
        
        Returns:
            Словарь с метриками производительности
        """
        try:
            trades_file = self.logs_dir / f"trades_{date_str}.json"
            
            if not trades_file.exists():
                return {
                    "date": date_str,
                    "total_trades": 0,
                    "message": "No trades found for this date"
                }
            
            with open(trades_file, 'r') as f:
                trades = json.load(f)
            
            return self._calculate_performance_metrics(trades, date_str)
            
        except Exception as e:
            if self.trading_logger:
                self.trading_logger.log_error(e, f"analyze_daily_performance for {date_str}")
            return {
                "date": date_str,
                "error": str(e)
            }
    
    def analyze_period_performance(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Анализирует производительность за период
        
        Args:
            start_date: Начальная дата YYYY-MM-DD
            end_date: Конечная дата YYYY-MM-DD
        
        Returns:
            Словарь с метриками за период
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            all_trades = []
            current_date = start
            
            while current_date <= end:
                date_str = current_date.strftime("%Y-%m-%d")
                trades_file = self.logs_dir / f"trades_{date_str}.json"
                
                if trades_file.exists():
                    with open(trades_file, 'r') as f:
                        daily_trades = json.load(f)
                        all_trades.extend(daily_trades)
                
                current_date += timedelta(days=1)
            
            return self._calculate_performance_metrics(all_trades, f"{start_date} to {end_date}")
            
        except Exception as e:
            if self.trading_logger:
                self.trading_logger.log_error(e, f"analyze_period_performance {start_date} to {end_date}")
            return {
                "period": f"{start_date} to {end_date}",
                "error": str(e)
            }
    
    def _calculate_performance_metrics(self, trades: List[Dict], period_name: str) -> Dict[str, Any]:
        """Вычисляет метрики производительности"""
        if not trades:
            return {
                "period": period_name,
                "total_trades": 0,
                "message": "No trades found"
            }
        
        # Фильтруем только исполненные сделки
        executed_trades = [t for t in trades if t.get("type") == "execution"]
        
        if not executed_trades:
            return {
                "period": period_name,
                "total_trades": 0,
                "message": "No executed trades found"
            }
        
        # Извлекаем данные о PnL
        pnl_values = []
        trade_sizes = []
        winning_trades = 0
        losing_trades = 0
        
        for trade in executed_trades:
            trade_data = trade.get("data", {})
            pnl = trade_data.get("pnl", 0)
            size = trade_data.get("size", 0)
            
            if isinstance(pnl, (int, float)):
                pnl_values.append(pnl)
                trade_sizes.append(size)
                
                if pnl > 0:
                    winning_trades += 1
                elif pnl < 0:
                    losing_trades += 1
        
        if not pnl_values:
            return {
                "period": period_name,
                "total_trades": len(executed_trades),
                "message": "No valid PnL data found"
            }
        
        # Вычисляем метрики
        total_trades = len(pnl_values)
        total_pnl = sum(pnl_values)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Средние значения
        avg_pnl = statistics.mean(pnl_values)
        avg_trade_size = statistics.mean(trade_sizes) if trade_sizes else 0
        
        # Волатильность
        pnl_volatility = statistics.stdev(pnl_values) if len(pnl_values) > 1 else 0
        
        # Максимальные значения
        max_profit = max(pnl_values)
        max_loss = min(pnl_values)
        
        # Процентные изменения
        if avg_trade_size > 0:
            avg_pnl_percentage = (avg_pnl / avg_trade_size) * 100
        else:
            avg_pnl_percentage = 0
        
        # Sharpe ratio (упрощенный)
        sharpe_ratio = 0
        if pnl_volatility > 0:
            sharpe_ratio = avg_pnl / pnl_volatility
        
        # Максимальная просадка
        max_drawdown = self._calculate_max_drawdown(pnl_values)
        
        # Консистентность
        consistency_score = self._calculate_consistency_score(pnl_values)
        
        return {
            "period": period_name,
            "total_trades": total_trades,
            "total_pnl": round(total_pnl, 4),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate * 100, 2),
            "avg_pnl": round(avg_pnl, 4),
            "avg_trade_size": round(avg_trade_size, 4),
            "avg_pnl_percentage": round(avg_pnl_percentage, 2),
            "pnl_volatility": round(pnl_volatility, 4),
            "max_profit": round(max_profit, 4),
            "max_loss": round(max_loss, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "max_drawdown": round(max_drawdown, 4),
            "consistency_score": round(consistency_score, 2),
            "risk_metrics": {
                "profit_factor": abs(max_profit / max_loss) if max_loss != 0 else float('inf'),
                "risk_reward_ratio": abs(avg_pnl / pnl_volatility) if pnl_volatility > 0 else 0,
                "calmar_ratio": abs(avg_pnl / max_drawdown) if max_drawdown != 0 else 0
            }
        }
    
    def _calculate_max_drawdown(self, pnl_values: List[float]) -> float:
        """Вычисляет максимальную просадку"""
        if not pnl_values:
            return 0
        
        peak = pnl_values[0]
        max_dd = 0
        
        for pnl in pnl_values:
            if pnl > peak:
                peak = pnl
            dd = peak - pnl
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_consistency_score(self, pnl_values: List[float]) -> float:
        """Вычисляет оценку консистентности"""
        if len(pnl_values) < 2:
            return 100
        
        # Вычисляем стандартное отклонение от среднего
        mean_pnl = statistics.mean(pnl_values)
        deviations = [abs(pnl - mean_pnl) for pnl in pnl_values]
        avg_deviation = statistics.mean(deviations)
        
        # Нормализуем к шкале 0-100
        if avg_deviation == 0:
            return 100
        
        # Меньше отклонение = выше консистентность
        consistency = max(0, 100 - (avg_deviation * 10))
        return consistency
    
    def generate_performance_report(self, date_str: str) -> str:
        """
        Генерирует текстовый отчет о производительности
        
        Args:
            date_str: Дата в формате YYYY-MM-DD
        
        Returns:
            Форматированный отчет
        """
        metrics = self.analyze_daily_performance(date_str)
        
        if "error" in metrics or "message" in metrics:
            return f"📊 Отчет за {date_str}\n\n{metrics.get('message', metrics.get('error', 'Нет данных'))}"
        
        report = f"""
📊 ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ
📅 Дата: {date_str}

🎯 ОБЩАЯ СТАТИСТИКА
• Всего сделок: {metrics['total_trades']}
• Прибыльных: {metrics['winning_trades']}
• Убыточных: {metrics['losing_trades']}
• Процент успешных: {metrics['win_rate']}%

💰 PnL АНАЛИЗ
• Общий PnL: ${metrics['total_pnl']:.2f}
• Средний PnL: ${metrics['avg_pnl']:.2f}
• Макс. прибыль: ${metrics['max_profit']:.2f}
• Макс. убыток: ${metrics['max_loss']:.2f}

📏 РАЗМЕРЫ ПОЗИЦИЙ
• Средний размер: {metrics['avg_trade_size']:.1%}
• Средний PnL %: {metrics['avg_pnl_percentage']:.1f}%

📈 РИСК-МЕТРИКИ
• Волатильность PnL: ${metrics['pnl_volatility']:.4f}
• Коэффициент Шарпа: {metrics['sharpe_ratio']:.4f}
• Макс. просадка: ${metrics['max_drawdown']:.4f}
• Консистентность: {metrics['consistency_score']:.1f}/100

⚖️ ДОПОЛНИТЕЛЬНЫЕ МЕТРИКИ
• Profit Factor: {metrics['risk_metrics']['profit_factor']:.2f}
• Risk/Reward: {metrics['risk_metrics']['risk_reward_ratio']:.2f}
• Calmar Ratio: {metrics['risk_metrics']['calmar_ratio']:.2f}
        """
        
        return report.strip()
    
    def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Получает краткую сводку производительности за последние дни
        
        Args:
            days: Количество дней для анализа
        
        Returns:
            Словарь с краткой сводкой
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            return self.analyze_period_performance(start_str, end_str)
            
        except Exception as e:
            if self.trading_logger:
                self.trading_logger.log_error(e, f"get_performance_summary for {days} days")
            return {
                "error": str(e),
                "period": f"Last {days} days"
            }
    
    def export_performance_data(self, start_date: str, end_date: str, filename: str = None) -> str:
        """
        Экспортирует данные о производительности в JSON файл
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            filename: Имя файла (опционально)
        
        Returns:
            Путь к экспортированному файлу
        """
        try:
            if not filename:
                filename = f"performance_{start_date}_to_{end_date}.json"
            
            export_path = self.logs_dir / filename
            
            # Получаем данные
            performance_data = self.analyze_period_performance(start_date, end_date)
            
            # Добавляем метаданные
            export_data = {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "period_start": start_date,
                    "period_end": end_date,
                    "version": "1.0"
                },
                "performance_metrics": performance_data
            }
            
            # Экспортируем
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return str(export_path)
            
        except Exception as e:
            if self.trading_logger:
                self.trading_logger.log_error(e, f"export_performance_data {start_date} to {end_date}")
            raise

# Глобальный экземпляр анализатора
performance_analyzer = PerformanceAnalyzer()
