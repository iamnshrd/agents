#!/usr/bin/env python3
"""
Улучшенный Dry-Run трейдер с интеграцией Tavily MCP
Использует MCP сервер вместо прямых API вызовов
"""

import os
import sys
import random
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_DOWN
from difflib import SequenceMatcher

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDryRunTrader:
    """
    Улучшенный трейдер с интеграцией Tavily MCP
    Использует MCP сервер для анализа рынков и новостей
    """
    
    def __init__(self):
        """Инициализация улучшенного трейдера"""
        try:
            # Импортируем необходимые модули
            from agents.utils.trading_config import trading_config
            from agents.connectors.telegram import TelegramAlertsSync
            from agents.connectors.tavily_mcp import TavilyMCPSync
            from agents.utils.trading_logger import trading_logger
            
            self.config = trading_config
            self.telegram = TelegramAlertsSync()
            self.tavily = TavilyMCPSync()
            self.logger = trading_logger
            
            # Статистика торговли
            self.daily_stats = {
                "total_trades": 0,
                "total_pnl": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
                "start_time": datetime.now(),
                "positions": [],
                "market_analysis": [],
                "news_analysis": []
            }
            
            # Проверяем доступность MCP
            self._check_mcp_availability()
            
            # Логируем инициализацию
            self.logger.log_performance({
                "action": "enhanced_trader_initialized",
                "trading_mode": self.config.trading_mode,
                "tavily_available": self.config.is_tavily_available(),
                "mcp_config": self.config.get_tavily_config()
            })
            
            logger.info(f"EnhancedDryRunTrader initialized in {self.config.trading_mode} mode")
            logger.info(f"Tavily MCP available: {self.config.is_tavily_available()}")
            
            # Отправляем уведомление о запуске (только если явно разрешено)
            try:
                if os.getenv("TELEGRAM_STARTUP_ALERTS", "false").lower() == "true":
                    self._send_startup_notification()
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Error initializing EnhancedDryRunTrader: {e}")
            raise

    def _find_best_market_match(self, query: str) -> Optional[Dict[str, Any]]:
        """Поиск наиболее похожего рынка по тексту вопроса через Gamma API.
        Возвращает dict с полями question, slug, id при успехе.
        """
        try:
            from agents.polymarket.gamma import GammaMarketClient
            client = GammaMarketClient()
            # Забираем батч активных рынков и ищем лучшую текстовую схожесть
            candidates = client.get_all_current_markets(limit=200)
            if not candidates:
                return None
            best = None
            best_score = 0.0
            qlow = (query or "").lower()
            for m in candidates:
                question = (m.get("question") or "").lower()
                if not question:
                    continue
                score = SequenceMatcher(None, qlow, question).ratio()
                if score > best_score:
                    best_score = score
                    best = m
            if best and best_score >= 0.5:
                return {
                    "id": best.get("id"),
                    "question": best.get("question"),
                    "slug": best.get("slug"),
                }
        except Exception as _:
            return None
        return None
    
    def _check_mcp_availability(self):
        """Проверяет доступность MCP сервера"""
        try:
            if self.config.is_tavily_available():
                status = self.tavily.health_check()
                logger.info(f"Tavily MCP status: {status}")
                
                if not status.get("api_key_configured"):
                    logger.warning("Tavily API key not configured - MCP features will be limited")
            else:
                logger.warning("Tavily MCP not available - using fallback mode")
                
        except Exception as e:
            logger.error(f"Error checking MCP availability: {e}")
    
    def _send_startup_notification(self):
        """Отправляет уведомление о запуске"""
        try:
            startup_data = {
                "event_title": "Enhanced Trading Bot Startup",
                "market_question": "Bot initialized with MCP integration",
                "side": "INFO",
                "price": 0.0,
                "size": 0.0,
                "confidence": 1.0,
                "timestamp": datetime.now().isoformat()
            }
            
            self.telegram.send_trade_alert(startup_data)
            logger.info("Startup notification sent to Telegram")
            
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    def analyze_market_with_mcp(self, market_query: str) -> Dict[str, Any]:
        """
        Анализирует рынок с помощью Tavily MCP
        
        Args:
            market_query: Запрос для анализа рынка
        
        Returns:
            Результаты анализа
        """
        try:
            if not self.config.is_tavily_available():
                logger.warning("Tavily MCP not available for market analysis")
                return self._fallback_market_analysis(market_query)
            
            logger.info(f"Analyzing market with MCP: {market_query}")
            
            # Поиск информации о рынке (синхронная обертка)
            search_results = self.tavily.search_markets(market_query, "advanced")
            
            if not search_results:
                logger.warning("No search results from MCP")
                return self._fallback_market_analysis(market_query)
            
            # Извлекаем данные с найденных страниц
            market_data = {}
            for result in search_results[:3]:  # Анализируем топ-3 результата
                url = result.get("url")
                if url:
                    extracted_data = self.tavily.extract_market_data(url)
                    if extracted_data:
                        market_data.update(extracted_data)
            
            # Анализируем настроения
            sentiment = self.tavily.analyze_market_sentiment(market_data)
            
            # Получаем новости от The Verge News MCP
            from agents.connectors.verge_news_mcp import VergeNewsMCPSync
            verge_news = VergeNewsMCPSync()
            
            # Ищем новости по ключевым словам (синхронная обертка)
            keywords = market_query.split()[:3]  # Берем первые 3 слова
            news = verge_news.search_news(" ".join(keywords), days_back=7)

            # Дополнительно: подтягиваем топ‑новости из локального RAG (без отправки в Telegram)
            rag_news = []
            try:
                from agents.connectors.news_rag import NewsRAG
                newsrag = NewsRAG()
                rag_hits = newsrag.query_news(market_query, top_k=3)
                for meta, _ in rag_hits:
                    title = (meta.get("title") or "No title").strip()
                    url = meta.get("url") or ""
                    rag_news.append({"title": title, "url": url})
            except Exception as _e:
                pass
            
            # Попытка резолвинга точного вопроса и URL рынка через Gamma
            gamma_match = self._find_best_market_match(market_query)
            if gamma_match:
                market_data["market_title"] = gamma_match.get("question") or market_data.get("market_title")
                slug = gamma_match.get("slug")
                if slug:
                    market_data["market_url"] = f"https://polymarket.com/event/{slug}"

            # Формируем результат анализа
            analysis_result = {
                "query": market_query,
                "search_results": len(search_results),
                "market_data": market_data,
                "sentiment_analysis": sentiment,
                "news_count": len(news),
                "rag_news_count": len(rag_news),
                "rag_news": rag_news,
                "analysis_timestamp": datetime.now().isoformat(),
                "mcp_source": "tavily"
            }
            
            # Логируем анализ
            self.logger.log_performance({
                "action": "market_analysis_completed",
                "query": market_query,
                "results_count": len(search_results),
                "sentiment_score": sentiment.get("overall_sentiment", 0.5)
            })
            
            # Сохраняем в статистику
            self.daily_stats["market_analysis"].append(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in market analysis with MCP: {e}")
            return self._fallback_market_analysis(market_query)
    
    def _fallback_market_analysis(self, market_query: str) -> Dict[str, Any]:
        """Fallback анализ рынка без MCP"""
        logger.info(f"Using fallback market analysis for: {market_query}")
        
        # Пытаемся получить новости от The Verge News MCP даже в fallback режиме
        news_count = 0
        rag_news = []
        try:
            from agents.connectors.verge_news_mcp import VergeNewsMCPSync
            verge_news = VergeNewsMCPSync()
            keywords = market_query.split()[:3]
            news = verge_news.search_news(" ".join(keywords), days_back=7)
            news_count = len(news)
            logger.info(f"Fallback: Retrieved {news_count} news items from The Verge")
        except Exception as e:
            logger.warning(f"Fallback: Could not get news from The Verge: {e}")
        # Пробуем RAG локально
        try:
            from agents.connectors.news_rag import NewsRAG
            newsrag = NewsRAG()
            rag_hits = newsrag.query_news(market_query, top_k=3)
            for meta, _ in rag_hits:
                title = (meta.get("title") or "No title").strip()
                url = meta.get("url") or ""
                rag_news.append({"title": title, "url": url})
        except Exception:
            pass

        # Попытка резолвинга точного вопроса и URL через Gamma
        market_url = None
        market_title = f"Market: {market_query}"
        gamma_match = self._find_best_market_match(market_query)
        if gamma_match:
            market_title = gamma_match.get("question") or market_title
            slug = gamma_match.get("slug")
            if slug:
                market_url = f"https://polymarket.com/event/{slug}"
        
        return {
            "query": market_query,
            "market_data": {
                "market_title": market_title,
                "current_price": random.uniform(0.3, 0.7),
                "total_volume": random.randint(5000, 50000),
                "participants": random.randint(500, 5000),
                "market_url": market_url or f"https://polymarket.com/event/{market_query.lower().replace(' ', '-')}"
            },
            "sentiment_analysis": {
                "overall_sentiment": random.uniform(0.3, 0.7),
                "confidence": 0.6
            },
            "analysis_timestamp": datetime.now().isoformat(),
            "mcp_source": "fallback",
            "news_count": news_count,
            "rag_news_count": len(rag_news),
            "rag_news": rag_news
        }
    
    def generate_enhanced_trade_signal(self, market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерирует торговый сигнал на основе анализа MCP
        
        Args:
            market_analysis: Результаты анализа рынка
        
        Returns:
            Торговый сигнал
        """
        try:
            market_data = market_analysis.get("market_data", {})
            sentiment = market_analysis.get("sentiment_analysis", {})
            
            # Анализируем настроения для принятия решения
            sentiment_score = sentiment.get("overall_sentiment", 0.5)
            confidence = sentiment.get("confidence", 0.6)
            
            # Определяем сторону торговли на основе настроений
            if sentiment_score > 0.6:
                side = "BUY"
                price = random.uniform(0.4, 0.8)
            elif sentiment_score < 0.4:
                side = "SELL"
                price = random.uniform(0.2, 0.6)
            else:
                # Нейтральные настроения - случайная сторона
                side = random.choice(["BUY", "SELL"])
                price = random.uniform(0.3, 0.7)
            
            # Рассчитываем размер позиции на основе уверенности
            position_size = self.config.calculate_position_size(confidence)
            
            # Определяем заголовок и URL рынка
            title = market_data.get("question") or market_data.get("market_title", "Unknown Market")
            market_url = market_data.get("market_url", "")

            # Формируем торговый сигнал
            trade_signal = {
                "event_title": title,
                "market_question": title,
                "side": side,
                "price": round(price, 3),
                "size": float(position_size),
                "confidence": confidence,
                "sentiment_score": sentiment_score,
                "timestamp": datetime.now().isoformat(),
                "analysis_source": market_analysis.get("mcp_source", "unknown"),
                "news_count": market_analysis.get("news_count", 0),
                "market_url": market_url
            }
            
            logger.info(f"Generated enhanced trade signal: {trade_signal['event_title']}")
            return trade_signal
            
        except Exception as e:
            logger.error(f"Error generating enhanced trade signal: {e}")
            return self._generate_fallback_signal()
    
    def _generate_fallback_signal(self) -> Dict[str, Any]:
        """Генерирует fallback торговый сигнал"""
        events = [
            "Will AI pass the Turing test in 2024?",
            "Will SpaceX land on Mars in 2024?",
            "Will Tesla deliver 2M+ vehicles in 2024?",
            "Will Bitcoin reach $100k in 2024?",
            "Will GPT-5 be released in 2024?"
        ]
        
        return {
            "event_title": random.choice(events),
            "market_question": "Will the prediction come true?",
            "side": random.choice(["BUY", "SELL"]),
            "price": round(random.uniform(0.2, 0.8), 3),
            "size": random.uniform(0.05, 0.15),
            "confidence": random.uniform(0.6, 0.9),
            "sentiment_score": random.uniform(0.3, 0.7),
            "timestamp": datetime.now().isoformat(),
            "analysis_source": "fallback",
            "news_count": 0,
            "market_url": "https://polymarket.com/event/example"
        }
    
    def execute_enhanced_trade(self) -> Dict[str, Any]:
        """
        Выполняет улучшенную торговую операцию с MCP анализом
        """
        try:
            logger.info("Starting enhanced trade execution with MCP...")
            
            # Генерируем запрос для анализа
            market_queries = [
                "AI technology predictions 2024",
                "Space exploration milestones 2024",
                "Electric vehicle market trends 2024",
                "Cryptocurrency market analysis 2024",
                "Tech company earnings predictions 2024"
            ]
            
            query = random.choice(market_queries)
            
            # Анализируем рынок с помощью MCP (синхронно)
            market_analysis = self.analyze_market_with_mcp(query)
            
            # Генерируем торговый сигнал
            trade_signal = self.generate_enhanced_trade_signal(market_analysis)
            
            # Отправляем алерт о сигнале
            self._send_trade_alert(trade_signal)
            
            # Логируем сигнал
            self.logger.log_trade(trade_signal, "enhanced_signal")
            
            # Симулируем исполнение
            trade_result = self._simulate_trade_execution(trade_signal)
            
            # Обновляем статистику
            self._update_trading_stats(trade_result)
            
            # Отправляем алерт о результате
            self._send_position_alert(trade_result)
            
            # Логируем исполнение
            self.logger.log_trade(trade_result, "enhanced_execution")
            
            logger.info("Enhanced trade completed successfully!")
            return trade_result
            
        except Exception as e:
            logger.error(f"Error in enhanced trade execution: {e}")
            self.logger.log_error(e, "enhanced_trade_execution")
            
            # Отправляем алерт об ошибке
            self._send_risk_alert({
                "risk_level": "HIGH",
                "description": f"Enhanced trading error: {str(e)}",
                "potential_loss": 0
            })
            
            return {}

    def execute_enhanced_trade_on_query(self, query: str) -> Dict[str, Any]:
        """
        Выполняет улучшенную торговую операцию по заданному рыночному запросу
        """
        try:
            logger.info("Starting enhanced trade execution with MCP (on query)...")
            market_analysis = self.analyze_market_with_mcp(query)
            trade_signal = self.generate_enhanced_trade_signal(market_analysis)
            self._send_trade_alert(trade_signal)
            self.logger.log_trade(trade_signal, "enhanced_signal")
            trade_result = self._simulate_trade_execution(trade_signal)
            self._update_trading_stats(trade_result)
            self._send_position_alert(trade_result)
            self.logger.log_trade(trade_result, "enhanced_execution")
            logger.info("Enhanced trade (on query) completed successfully!")
            return trade_result
        except Exception as e:
            logger.error(f"Error in enhanced trade execution (on query): {e}")
            self.logger.log_error(e, "enhanced_trade_execution_on_query")
            self._send_risk_alert({
                "risk_level": "HIGH",
                "description": f"Enhanced trading error (on query): {str(e)}",
                "potential_loss": 0
            })
            return {}
    
    def _simulate_trade_execution(self, trade_signal: Dict[str, Any]) -> Dict[str, Any]:
        """Симулирует исполнение торговой операции"""
        try:
            # Симулируем изменение цены на основе настроений
            sentiment_score = trade_signal.get("sentiment_score", 0.5)
            base_price = trade_signal.get("price", 0.5)
            
            # Настроения влияют на направление изменения цены
            if trade_signal.get("side") == "BUY":
                # Покупка: позитивные настроения = рост цены
                price_change = random.uniform(-0.1, 0.2) * sentiment_score
            else:
                # Продажа: негативные настроения = падение цены
                price_change = random.uniform(-0.2, 0.1) * (1 - sentiment_score)
            
            new_price = max(0.01, min(0.99, base_price + price_change))
            
            # Рассчитываем PnL
            position_value = float(trade_signal.get("size", 0)) * float(self.config.get_available_balance())
            pnl = position_value * price_change
            
            # Формируем результат
            trade_result = {
                "event_title": trade_signal.get("event_title"),
                "side": trade_signal.get("side"),
                "entry_price": base_price,
                "exit_price": new_price,
                "price_change": price_change,
                "size": trade_signal.get("size"),
                "pnl": pnl,
                "sentiment_score": sentiment_score,
                "analysis_source": trade_signal.get("analysis_source"),
                "execution_time": datetime.now().isoformat(),
                "trade_id": f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "market_url": trade_signal.get("market_url", "")
            }
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error simulating trade execution: {e}")
            return {}
    
    def _send_trade_alert(self, trade_data: Dict[str, Any]):
        """Отправляет алерт о торговой операции"""
        try:
            self.telegram.send_trade_alert(trade_data)
            logger.info("Enhanced trade alert sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send enhanced trade alert: {e}")
    
    def _send_position_alert(self, position_data: Dict[str, Any]):
        """Отправляет алерт о позиции"""
        try:
            self.telegram.send_position_alert(position_data)
            logger.info("Enhanced position alert sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send enhanced position alert: {e}")
    
    def _send_risk_alert(self, risk_data: Dict[str, Any]):
        """Отправляет алерт о рисках"""
        try:
            self.telegram.send_risk_alert(risk_data)
            logger.info("Enhanced risk alert sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send enhanced risk alert: {e}")
    
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
        
        logger.info(f"Updated enhanced stats: {self.daily_stats}")
    
    def get_enhanced_summary(self) -> Dict[str, Any]:
        """Возвращает расширенную сводку торговли"""
        if self.daily_stats["total_trades"] == 0:
            return {"message": "No enhanced trades executed today"}
        
        win_rate = self.daily_stats["winning_trades"] / self.daily_stats["total_trades"]
        
        # Анализируем источники анализа
        mcp_sources = [pos.get("analysis_source") for pos in self.daily_stats["positions"]]
        mcp_trades = mcp_sources.count("tavily")
        fallback_trades = mcp_sources.count("fallback")
        
        summary = {
            "total_trades": self.daily_stats["total_trades"],
            "total_pnl": self.daily_stats["total_pnl"],
            "winning_trades": self.daily_stats["winning_trades"],
            "losing_trades": self.daily_stats["losing_trades"],
            "win_rate": win_rate,
            "mcp_analysis_trades": mcp_trades,
            "fallback_trades": fallback_trades,
            "market_analysis_count": len(self.daily_stats["market_analysis"]),
            "start_time": self.daily_stats["start_time"].isoformat(),
            "end_time": datetime.now().isoformat()
        }
        
        return summary
    
    def send_enhanced_summary(self):
        """Отправляет расширенную сводку в Telegram"""
        try:
            summary = self.get_enhanced_summary()
            self.telegram.send_daily_summary(summary)
            
            # Логируем сводку
            self.logger.log_daily_summary(summary)
            
            logger.info("Enhanced daily summary sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send enhanced daily summary: {e}")
            self.logger.log_error(e, "send_enhanced_summary")
    
    def run_enhanced_session(self, num_trades: int = 3):
        """
        Запускает расширенную торговую сессию
        
        Args:
            num_trades: Количество сделок для выполнения
        """
        try:
            logger.info(f"Starting enhanced trading session with {num_trades} trades...")
            
            for i in range(num_trades):
                logger.info(f"Executing enhanced trade {i+1}/{num_trades}")
                
                # Выполняем торговую операцию (синхронно)
                trade_result = self.execute_enhanced_trade()
                
                if trade_result:
                    logger.info(f"Enhanced trade {i+1} completed: {trade_result.get('event_title')}")
                else:
                    logger.warning(f"Enhanced trade {i+1} failed")
                
                # Небольшая пауза между сделками
                if i < num_trades - 1:
                    time.sleep(2)
            
            # Отправляем итоговую сводку
            self.send_enhanced_summary()
            
            logger.info("Enhanced trading session completed!")
            
        except Exception as e:
            logger.error(f"Error in enhanced trading session: {e}")
            self.logger.log_error(e, "enhanced_trading_session")

# Синхронная обертка для совместимости
class EnhancedDryRunTraderSync:
    """Синхронная обертка для EnhancedDryRunTrader (без event loop)"""
    def __init__(self):
        self.trader = EnhancedDryRunTrader()

    def execute_enhanced_trade(self) -> Dict[str, Any]:
        return self.trader.execute_enhanced_trade()

    def run_enhanced_session(self, num_trades: int = 3):
        self.trader.run_enhanced_session(num_trades)

    def get_enhanced_summary(self) -> Dict[str, Any]:
        return self.trader.get_enhanced_summary()

    def send_enhanced_summary(self):
        self.trader.send_enhanced_summary()

    def execute_enhanced_trade_on_query(self, query: str) -> Dict[str, Any]:
        return self.trader.execute_enhanced_trade_on_query(query)

if __name__ == "__main__":
    """Демонстрация работы улучшенного трейдера"""
    try:
        # Создаем синхронную версию
        trader = EnhancedDryRunTraderSync()
        
        # Выполняем демонстрационную сессию
        print("🚀 Запуск улучшенного Dry-Run трейдера с MCP интеграцией...")
        trader.run_enhanced_session(3)
        
        # Показываем результаты
        summary = trader.get_enhanced_summary()
        print(f"\n📊 Результаты сессии:")
        print(f"Всего сделок: {summary.get('total_trades', 0)}")
        print(f"Общий PnL: ${summary.get('total_pnl', 0):.2f}")
        print(f"MCP анализ: {summary.get('mcp_analysis_trades', 0)} сделок")
        print(f"Fallback: {summary.get('fallback_trades', 0)} сделок")
        
    except Exception as e:
        print(f"❌ Ошибка в демонстрации: {e}")
        import traceback
        traceback.print_exc()
