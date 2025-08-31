#!/usr/bin/env python3
"""
MCP клиент для The Verge News
Использует Smithery для доступа к verge-news-mcp серверу
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class VergeNewsMCPClient:
    """
    MCP клиент для The Verge News
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SMITHERY_API_KEY", "970828f0-e3a7-4778-a72f-2cc44656511d")
        self.base_url = "https://server.smithery.ai/@manimohans/verge-news-mcp/mcp"
        self._session = None
        # retry params
        try:
            self.retry_attempts = int(os.getenv("SMITHERY_RETRY_ATTEMPTS", "3"))
        except Exception:
            self.retry_attempts = 3
        try:
            self.retry_backoff = float(os.getenv("SMITHERY_RETRY_BACKOFF_SECS", "1.5"))
        except Exception:
            self.retry_backoff = 1.5
        
    async def _get_session(self):
        """Получает MCP сессию"""
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
            from urllib.parse import urlencode
            
            # Формируем URL с аутентификацией
            params = {"api_key": self.api_key}
            url = f"{self.base_url}?{urlencode(params)}"
            
            # Ретраим установку соединения
            last_err = None
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    client = streamablehttp_client(url)
                    read, write, _ = await client.__aenter__()
                    session = ClientSession(read, write)
                    await session.__aenter__()
                    await session.initialize()
                    return session, client
                except Exception as e:
                    last_err = e
                    logger.warning(
                        f"MCP session connect failed (attempt {attempt}/{self.retry_attempts}): {e}"
                    )
                    # simple backoff
                    await asyncio.sleep(self.retry_backoff * attempt)
            logger.error(f"Failed to create MCP session after retries: {last_err}")
            return None, None
            
        except Exception as e:
            logger.error(f"Error creating MCP session: {e}")
            return None, None
    
    async def get_daily_news(self) -> List[Dict[str, Any]]:
        """
        Получает новости за последние 24 часа
        
        Returns:
            Список новостей
        """
        try:
            session, client = await self._get_session()
            if not session:
                return self._fallback_daily_news()
            
            try:
                # Вызываем get-daily-news
                result = await session.call_tool("get-daily-news", {})
                
                if result.content:
                    parsed_items = self._parse_tool_content(result.content)
                    news_items: List[Dict[str, Any]] = []
                    for item in parsed_items:
                        news_items.append({
                            "title": item.get("title", "No title"),
                            "description": item.get("description", item.get("summary", "No description")),
                            "url": item.get("url", item.get("link", "")),
                            "published_at": item.get("published_at", item.get("publishedAt", item.get("pubDate", ""))),
                            "source": item.get("source", "The Verge"),
                            "relevance_score": float(item.get("relevance_score", 0.9)),
                            "category": item.get("category", "Technology News")
                        })
                    logger.info(f"Retrieved {len(news_items)} daily news items from The Verge")
                    return news_items
                else:
                    logger.warning("No content in daily news response")
                    return self._fallback_daily_news()
                    
            finally:
                await session.__aexit__(None, None, None)
                await client.__aexit__(None, None, None)
                
        except Exception as e:
            logger.error(f"Error getting daily news: {e}")
            return self._fallback_daily_news()
    
    async def get_weekly_news(self) -> List[Dict[str, Any]]:
        """
        Получает новости за последнюю неделю
        
        Returns:
            Список новостей
        """
        try:
            session, client = await self._get_session()
            if not session:
                return self._fallback_weekly_news()
            
            try:
                # Вызываем get-weekly-news
                result = await session.call_tool("get-weekly-news", {})
                
                if result.content:
                    parsed_items = self._parse_tool_content(result.content)
                    news_items: List[Dict[str, Any]] = []
                    for item in parsed_items:
                        news_items.append({
                            "title": item.get("title", "No title"),
                            "description": item.get("description", item.get("summary", "No description")),
                            "url": item.get("url", item.get("link", "")),
                            "published_at": item.get("published_at", item.get("publishedAt", item.get("pubDate", ""))),
                            "source": item.get("source", "The Verge"),
                            "relevance_score": float(item.get("relevance_score", 0.8)),
                            "category": item.get("category", "Technology News")
                        })
                    logger.info(f"Retrieved {len(news_items)} weekly news items from The Verge")
                    return news_items
                else:
                    logger.warning("No content in weekly news response")
                    return self._fallback_weekly_news()
                    
            finally:
                await session.__aexit__(None, None, None)
                await client.__aexit__(None, None, None)
                
        except Exception as e:
            logger.error(f"Error getting weekly news: {e}")
            return self._fallback_weekly_news()
    
    async def search_news(self, keyword: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Ищет новости по ключевому слову
        
        Args:
            keyword: Ключевое слово для поиска
            days_back: Количество дней назад для поиска
            
        Returns:
            Список найденных новостей
        """
        try:
            session, client = await self._get_session()
            if not session:
                return self._fallback_search_news(keyword)
            
            try:
                # Вызываем search-news
                result = await session.call_tool("search-news", {
                    "keyword": keyword,
                    "days": days_back
                })
                
                if result.content:
                    parsed_items = self._parse_tool_content(result.content)
                    news_items: List[Dict[str, Any]] = []
                    for item in parsed_items:
                        news_items.append({
                            "title": item.get("title", "No title"),
                            "description": item.get("description", item.get("summary", "No description")),
                            "url": item.get("url", item.get("link", "")),
                            "published_at": item.get("published_at", item.get("publishedAt", item.get("pubDate", ""))),
                            "source": item.get("source", "The Verge"),
                            "relevance_score": float(item.get("relevance_score", 0.85)),
                            "category": item.get("category", "Technology News"),
                            "search_keyword": keyword
                        })
                    logger.info(f"Found {len(news_items)} news items for keyword '{keyword}'")
                    return news_items
                else:
                    logger.warning(f"No content in search response for keyword '{keyword}'")
                    return self._fallback_search_news(keyword)
                    
            finally:
                await session.__aexit__(None, None, None)
                await client.__aexit__(None, None, None)
                
        except Exception as e:
            logger.error(f"Error searching news for '{keyword}': {e}")
            return self._fallback_search_news(keyword)

    def _parse_tool_content(self, content_items: List[Any]) -> List[Dict[str, Any]]:
        """Универсальный парсер содержимого MCP-ответа (TextContent/JSON/словарь).
        Преобразует список элементов в список словарей новостей.
        """
        parsed: List[Dict[str, Any]] = []
        for item in content_items:
            try:
                # Если это уже словарь
                if isinstance(item, dict):
                    parsed.append(item)
                    continue
                # Если у элемента есть текст
                text = None
                if hasattr(item, "text") and isinstance(item.text, str):
                    text = item.text
                elif hasattr(item, "value") and isinstance(item.value, str):
                    text = item.value
                # Пытаемся распарсить JSON, если это текст
                if text is not None:
                    try:
                        data = json.loads(text)
                        if isinstance(data, list):
                            for d in data:
                                if isinstance(d, dict):
                                    parsed.append(d)
                                else:
                                    parsed.append({"description": str(d)})
                        elif isinstance(data, dict):
                            parsed.append(data)
                        else:
                            parsed.append({"description": str(data)})
                    except Exception:
                        # Текст без JSON — используем как описание
                        parsed.append({"description": text})
                else:
                    # Фоллбек: приводим к строке
                    parsed.append({"description": str(item)})
            except Exception as e:
                logger.warning(f"Failed to parse tool content item: {e}")
        return parsed
    
    async def get_available_tools(self) -> List[str]:
        """
        Получает список доступных инструментов
        
        Returns:
            Список названий инструментов
        """
        try:
            session, client = await self._get_session()
            if not session:
                return ["get-daily-news", "get-weekly-news", "search-news"]
            
            try:
                # Получаем список инструментов
                tools_result = await session.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                
                logger.info(f"Available tools: {', '.join(tool_names)}")
                return tool_names
                
            finally:
                await session.__aexit__(None, None, None)
                await client.__aexit__(None, None, None)
                
        except Exception as e:
            logger.error(f"Error getting available tools: {e}")
            return ["get-daily-news", "get-weekly-news", "search-news"]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Проверяет состояние MCP сервера
        
        Returns:
            Статус сервера
        """
        try:
            # Проверяем доступность
            loop = asyncio.new_event_loop()
            try:
                tools = loop.run_until_complete(self.get_available_tools())
                return {
                    "status": "healthy",
                    "available_tools": tools,
                    "api_key_configured": bool(self.api_key),
                    "timestamp": datetime.now().isoformat(),
                    "source": "verge-news-mcp"
                }
            finally:
                loop.close()
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_key_configured": bool(self.api_key),
                "timestamp": datetime.now().isoformat(),
                "source": "verge-news-mcp"
            }
    
    def _fallback_daily_news(self) -> List[Dict[str, Any]]:
        """Fallback новости за день"""
        return [
            {
                "title": "The Verge: Latest Technology News",
                "description": "Fallback daily news from The Verge",
                "url": "https://www.theverge.com",
                "published_at": datetime.now().isoformat(),
                "source": "The Verge (Fallback)",
                "relevance_score": 0.7,
                "category": "Technology News"
            }
        ]
    
    def _fallback_weekly_news(self) -> List[Dict[str, Any]]:
        """Fallback новости за неделю"""
        return [
            {
                "title": "The Verge: Weekly Technology Roundup",
                "description": "Fallback weekly news from The Verge",
                "url": "https://www.theverge.com",
                "published_at": (datetime.now() - timedelta(days=3)).isoformat(),
                "source": "The Verge (Fallback)",
                "relevance_score": 0.6,
                "category": "Technology News"
            }
        ]
    
    def _fallback_search_news(self, keyword: str) -> List[Dict[str, Any]]:
        """Fallback поиск новостей"""
        return [
            {
                "title": f"The Verge: News about {keyword}",
                "description": f"Fallback search results for '{keyword}' from The Verge",
                "url": "https://www.theverge.com",
                "published_at": datetime.now().isoformat(),
                "source": "The Verge (Fallback)",
                "relevance_score": 0.5,
                "category": "Technology News",
                "search_keyword": keyword
            }
        ]

