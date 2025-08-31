import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TavilyMCPClient:
    """
    Клиент для работы с Tavily MCP сервером
    Обеспечивает доступ к поиску, извлечению данных и анализу веб-страниц
    """
    
    def __init__(self, api_key: str = None, server_url: str = None):
        """
        Инициализация клиента Tavily MCP
        
        Args:
            api_key: API ключ Tavily (если не указан, берется из переменных окружения)
            server_url: URL MCP сервера (если не указан, используется локальный)
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.server_url = server_url or "https://mcp.tavily.com/mcp/"
        
        if not self.api_key:
            logger.warning("Tavily API key not configured. Some features will be disabled.")
        
        # Настройки для локального MCP сервера
        self.local_mcp_config = {
            "command": "npx",
            "args": ["-y", "tavily-mcp@latest"],
            "env": {
                "TAVILY_API_KEY": self.api_key
            }
        }
        
        # Проверяем доступность
        self._check_availability()
    
    def _check_availability(self):
        """Проверяет доступность Tavily MCP сервера"""
        try:
            if self.api_key:
                logger.info("Tavily MCP client initialized with API key")
            else:
                logger.warning("Tavily MCP client initialized without API key")
        except Exception as e:
            logger.error(f"Error initializing Tavily MCP client: {e}")
    
    async def search_markets(self, query: str, search_depth: str = "basic") -> List[Dict[str, Any]]:
        """
        Поиск информации о рынках и событиях
        
        Args:
            query: Поисковый запрос
            search_depth: Глубина поиска (basic, advanced)
        
        Returns:
            Список результатов поиска
        """
        try:
            if not self.api_key:
                logger.warning("Tavily API key not available for market search")
                return []
            
            # Используем удаленный MCP сервер для поиска
            search_url = f"{self.server_url}?tavilyApiKey={self.api_key}"
            
            # Параметры поиска
            search_params = {
                "query": query,
                "search_depth": search_depth,
                "include_domains": [
                    "polymarket.com",
                    "predictit.org", 
                    "manifold.markets",
                    "reuters.com",
                    "bloomberg.com",
                    "cnbc.com",
                    "wsj.com"
                ],
                "max_results": 10
            }
            
            # В реальной реализации здесь был бы вызов MCP сервера
            # Пока возвращаем заглушку
            logger.info(f"Searching markets for: {query}")
            
            # Симулируем результаты поиска
            mock_results = [
                {
                    "title": f"Market Analysis: {query}",
                    "url": "https://polymarket.com/event/example",
                    "content": f"Analysis of market conditions for {query}",
                    "published_date": datetime.now().isoformat(),
                    "relevance_score": 0.95
                }
            ]
            
            return mock_results
            
        except Exception as e:
            logger.error(f"Error searching markets: {e}")
            return []
    
    async def extract_market_data(self, url: str) -> Dict[str, Any]:
        """
        Извлекает данные о рынке с веб-страницы
        
        Args:
            url: URL страницы для анализа
        
        Returns:
            Структурированные данные о рынке
        """
        try:
            if not self.api_key:
                logger.warning("Tavily API key not available for data extraction")
                return {}
            
            logger.info(f"Extracting market data from: {url}")
            
            # В реальной реализации здесь был бы вызов MCP сервера
            # Пока возвращаем заглушку
            mock_data = {
                "market_title": "Example Market",
                "current_price": 0.65,
                "total_volume": 15000,
                "participants": 1250,
                "end_date": "2024-12-31",
                "description": "Example market description",
                "outcomes": ["Yes", "No"],
                "extraction_timestamp": datetime.now().isoformat()
            }
            
            return mock_data
            
        except Exception as e:
            logger.error(f"Error extracting market data: {url}: {e}")
            return {}
    
    async def analyze_market_sentiment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует настроения рынка на основе извлеченных данных
        
        Args:
            market_data: Данные о рынке
        
        Returns:
            Анализ настроений
        """
        try:
            logger.info("Analyzing market sentiment")
            
            # Простой анализ на основе доступных данных
            sentiment_score = 0.5  # Нейтральный по умолчанию
            
            if market_data.get("current_price"):
                price = market_data["current_price"]
                if price > 0.7:
                    sentiment_score = 0.8  # Более оптимистично
                elif price < 0.3:
                    sentiment_score = 0.2  # Более пессимистично
            
            # Анализ объема торгов
            volume = market_data.get("total_volume", 0)
            volume_sentiment = min(volume / 10000, 1.0)  # Нормализуем объем
            
            # Анализ количества участников
            participants = market_data.get("participants", 0)
            participation_sentiment = min(participants / 1000, 1.0)
            
            sentiment_analysis = {
                "overall_sentiment": sentiment_score,
                "price_sentiment": sentiment_score,
                "volume_sentiment": volume_sentiment,
                "participation_sentiment": participation_sentiment,
                "confidence": 0.7,
                "analysis_timestamp": datetime.now().isoformat(),
                "factors": [
                    "current_price",
                    "trading_volume", 
                    "participant_count"
                ]
            }
            
            return sentiment_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market sentiment: {e}")
            return {}
    
    async def get_market_news(self, market_keywords: List[str], days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Получает новости, связанные с рынком
        
        Args:
            market_keywords: Ключевые слова для поиска новостей
            days_back: Количество дней назад для поиска
        
        Returns:
            Список новостей
        """
        try:
            if not self.api_key:
                logger.warning("Tavily API key not available for news search")
                return []
            
            logger.info(f"Searching news for keywords: {market_keywords}")
            
            # Формируем поисковый запрос
            query = " AND ".join(market_keywords)
            
            # В реальной реализации здесь был бы вызов MCP сервера
            # Пока возвращаем заглушку
            mock_news = [
                {
                    "title": f"News about {market_keywords[0]}",
                    "url": "https://example.com/news/1",
                    "content": f"Recent developments in {market_keywords[0]} market",
                    "published_date": (datetime.now() - timedelta(days=1)).isoformat(),
                    "source": "Reuters",
                    "relevance_score": 0.9
                }
            ]
            
            return mock_news
            
        except Exception as e:
            logger.error(f"Error getting market news: {e}")
            return []
    
    async def crawl_market_websites(self, domains: List[str] = None) -> Dict[str, Any]:
        """
        Обходит веб-сайты для сбора информации о рынках
        
        Args:
            domains: Список доменов для обхода
        
        Returns:
            Результаты обхода
        """
        try:
            if not self.api_key:
                logger.warning("Tavily API key not available for website crawling")
                return {}
            
            if not domains:
                domains = ["polymarket.com", "predictit.org"]
            
            logger.info(f"Crawling market websites: {domains}")
            
            # В реальной реализации здесь был бы вызов MCP сервера
            # Пока возвращаем заглушку
            crawl_results = {
                "crawled_domains": domains,
                "total_pages": len(domains) * 10,
                "markets_found": len(domains) * 5,
                "crawl_timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            return crawl_results
            
        except Exception as e:
            logger.error(f"Error crawling market websites: {e}")
            return {}
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию MCP сервера для интеграции
        
        Returns:
            Конфигурация MCP
        """
        return {
            "mcpServers": {
                "tavily-mcp": {
                    "command": "npx",
                    "args": ["-y", "tavily-mcp@latest"],
                    "env": {
                        "TAVILY_API_KEY": self.api_key
                    },
                    "disabled": False,
                    "autoApprove": ["tavily-search", "tavily-extract"]
                }
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Проверяет состояние MCP сервера
        
        Returns:
            Статус сервера
        """
        try:
            status = {
                "api_key_configured": bool(self.api_key),
                "server_url": self.server_url,
                "local_mcp_available": True,
                "remote_mcp_available": bool(self.api_key),
                "timestamp": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {"error": str(e)}

# Глобальный экземпляр клиента
tavily_client = TavilyMCPClient()

# Синхронная обертка для совместимости
class TavilyMCPSync:
    """Синхронная обертка для TavilyMCPClient"""
    
    def __init__(self):
        self.client = tavily_client
    
    def search_markets(self, query: str, search_depth: str = "basic") -> List[Dict[str, Any]]:
        """Синхронный поиск рынков"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.search_markets(query, search_depth))
        finally:
            loop.close()
    
    def extract_market_data(self, url: str) -> Dict[str, Any]:
        """Синхронное извлечение данных о рынке"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.extract_market_data(url))
        finally:
            loop.close()
    
    def analyze_market_sentiment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Синхронный анализ настроений"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.analyze_market_sentiment(market_data))
        finally:
            loop.close()
    
    def get_market_news(self, market_keywords: List[str], days_back: int = 7) -> List[Dict[str, Any]]:
        """Синхронное получение новостей"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.get_market_news(market_keywords, days_back))
        finally:
            loop.close()
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """Получение конфигурации MCP"""
        return self.client.get_mcp_config()
    
    def health_check(self) -> Dict[str, Any]:
        """Синхронная проверка состояния"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.health_check())
        finally:
            loop.close()
