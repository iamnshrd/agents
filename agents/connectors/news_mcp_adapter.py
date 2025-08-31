#!/usr/bin/env python3
"""
Адаптер для совместимости старого кода с новыми MCP серверами
Позволяет использовать новые MCP серверы через старый интерфейс News()
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from agents.utils.objects import Article, Source
from agents.connectors.verge_news_mcp import VergeNewsMCPSync
from agents.connectors.tavily_mcp import TavilyMCPSync


class NewsMCPAdapter:
    """
    Адаптер для совместимости старого кода с новыми MCP серверами
    Реализует тот же интерфейс, что и старый класс News()
    """
    
    def __init__(self) -> None:
        """Инициализация с MCP клиентами"""
        self.configs = {
            "language": "en",
            "country": "us",
            "top_headlines": "https://mcp.theverge.com/news/headlines",
            "base_url": "https://mcp.theverge.com/",
        }

        self.categories = {
            "business",
            "entertainment", 
            "general",
            "health",
            "science",
            "sports",
            "technology",
        }
        
        # Инициализируем MCP клиенты
        try:
            self.verge_news = VergeNewsMCPSync()
            self.tavily = TavilyMCPSync()
            self.mcp_available = True
        except Exception as e:
            print(f"⚠️ MCP клиенты недоступны: {e}")
            self.mcp_available = False

    def get_articles_for_cli_keywords(self, keywords: str) -> List[Article]:
        """
        Получение статей по ключевым словам (совместимость со старым кодом)
        """
        if not self.mcp_available:
            return self._get_fallback_articles(keywords)
        
        try:
            query_words = keywords.split(",")
            all_articles = self.get_articles_for_options(query_words)
            article_objects: List[Article] = []
            
            for _, articles in all_articles.items():
                for item in articles:
                    # Нормализуем поле source
                    src_id = None
                    src_name = "The Verge"
                    src_field = item.get("source")
                    if isinstance(src_field, dict):
                        src_id = src_field.get("id")
                        src_name = src_field.get("name") or "The Verge"
                    elif isinstance(src_field, str) and src_field:
                        src_name = src_field
                    
                    # Нормализуем даты и поля
                    published_at = (
                        item.get("published_at")
                        or item.get("publishedAt")
                        or item.get("pubDate")
                        or ""
                    )
                    description = item.get("description") or item.get("summary") or "No description"
                    url = item.get("url") or item.get("link") or ""
                    content = item.get("content") or description

                    article_obj = Article(
                        title=item.get("title", "No title"),
                        description=description,
                        url=url,
                        publishedAt=published_at,
                        source=Source(id=src_id or "verge", name=src_name),
                        author=item.get("author", "Unknown"),
                        urlToImage=item.get("urlToImage", ""),
                        content=content,
                    )
                    article_objects.append(article_obj)
            
            return article_objects
            
        except Exception as e:
            print(f"❌ Ошибка при получении статей через MCP: {e}")
            return self._get_fallback_articles(keywords)

    def get_top_articles_for_market(self, market_object: Dict[str, Any]) -> List[Article]:
        """
        Получение топ статей для рынка (совместимость со старым кодом)
        """
        if not self.mcp_available:
            return self._get_fallback_articles(market_object.get("description", ""))
        
        try:
            query = market_object.get("description", "")
            if not query:
                return []
            
            # Используем The Verge News MCP для получения новостей
            news_items = self.verge_news.search_news(query, days_back=7)
            
            articles = []
            for news in news_items[:10]:  # Ограничиваем 10 статьями
                article = Article(
                    title=news.get("title", "No title"),
                    description=news.get("description", "No description"),
                    url=news.get("url", ""),
                    published_at=news.get("published_at", ""),
                    source=news.get("source", "The Verge"),
                    relevance_score=news.get("relevance_score", 0.5)
                )
                articles.append(article)
            
            return articles
            
        except Exception as e:
            print(f"❌ Ошибка при получении топ статей через MCP: {e}")
            return self._get_fallback_articles(market_object.get("description", ""))

    def get_articles_for_options(
        self,
        market_options: List[str],
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получение статей для опций рынка (совместимость со старым кодом)
        """
        if not self.mcp_available:
            return self._get_fallback_articles_dict(market_options)
        
        try:
            all_articles = {}
            
            for option in market_options:
                try:
                    # Используем The Verge News MCP для поиска
                    news_items = self.verge_news.search_news(
                        option.strip(), 
                        days_back=7 if not date_start else 30
                    )
                    
                    # Преобразуем в формат, совместимый со старым кодом
                    articles = []
                    for news in news_items:
                        src_name = news.get("source", "The Verge")
                        if isinstance(src_name, dict):
                            src_name = src_name.get("name") or "The Verge"
                        article_dict = {
                            "title": news.get("title", "No title"),
                            "description": news.get("description", news.get("summary", "No description")),
                            "url": news.get("url", news.get("link", "")),
                            "publishedAt": news.get("published_at", news.get("publishedAt", news.get("pubDate", ""))),
                            "source": {"name": src_name},
                            "author": news.get("author", "Unknown"),
                            "urlToImage": news.get("urlToImage", ""),
                            "content": news.get("content", news.get("description", "No content"))
                        }
                        articles.append(article_dict)
                    
                    all_articles[option] = articles
                    
                except Exception as e:
                    print(f"⚠️ Ошибка при получении статей для '{option}': {e}")
                    all_articles[option] = []
            
            return all_articles
            
        except Exception as e:
            print(f"❌ Ошибка при получении статей через MCP: {e}")
            return self._get_fallback_articles_dict(market_options)

    def get_category(self, market_object: Dict[str, Any]) -> str:
        """
        Получение категории новостей (совместимость со старым кодом)
        """
        news_category = "general"
        market_category = market_object.get("category", "general")
        
        if market_category in self.categories:
            news_category = market_category
            
        return news_category

    def _get_fallback_articles(self, keywords: str) -> List[Article]:
        """Fallback статьи при недоступности MCP"""
        fallback_articles = [
            Article(
                title=f"Fallback news for: {keywords}",
                description="This is a fallback article when MCP servers are unavailable",
                url="https://www.theverge.com",
                publishedAt=datetime.now().isoformat(),
                source=Source(id="verge-fallback", name="The Verge (Fallback)"),
                author="System",
                urlToImage="",
                content="This is a fallback article when MCP servers are unavailable"
            )
        ]
        return fallback_articles

    def _get_fallback_articles_dict(self, market_options: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback словарь статей при недоступности MCP"""
        all_articles = {}
        
        for option in market_options:
            fallback_article = {
                "title": f"Fallback news for: {option}",
                "description": "This is a fallback article when MCP servers are unavailable",
                "url": "https://www.theverge.com",
                "publishedAt": datetime.now().isoformat(),
                "source": {"name": "The Verge (Fallback)"},
                "author": "System",
                "urlToImage": "",
                "content": "This is a fallback article when MCP servers are unavailable"
            }
            all_articles[option] = [fallback_article]
        
        return all_articles

    def health_check(self) -> Dict[str, Any]:
        """Проверка состояния MCP серверов"""
        status = {
            "mcp_available": self.mcp_available,
            "verge_news_status": "unknown",
            "tavily_status": "unknown",
            "timestamp": datetime.now().isoformat()
        }
        
        if self.mcp_available:
            try:
                verge_status = self.verge_news.health_check()
                status["verge_news_status"] = verge_status.get("status", "unknown")
            except:
                status["verge_news_status"] = "error"
            
            try:
                tavily_status = self.tavily.health_check()
                status["tavily_status"] = tavily_status.get("status", "unknown")
            except:
                status["tavily_status"] = "error"
        
        return status


# Создаем экземпляр для совместимости
News = NewsMCPAdapter