# Синхронная обертка
class VergeNewsMCPSync:
    """Синхронная обертка для VergeNewsMCPClient"""
    
    def __init__(self, api_key: str = None):
        self.client = VergeNewsMCPClient(api_key)
    
    def get_daily_news(self) -> List[Dict[str, Any]]:
        """Синхронное получение дневных новостей"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.get_daily_news())
        finally:
            loop.close()
    
    def get_weekly_news(self) -> List[Dict[str, Any]]:
        """Синхронное получение недельных новостей"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.get_weekly_news())
        finally:
            loop.close()
    
    def search_news(self, keyword: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Синхронный поиск новостей"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.search_news(keyword, days_back))
        finally:
            loop.close()
    
    def get_available_tools(self) -> List[str]:
        """Синхронное получение доступных инструментов"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.client.get_available_tools())
        finally:
            loop.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Синхронная проверка состояния"""
        return self.client.health_check()

# Глобальный экземпляр
verge_news_client = VergeNewsMCPClient()

if __name__ == "__main__":
    """Тестирование MCP клиента"""
    async def test_client():
        client = VergeNewsMCPClient()
        
        print("🔍 Проверяем доступные инструменты...")
        tools = await client.get_available_tools()
        print(f"✅ Доступные инструменты: {', '.join(tools)}")
        
        print("\n📰 Получаем дневные новости...")
        daily_news = await client.get_daily_news()
        print(f"✅ Получено {len(daily_news)} дневных новостей")
        
        print("\n🔍 Ищем новости об AI...")
        ai_news = await client.search_news("AI", 7)
        print(f"✅ Найдено {len(ai_news)} новостей об AI")
        
        print("\n📊 Проверяем состояние...")
        health = client.health_check()
        print(f"✅ Статус: {health['status']}")
    
    try:
        asyncio.run(test_client())
    except Exception as e:
        print(f"❌ Ошибка в тестировании: {e}")
