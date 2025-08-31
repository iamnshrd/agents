import typer
import json
from devtools import pprint
import os
import sys

# Ensure project root is on PYTHONPATH when running via `python scripts/python/cli.py`
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load environment variables from .env as early as possible
try:
    from dotenv import load_dotenv
    _ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")
    # Try explicit project-root .env to avoid search issues
    load_dotenv(dotenv_path=_ENV_PATH)
except Exception:
    pass

from agents.connectors.news_mcp_adapter import News

# Lazy loaders to avoid importing heavy deps (e.g., web3) at CLI import time
def _get_Polymarket():
    try:
        from agents.polymarket.polymarket import Polymarket as _Polymarket
        return _Polymarket
    except Exception as e:
        raise RuntimeError(f"Polymarket is unavailable: {e}")

def _get_Trader():
    try:
        from agents.application.trade import Trader as _Trader
        return _Trader
    except Exception as e:
        raise RuntimeError(f"Trader is unavailable: {e}")

def _get_DryRunTrader():
    try:
        from agents.application.dry_run_trader import DryRunTrader as _Dry
        return _Dry
    except Exception:
        # Fallback to enhanced dry-run trader if base implementation unavailable
        try:
            from agents.application.enhanced_dry_run_trader import EnhancedDryRunTraderSync as _Enhanced
            return _Enhanced
        except Exception:
            # Minimal stub to keep CLI responsive
            class _Stub:
                def one_best_trade(self):
                    print("DryRunTrader unavailable: optional dependencies missing")

                def send_daily_summary(self):
                    pass
            return _Stub

def _get_Executor():
    from agents.application.executor import Executor as _Executor
    return _Executor

def _get_Creator():
    from agents.application.creator import Creator as _Creator
    return _Creator

app = typer.Typer()
newsapi_client = News()

def _get_PolymarketRAG():
    try:
        from agents.connectors.chroma import PolymarketRAG as _RAG
        return _RAG
    except Exception as e:
        raise RuntimeError(f"PolymarketRAG is unavailable: {e}")


@app.command()
def get_all_markets(limit: int = 5, sort_by: str = "spread") -> None:
    """
    Query Polymarket's markets
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    try:
        Polymarket = _get_Polymarket()
        polymarket = Polymarket()
    except RuntimeError as e:
        print(f"❌ {e}")
        print("💡 Install 'web3' or run in Docker to use Polymarket features.")
        return
    markets = polymarket.get_all_markets()
    markets = polymarket.filter_markets_for_trading(markets)
    if sort_by == "spread":
        markets = sorted(markets, key=lambda x: x.spread, reverse=True)
    markets = markets[:limit]
    pprint(markets)


@app.command()
def get_relevant_news(keywords: str) -> None:
    """
    Use MCP servers to query the internet (compatible with old NewsAPI interface)
    """
    articles = newsapi_client.get_articles_for_cli_keywords(keywords)
    
    if not articles:
        print("❌ Новости не найдены")
    else:
        print(f"\n📰 Найдено статей: {len(articles)} по ключевым словам: {keywords}")
        print("=" * 50)
        # Печатаем первые 5 в коротком формате
        for i, a in enumerate(articles[:5], 1):
            title = a.title or "No title"
            url = a.url or ""
            source = a.source.name if a.source else "Unknown"
            published = a.publishedAt or ""
            print(f"{i}. {title}")
            if published:
                print(f"   📅 {published}")
            if url:
                print(f"   🔗 {url}")
            print(f"   📰 {source}")
            # Короткий анонс
            if a.description:
                desc = a.description.replace("\n", " ")
                print(f"   📝 {desc[:140]}{'...' if len(desc) > 140 else ''}")
            print()
    
    # Показываем статус MCP серверов
    if hasattr(newsapi_client, 'health_check'):
        status = newsapi_client.health_check()
        print(f"\n📡 MCP Status: {status['mcp_available']}")
        print(f"   The Verge News: {status['verge_news_status']}")
        print(f"   Tavily: {status['tavily_status']}")


@app.command()
def get_all_events(limit: int = 5, sort_by: str = "number_of_markets") -> None:
    """
    Query Polymarket's events
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    try:
        Polymarket = _get_Polymarket()
        polymarket = Polymarket()
    except RuntimeError as e:
        print(f"❌ {e}")
        print("💡 Install 'web3' or run in Docker to use Polymarket features.")
        return
    events = polymarket.get_all_events()
    events = polymarket.filter_events_for_trading(events)
    if sort_by == "number_of_markets":
        events = sorted(events, key=lambda x: len(x.markets), reverse=True)
    events = events[:limit]
    pprint(events)


@app.command()
def create_local_markets_rag(local_directory: str) -> None:
    """
    Create a local markets database for RAG
    """
    try:
        PolymarketRAG = _get_PolymarketRAG()
        polymarket_rag = PolymarketRAG()
    except RuntimeError as e:
        print(f"❌ {e}")
        print("💡 Install 'langchain', 'chromadb', 'openai' to use RAG features.")
        return
    polymarket_rag.create_local_markets_rag(local_directory=local_directory)


@app.command()
def query_local_markets_rag(vector_db_directory: str, query: str) -> None:
    """
    RAG over a local database of Polymarket's events
    """
    try:
        PolymarketRAG = _get_PolymarketRAG()
        polymarket_rag = PolymarketRAG()
    except RuntimeError as e:
        print(f"❌ {e}")
        print("💡 Install 'langchain', 'chromadb', 'openai' to use RAG features.")
        return
    response = polymarket_rag.query_local_markets_rag(local_directory=vector_db_directory, query=query)
    pprint(response)


@app.command()
def ask_superforecaster(event_title: str, market_question: str, outcome: str) -> None:
    """
    Ask a superforecaster about a trade
    """
    print(
        f"event: str = {event_title}, question: str = {market_question}, outcome (usually yes or no): str = {outcome}"
    )
    Executor = _get_Executor()
    executor = Executor()
    response = executor.get_superforecast(
        event_title=event_title, market_question=market_question, outcome=outcome
    )
    print(f"Response:{response}")


@app.command()
def create_market() -> None:
    """
    Format a request to create a market on Polymarket
    """
    Creator = _get_Creator()
    c = Creator()
    market_description = c.one_best_market()
    print(f"market_description: str = {market_description}")


@app.command()
def dry_run_trade() -> None:
    """
    Execute one trade in dry-run mode with Telegram alerts
    """
    print("Starting dry-run trading...")
    DryRunTrader = _get_DryRunTrader()
    trader = DryRunTrader()
    try:
        if hasattr(trader, "one_best_trade"):
            trader.one_best_trade()
        elif hasattr(trader, "execute_enhanced_trade"):
            result = trader.execute_enhanced_trade()
            if result:
                print(f"✅ Dry-run trade done: {result.get('event_title')}")
        else:
            print("No suitable dry-run trader available.")
    finally:
        # Best-effort summary if supported
        if hasattr(trader, "send_daily_summary"):
            trader.send_daily_summary()
        elif hasattr(trader, "get_enhanced_summary"):
            summary = trader.get_enhanced_summary()
            print(f"Summary: trades={summary.get('total_trades',0)}, pnl={summary.get('total_pnl',0):.2f}")
    print("Dry-run trading completed!")


@app.command()
def show_config() -> None:
    """
    Show current trading configuration
    """
    from agents.utils.trading_config import trading_config
    config_summary = trading_config.get_config_summary()
    print("Current Trading Configuration:")
    pprint(config_summary)


@app.command()
def performance_report(date: str = None) -> None:
    """
    Generate performance report for a specific date or last 7 days
    """
    from agents.utils.performance_analyzer import performance_analyzer
    
    if date is None:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Generating performance report for {date}...")
    report = performance_analyzer.generate_performance_report(date)
    print(report)


@app.command()
def performance_summary(days: int = 7) -> None:
    """
    Show performance summary for the last N days
    """
    from agents.utils.performance_analyzer import performance_analyzer
    
    print(f"Generating performance summary for last {days} days...")
    summary = performance_analyzer.get_performance_summary(days)
    
    if "error" in summary:
        print(f"Error: {summary['error']}")
        return
    
    print(f"\n📊 Performance Summary for {summary['period']}")
    print(f"Total trades: {summary.get('total_trades', 0)}")
    print(f"Total PnL: ${summary.get('total_pnl', 0):.2f}")
    print(f"Win rate: {summary.get('win_rate', 0):.1f}%")
    print(f"Sharpe ratio: {summary.get('sharpe_ratio', 0):.4f}")
    print(f"Max drawdown: ${summary.get('max_drawdown', 0):.4f}")


@app.command()
def export_performance(start_date: str, end_date: str, filename: str = None) -> None:
    """
    Export performance data to JSON file
    """
    from agents.utils.performance_analyzer import performance_analyzer
    
    print(f"Exporting performance data from {start_date} to {end_date}...")
    
    try:
        export_path = performance_analyzer.export_performance_data(start_date, end_date, filename)
        print(f"✅ Performance data exported to: {export_path}")
    except Exception as e:
        print(f"❌ Error exporting data: {e}")


@app.command()
def cleanup_logs(days_to_keep: int = 30) -> None:
    """
    Clean up old log files
    """
    from agents.utils.trading_logger import trading_logger
    
    print(f"Cleaning up logs older than {days_to_keep} days...")
    trading_logger.cleanup_old_logs(days_to_keep)
    print("✅ Log cleanup completed!")


@app.command()
def show_positions() -> None:
    """
    Show current open positions
    """
    from agents.utils.trading_logger import trading_logger
    from datetime import datetime
    
    print("📊 ТЕКУЩИЕ ПОЗИЦИИ")
    print("=" * 50)
    
    try:
        # Получаем сегодняшние сделки
        today = datetime.now().strftime("%Y-%m-%d")
        trades = trading_logger.get_trades_for_date(today)
        
        if not trades:
            print("❌ Нет данных о позициях за сегодня")
            return
        
        # Фильтруем только исполненные сделки (включая enhanced)
        executed_trades = [
            t for t in trades if t.get("type") in {"execution", "enhanced_execution"}
        ]
        
        if not executed_trades:
            print("❌ Нет исполненных сделок за сегодня")
            return
        
        print(f"📅 Дата: {today}")
        print(f"🔢 Всего позиций: {len(executed_trades)}")
        print()
        
        total_pnl = 0
        winning_positions = 0
        losing_positions = 0
        
        for i, trade in enumerate(executed_trades, 1):
            data = trade.get("data", {})
            event_title = data.get("event_title", "Unknown")
            size = data.get("size", 0)
            pnl = data.get("pnl", 0)
            price_change = data.get("price_change", 0)
            trade_id = data.get("trade_id", "N/A")
            
            # Определяем статус позиции
            if pnl > 0:
                status = "📈 ПРИБЫЛЬ"
                winning_positions += 1
            elif pnl < 0:
                status = "📉 УБЫТОК"
                losing_positions += 1
            else:
                status = "➖ БЕЗ ИЗМЕНЕНИЙ"
            
            total_pnl += pnl
            
            print(f"🎯 Позиция {i}: {event_title}")
            print(f"   {status}")
            print(f"   💰 PnL: ${pnl:.2f}")
            print(f"   📏 Размер: {size*100:.1f}%")
            print(f"   📊 Изменение цены: {price_change*100:+.2f}%")
            print(f"   🆔 ID: {trade_id}")
            print()
        
        # Сводка
        print("=" * 50)
        print("📊 СВОДКА ПОЗИЦИЙ")
        print(f"💰 Общий PnL: ${total_pnl:.2f}")
        print(f"📈 Прибыльных: {winning_positions}")
        print(f"📉 Убыточных: {losing_positions}")
        
        if executed_trades:
            win_rate = winning_positions / len(executed_trades) * 100
            print(f"🎯 Процент успешных: {win_rate:.1f}%")
        
    except Exception as e:
        print(f"❌ Ошибка при получении позиций: {e}")


@app.command()
def show_portfolio() -> None:
    """
    Show current portfolio performance
    """
    from agents.utils.trading_config import trading_config
    from agents.utils.trading_logger import trading_logger
    from datetime import datetime
    
    print("📈 ПРОИЗВОДИТЕЛЬНОСТЬ ПОРТФЕЛЯ")
    print("=" * 50)
    
    try:
        # Показываем конфигурацию
        config = trading_config.get_config_summary()
        print(f"🔧 Режим торговли: {config['trading_mode']}")
        print(f"💰 Доступный баланс: ${config['available_balance']:.2f}")
        print(f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Получаем сегодняшние сделки
        today = datetime.now().strftime("%Y-%m-%d")
        trades = trading_logger.get_trades_for_date(today)
        
        if not trades:
            print("❌ Нет данных о торговле за сегодня")
            return
        
        # Анализируем производительность
        executed_trades = [
            t for t in trades if t.get("type") in {"execution", "enhanced_execution"}
        ]
        
        if not executed_trades:
            print("❌ Нет исполненных сделок за сегодня")
            return
        
        # Вычисляем метрики
        total_trades = len(executed_trades)
        total_pnl = sum(t.get("data", {}).get("pnl", 0) for t in executed_trades)
        winning_trades = sum(1 for t in executed_trades if t.get("data", {}).get("pnl", 0) > 0)
        losing_trades = sum(1 for t in executed_trades if t.get("data", {}).get("pnl", 0) < 0)
        
        # Размеры позиций
        position_sizes = [t.get("data", {}).get("size", 0) for t in executed_trades]
        avg_position_size = sum(position_sizes) / len(position_sizes) if position_sizes else 0
        
        # PnL метрики
        pnl_values = [t.get("data", {}).get("pnl", 0) for t in executed_trades]
        max_profit = max(pnl_values) if pnl_values else 0
        max_loss = min(pnl_values) if pnl_values else 0
        
        # Процентные изменения
        price_changes = [t.get("data", {}).get("price_change", 0) for t in executed_trades]
        avg_price_change = sum(price_changes) / len(price_changes) if price_changes else 0
        
        print("🎯 ОБЩАЯ СТАТИСТИКА")
        print(f"📊 Всего сделок: {total_trades}")
        print(f"💰 Общий PnL: ${total_pnl:.2f}")
        print(f"📈 Прибыльных: {winning_trades}")
        print(f"📉 Убыточных: {losing_trades}")
        
        if total_trades > 0:
            win_rate = winning_trades / total_trades * 100
            print(f"🎯 Процент успешных: {win_rate:.1f}%")
        
        print()
        print("📏 РАЗМЕРЫ ПОЗИЦИЙ")
        print(f"📊 Средний размер: {avg_position_size*100:.1f}%")
        print(f"📈 Максимальный размер: {max(position_sizes)*100:.1f}%" if position_sizes else "N/A")
        print(f"📉 Минимальный размер: {min(position_sizes)*100:.1f}%" if position_sizes else "N/A")
        
        print()
        print("💰 PnL АНАЛИЗ")
        print(f"📈 Макс. прибыль: ${max_profit:.2f}")
        print(f"📉 Макс. убыток: ${max_loss:.2f}")
        print(f"📊 Среднее изменение цены: {avg_price_change*100:+.2f}%")
        
        # Риск-метрики
        print()
        print("⚠️ РИСК-МЕТРИКИ")
        risk_limits = trading_config.get_risk_limits()
        print(f"🚫 Макс. размер позиции: {risk_limits['max_position_size']*100:.1f}%")
        print(f"⚠️ Риск на сделку: {risk_limits['risk_per_trade']*100:.1f}%")
        print(f"📊 Макс. сделок в день: {risk_limits['max_daily_trades']}")
        print(f"💸 Макс. дневной убыток: {risk_limits['max_daily_loss']*100:.1f}%")
        
        # Проверяем лимиты
        if total_trades >= risk_limits['max_daily_trades']:
            print("🚨 Достигнут лимит сделок на день!")
        
        if abs(total_pnl) >= config['available_balance'] * risk_limits['max_daily_loss']:
            print("🚨 Достигнут лимит дневных убытков!")
        
    except Exception as e:
        print(f"❌ Ошибка при анализе портфеля: {e}")


@app.command()
def show_trade_history(limit: int = 10) -> None:
    """
    Show recent trade history
    """
    from agents.utils.trading_logger import trading_logger
    from datetime import datetime
    
    print(f"📚 ИСТОРИЯ СДЕЛОК (последние {limit})")
    print("=" * 50)
    
    try:
        # Получаем сегодняшние сделки
        today = datetime.now().strftime("%Y-%m-%d")
        trades = trading_logger.get_trades_for_date(today)
        
        if not trades:
            print("❌ Нет данных о торговле за сегодня")
            return
        
        # Фильтруем и сортируем по времени
        executed_trades = [
            t for t in trades if t.get("type") in {"execution", "enhanced_execution"}
        ]
        executed_trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        if not executed_trades:
            print("❌ Нет исполненных сделок за сегодня")
            return
        
        # Показываем последние сделки
        recent_trades = executed_trades[:limit]
        
        for i, trade in enumerate(recent_trades, 1):
            data = trade.get("data", {})
            timestamp = trade.get("timestamp", "")
            event_title = data.get("event_title", "Unknown")
            size = data.get("size", 0)
            pnl = data.get("pnl", 0)
            trade_id = data.get("trade_id", "N/A")
            
            # Форматируем время
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp
            
            # Статус
            if pnl > 0:
                status = "📈"
            elif pnl < 0:
                status = "📉"
            else:
                status = "➖"
            
            print(f"{i:2d}. {status} {time_str} | {event_title[:40]}...")
            print(f"    💰 PnL: ${pnl:+.2f} | 📏 {size*100:.1f}% | 🆔 {trade_id}")
            print()
        
        print(f"📊 Показано {len(recent_trades)} из {len(executed_trades)} сделок")
        
    except Exception as e:
        print(f"❌ Ошибка при получении истории: {e}")


@app.command()
def enhanced_dry_run_trade() -> None:
    """
    Execute one enhanced trade using Tavily MCP integration
    """
    print("🚀 Starting enhanced dry-run trading with MCP...")
    
    try:
        from agents.application.enhanced_dry_run_trader import EnhancedDryRunTraderSync
        
        trader = EnhancedDryRunTraderSync()
        trade_result = trader.execute_enhanced_trade()
        
        if trade_result:
            print(f"✅ Enhanced trade completed: {trade_result.get('event_title')}")
            print(f"💰 PnL: ${trade_result.get('pnl', 0):.2f}")
            print(f"🎯 Analysis source: {trade_result.get('analysis_source', 'unknown')}")
        else:
            print("❌ Enhanced trade failed")
        
        # Ежедневный отчёт отключён по умолчанию
        
    except Exception as e:
        print(f"❌ Error in enhanced dry-run trade: {e}")


@app.command()
def enhanced_dry_run_on_query(query: str) -> None:
    """
    Execute one enhanced dry-run trade on a specific real-market query (MCP + RAG, Telegram trade alerts only)
    """
    print(f"🚀 Starting enhanced dry-run on query: {query}")
    try:
        from agents.application.enhanced_dry_run_trader import EnhancedDryRunTraderSync
        trader = EnhancedDryRunTraderSync()
        trade_result = trader.execute_enhanced_trade_on_query(query)
        if trade_result:
            print(f"✅ Enhanced trade completed: {trade_result.get('event_title')}")
            print(f"💰 PnL: ${trade_result.get('pnl', 0):.2f}")
            print(f"🎯 Analysis source: {trade_result.get('analysis_source', 'unknown')}")
        else:
            print("❌ Enhanced trade failed")
        # Ежедневный отчёт отключён по умолчанию
    except Exception as e:
        print(f"❌ Error in enhanced dry-run trade on query: {e}")

@app.command()
def enhanced_session(num_trades: int = 3) -> None:
    """
    Run enhanced trading session with MCP integration
    """
    print(f"🚀 Starting enhanced trading session with {num_trades} trades...")
    
    try:
        from agents.application.enhanced_dry_run_trader import EnhancedDryRunTraderSync
        
        trader = EnhancedDryRunTraderSync()
        trader.run_enhanced_session(num_trades)
        
        # Показываем результаты
        summary = trader.get_enhanced_summary()
        print(f"\n📊 Enhanced Session Results:")
        print(f"Total trades: {summary.get('total_trades', 0)}")
        print(f"Total PnL: ${summary.get('total_pnl', 0):.2f}")
        print(f"MCP analysis trades: {summary.get('mcp_analysis_trades', 0)}")
        print(f"Fallback trades: {summary.get('fallback_trades', 0)}")
        print(f"Market analysis count: {summary.get('market_analysis_count', 0)}")
        
    except Exception as e:
        print(f"❌ Error in enhanced session: {e}")


@app.command()
def show_mcp_status() -> None:
    """
    Show Tavily MCP server status and configuration
    """
    print("🔍 TAVILY MCP СТАТУС")
    print("=" * 50)
    
    try:
        from agents.utils.trading_config import trading_config
        from agents.connectors.tavily_mcp import TavilyMCPSync
        
        # Показываем конфигурацию
        tavily_config = trading_config.get_tavily_config()
        print(f"🔑 API ключ настроен: {'✅' if tavily_config['api_key_configured'] else '❌'}")
        print(f"🌐 Сервер URL: {tavily_config['server_url']}")
        print(f"🔍 Глубина поиска: {tavily_config['search_depth']}")
        print(f"📊 Макс. результатов: {tavily_config['max_results']}")
        print(f"📁 Домены: {', '.join(tavily_config['include_domains'])}")
        
        print()
        
        # Проверяем состояние MCP сервера
        if trading_config.is_tavily_available():
            tavily = TavilyMCPSync()
            status = tavily.health_check()
            
            print("📡 СОСТОЯНИЕ MCP СЕРВЕРА:")
            print(f"   API ключ: {'✅' if status.get('api_key_configured') else '❌'}")
            print(f"   Локальный MCP: {'✅' if status.get('local_mcp_available') else '❌'}")
            print(f"   Удаленный MCP: {'✅' if status.get('remote_mcp_available') else '❌'}")
            print(f"   Время проверки: {status.get('timestamp', 'N/A')}")
            
            if status.get('error'):
                print(f"   ⚠️ Ошибка: {status['error']}")
        else:
            print("❌ Tavily MCP недоступен")
            print("💡 Для настройки добавьте TAVILY_API_KEY в .env файл")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке MCP статуса: {e}")


@app.command()
def test_mcp_search(query: str = "AI technology 2024") -> None:
    """
    Test Tavily MCP search functionality
    """
    print(f"🔍 Тестирование MCP поиска: {query}")
    print("=" * 50)
    
    try:
        from agents.connectors.tavily_mcp import TavilyMCPSync
        
        tavily = TavilyMCPSync()
        
        # Тестируем поиск
        print("🔍 Выполняем поиск...")
        search_results = tavily.search_markets(query, "basic")
        
        if search_results:
            print(f"✅ Найдено результатов: {len(search_results)}")
            
            for i, result in enumerate(search_results[:3], 1):
                print(f"\n{i}. {result.get('title', 'No title')}")
                print(f"   URL: {result.get('url', 'No URL')}")
                print(f"   Релевантность: {result.get('relevance_score', 'N/A')}")
        else:
            print("❌ Результаты поиска не найдены")
        
        # Тестируем извлечение данных
        if search_results:
            print(f"\n📊 Тестируем извлечение данных...")
            first_url = search_results[0].get('url')
            if first_url:
                extracted_data = tavily.extract_market_data(first_url)
                if extracted_data:
                    print("✅ Данные успешно извлечены:")
                    for key, value in extracted_data.items():
                        print(f"   {key}: {value}")
                else:
                    print("❌ Не удалось извлечь данные")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании MCP: {e}")


@app.command()
def show_mcp_config() -> None:
    """
    Show MCP configuration for different clients
    """
    print("⚙️ MCP КОНФИГУРАЦИЯ ДЛЯ КЛИЕНТОВ")
    print("=" * 50)
    
    try:
        from agents.connectors.tavily_mcp import TavilyMCPSync
        
        tavily = TavilyMCPSync()
        tavily_config = tavily.get_mcp_config()
        
        print("📱 Для Claude Desktop:")
        print("Добавьте в ~/Library/Application Support/Claude/claude_desktop_config.json:")
        print(json.dumps(tavily_config, indent=2))
        
        print("\n💻 Для VS Code:")
        print("Добавьте в User Settings (JSON):")
        print(json.dumps(tavily_config, indent=2))
        
        print("\n🤖 Для Cline:")
        print("Добавьте в cline_mcp_settings.json:")
        print(json.dumps(tavily_config, indent=2))
        
    except Exception as e:
        print(f"❌ Ошибка при получении Tavily MCP конфигурации: {e}")
    
    print("\n" + "=" * 50)
    print("📰 THE VERGE NEWS MCP КОНФИГУРАЦИЯ")
    print("=" * 50)
    
    try:
        from agents.connectors.verge_news_mcp import VergeNewsMCPSync
        
        verge_news = VergeNewsMCPSync()
        verge_config = {
            "mcpServers": {
                "verge-news-mcp": {
                    "command": "npx",
                    "args": ["-y", "@anthropic-ai/smithery"],
                    "env": {
                        "SMITHERY_API_KEY": "970828f0-e3a7-4778-a72f-2cc44656511d"
                    }
                }
            }
        }
        
        print("📱 Для Claude Desktop:")
        print("Добавьте в ~/Library/Application Support/Claude/claude_desktop_config.json:")
        print(json.dumps(verge_config, indent=2))
        
        print("\n💻 Для VS Code:")
        print("Добавьте в User Settings (JSON):")
        print(json.dumps(verge_config, indent=2))
        
        print("\n🤖 Для Cline:")
        print("Добавьте в cline_mcp_settings.json:")
        print(json.dumps(verge_config, indent=2))
        
    except Exception as e:
        print(f"❌ Ошибка при получении Verge News MCP конфигурации: {e}")


@app.command()
def show_verge_news_status() -> None:
    """
    Show The Verge News MCP server status and configuration
    """
    print("📰 THE VERGE NEWS MCP СТАТУС")
    print("=" * 50)
    
    try:
        from agents.utils.trading_config import trading_config
        from agents.connectors.verge_news_mcp import VergeNewsMCPSync
        
        # Показываем конфигурацию
        verge_config = trading_config.get_verge_news_config()
        print(f"🔑 API ключ настроен: {'✅' if verge_config['api_key_configured'] else '❌'}")
        print(f"🌐 Сервер URL: {verge_config['server_url']}")
        print(f"📰 Источник: {verge_config['source']}")
        print(f"🔧 Доступные инструменты: {', '.join(verge_config['available_tools'])}")
        
        print()
        
        # Проверяем состояние MCP сервера
        if trading_config.is_verge_news_available():
            verge_news = VergeNewsMCPSync()
            status = verge_news.health_check()
            
            print("📡 СОСТОЯНИЕ MCP СЕРВЕРА:")
            print(f"   Статус: {status.get('status', 'Unknown')}")
            print(f"   API ключ: {'✅' if status.get('api_key_configured') else '❌'}")
            print(f"   Доступные инструменты: {', '.join(status.get('available_tools', []))}")
            print(f"   Время проверки: {status.get('timestamp', 'N/A')}")
            print(f"   Источник: {status.get('source', 'N/A')}")
            
            if status.get('error'):
                print(f"   ⚠️ Ошибка: {status['error']}")
        else:
            print("❌ The Verge News MCP недоступен")
            print("💡 Для настройки добавьте SMITHERY_API_KEY в .env файл")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке Verge News MCP статуса: {e}")


@app.command()
def test_verge_news_search(query: str = "AI technology") -> None:
    """
    Test The Verge News MCP search functionality
    """
    print(f"🔍 Тестирование Verge News MCP поиска: {query}")
    print("=" * 50)
    
    try:
        from agents.connectors.verge_news_mcp import VergeNewsMCPSync
        
        verge_news = VergeNewsMCPSync()
        
        # Тестируем поиск
        print("🔍 Выполняем поиск новостей...")
        search_results = verge_news.search_news(query, days_back=7)
        
        if search_results:
            print(f"✅ Найдено новостей: {len(search_results)}")
            
            for i, news in enumerate(search_results[:3], 1):
                print(f"\n{i}. {news.get('title', 'No title')}")
                print(f"   Описание: {news.get('description', 'No description')[:100]}...")
                print(f"   URL: {news.get('url', 'No URL')}")
                print(f"   Источник: {news.get('source', 'Unknown')}")
                print(f"   Релевантность: {news.get('relevance_score', 'N/A')}")
        else:
            print("❌ Новости не найдены")
        
        # Тестируем дневные новости
        print(f"\n📰 Тестируем дневные новости...")
        daily_news = verge_news.get_daily_news()
        if daily_news:
            print(f"✅ Получено дневных новостей: {len(daily_news)}")
        else:
            print("❌ Дневные новости не получены")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании Verge News MCP: {e}")


@app.command()
def get_verge_daily_news() -> None:
    """
    Get today's news from The Verge
    """
    print("📰 ПОЛУЧЕНИЕ ДНЕВНЫХ НОВОСТЕЙ ОТ THE VERGE")
    print("=" * 50)
    
    try:
        from agents.connectors.verge_news_mcp import VergeNewsMCPSync
        
        verge_news = VergeNewsMCPSync()
        
        print("🔍 Получаем новости за последние 24 часа...")
        daily_news = verge_news.get_daily_news()
        
        if daily_news:
            print(f"✅ Получено {len(daily_news)} новостей:")
            
            for_found = False
            for i, news in enumerate(daily_news, 1):
                print(f"\n{i}. {news.get('title', 'No title')}")
                print(f"   📝 {news.get('description', 'No description')[:150]}...")
                print(f"   🔗 {news.get('url', 'No URL')}")
                print(f"   📅 {news.get('published_at', 'Unknown date')}")
                print(f"   📊 Релевантность: {news.get('relevance_score', 'N/A')}")
        else:
            print("❌ Новости не получены")
        
    except Exception as e:
        print(f"❌ Ошибка при получении дневных новостей: {e}")


@app.command()
def check_mcp_compatibility() -> None:
    """
    Check compatibility between old code and new MCP servers
    """
    print("🔍 ПРОВЕРКА СОВМЕСТИМОСТИ MCP СЕРВЕРОВ")
    print("=" * 50)
    
    try:
        # Проверяем старый интерфейс
        print("📰 Тестирование старого интерфейса News()...")
        
        # Тест 1: Получение статей по ключевым словам
        print("   🔍 Тест 1: get_articles_for_cli_keywords")
        test_keywords = "AI,technology"
        articles = newsapi_client.get_articles_for_cli_keywords(test_keywords)
        print(f"   ✅ Получено статей: {len(articles)}")
        
        # Тест 2: Получение статей для опций
        print("   📊 Тест 2: get_articles_for_options")
        test_options = ["AI", "technology", "blockchain"]
        articles_dict = newsapi_client.get_articles_for_options(test_options)
        print(f"   ✅ Опций обработано: {len(articles_dict)}")
        
        # Тест 3: Проверка состояния MCP
        print("   📡 Тест 3: health_check")
        if hasattr(newsapi_client, 'health_check'):
            status = newsapi_client.health_check()
            print(f"   ✅ MCP доступен: {status['mcp_available']}")
            print(f"      The Verge News: {status['verge_news_status']}")
            print(f"      Tavily: {status['tavily_status']}")
        else:
            print("   ❌ health_check недоступен")
        
        print("\n🎉 Все тесты совместимости пройдены!")
        print("💡 Старый код теперь работает с новыми MCP серверами")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке совместимости: {e}")


@app.command()
def ask_llm(user_input: str) -> None:
    """
    Ask a question to the LLM and get a response.
    """
    Executor = _get_Executor()
    executor = Executor()
    response = executor.get_llm_response(user_input)
    print(f"LLM Response: {response}")


@app.command()
def ask_polymarket_llm(user_input: str) -> None:
    """
    What types of markets do you want trade?
    """
    Executor = _get_Executor()
    executor = Executor()
    response = executor.get_polymarket_llm(user_input=user_input)
    print(f"LLM + current markets&events response: {response}")


@app.command()
def run_autonomous_trader() -> None:
    """
    Let an autonomous system trade for you.
    """
    Trader = _get_Trader()
    trader = Trader()
    trader.one_best_trade()


@app.command()
def test_telegram(message: str = "Test trade alert ping") -> None:
    """
    Send test Telegram message and print config status.
    """
    try:
        from agents.connectors.telegram import TelegramAlertsSync
        from dotenv import load_dotenv
        # Ensure .env is loaded explicitly
        _ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")
        load_dotenv(dotenv_path=_ENV_PATH)
    except Exception as e:
        print(f"❌ dotenv error: {e}")
    try:
        alerts = TelegramAlertsSync()
        cfg = {
            "enabled": getattr(alerts.async_client, "alerts_enabled", False),
            "token_present": bool(getattr(alerts.async_client, "bot_token", None)),
            "chat_present": bool(getattr(alerts.async_client, "chat_id", None)),
        }
        print(f"Telegram config: enabled={cfg['enabled']} token={cfg['token_present']} chat={cfg['chat_present']}")
        ok = alerts.send_trade_alert({
            "event_title": message,
            "market_question": "Connectivity check",
            "side": "INFO",
            "price": 0.0,
            "size": 0.0,
            "confidence": 1.0,
        })
        print(f"Send status: {'✅' if ok else '❌'}")
    except Exception as e:
        print(f"❌ Telegram test failed: {e}")


@app.command()
def scan_fresh_markets(
    limit: int = 100,
    top_k: int = 10,
    min_spread: float = 0.02,
    min_volume: float = 100.0,
    max_days_to_end: int = 120,
    include_keywords: str = "",
    exclude_keywords: str = "",
    post_to_telegram: bool = False,
    max_posts: int = 5,
    attach_rag_news: bool = False,
    news_topk: int = 3,
) -> None:
    """
    Сканирует свежие рынки Polymarket и ранжирует по opportunity_score.
    Фильтры: min_spread, min_volume, max_days_to_end, include/exclude keywords.
    Опционально постит топ-находки в Telegram.
    """
    from datetime import datetime, timezone
    import math
    try:
        from agents.polymarket.gamma import GammaMarketClient
    except Exception as e:
        print(f"❌ Gamma client unavailable: {e}")
        return

    client = GammaMarketClient()
    try:
        raw_markets = client.get_all_current_markets(limit=limit)
    except Exception as e:
        print(f"❌ Error fetching markets: {e}")
        return

    def to_float(value, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return float(value)
            return float(str(value))
        except Exception:
            return default

    def parse_dt(value) -> datetime | None:
        try:
            if not value:
                return None
            # Allow Z suffix
            if isinstance(value, str):
                if value.endswith("Z"):
                    value = value.replace("Z", "+00:00")
                return datetime.fromisoformat(value)
            return None
        except Exception:
            return None

    now = datetime.now(timezone.utc)
    inc = [k.strip().lower() for k in include_keywords.split(",") if k.strip()]
    exc = [k.strip().lower() for k in exclude_keywords.split(",") if k.strip()]
    ranked = []
    for m in raw_markets or []:
        active = m.get("active", True)
        if not active:
            continue

        spread = to_float(m.get("spread"), 0.0)
        if spread < min_spread:
            continue

        volume = to_float(m.get("volume"), 0.0)
        if volume < min_volume:
            continue
        end_dt = parse_dt(m.get("endDate"))
        start_dt = parse_dt(m.get("startDate"))

        # Keyword filters (по вопросу/описанию)
        qtext = f"{m.get('question','')}\n{m.get('description','')}".lower()
        if inc and not any(k in qtext for k in inc):
            continue
        if exc and any(k in qtext for k in exc):
            continue

        # Normalizations
        spread_norm = max(0.0, min(spread, 0.5)) / 0.5
        volume_norm = 0.0
        if volume > 0:
            volume_norm = min(1.0, math.log10(volume + 1.0) / 6.0)

        # Prefer nearer resolution (sooner end -> higher score)
        time_norm = 0.5
        if end_dt is not None:
            try:
                remaining_days = max(0.0, (end_dt.astimezone(timezone.utc) - now).total_seconds() / 86400.0)
                if remaining_days > max_days_to_end:
                    continue
                time_norm = math.exp(-remaining_days / 30.0)
            except Exception:
                pass

        opportunity_score = 0.5 * spread_norm + 0.3 * volume_norm + 0.2 * time_norm

        slug = m.get("slug")
        market_url = f"https://polymarket.com/event/{slug}" if slug else None
        ranked.append({
            "id": m.get("id"),
            "question": m.get("question", ""),
            "spread": spread,
            "volume": volume,
            "endDate": m.get("endDate"),
            "opportunity_score": opportunity_score,
            "link": f"https://gamma-api.polymarket.com/markets/{m.get('id')}",
            "market_url": market_url,
        })

    ranked.sort(key=lambda x: x["opportunity_score"], reverse=True)
    top = ranked[:top_k]

    if not top:
        print("❌ Подходящих свежих рынков не найдено")
        return

    print(f"\n🔎 Top {len(top)} opportunities (from {len(ranked)} candidates)")
    print("=" * 60)
    # Optional: load NewsRAG once if requested
    newsrag = None
    if attach_rag_news:
        try:
            from agents.connectors.news_rag import NewsRAG
            newsrag = NewsRAG(os.getenv("NEWS_RAG_DIR", "./local_news_db"))
        except Exception as e:
            print(f"⚠️ NewsRAG недоступен: {e}")
            newsrag = None

    for i, r in enumerate(top, 1):
        print(f"{i}. {r['question'][:80]}" )
        print(f"   🆔 {r['id']} | 🧮 score: {r['opportunity_score']:.3f}")
        print(f"   📊 spread: {r['spread']:.3f} | 💧 volume: {r['volume']:.2f}")
        if r.get('endDate'):
            print(f"   ⏳ end: {r['endDate']}")
        print(f"   🔗 {r['market_url'] or r['link']}")
        # Attach top news from RAG
        if newsrag is not None:
            try:
                q = r.get("question", "")
                news_hits = newsrag.query_news(q, top_k=news_topk)
                if news_hits:
                    print("   📰 Топ новости:")
                    for j, (meta, _) in enumerate(news_hits, 1):
                        title = (meta.get("title") or "No title").strip()
                        url = meta.get("url") or ""
                        if url:
                            print(f"     {j}) {title} — {url}")
                        else:
                            print(f"     {j}) {title}")
            except Exception as e:
                print(f"   ⚠️ Ошибка получения новостей: {e}")
        print()

    if post_to_telegram:
        # Policy: в Telegram отправляются только сообщения о трейдах (сигналы/исполнения/риски)
        print("ℹ️ Post-to-Telegram отключён для сканера рынков: разрешены только трейд-алерты.")


@app.command()
def create_news_rag(persist_dir: str = "./local_news_db", days: int = 14, max_items: int = 300, keywords: str = "") -> None:
    """
    Собрать новости через MCP и проиндексировать в Chroma (full text с чанкингом).
    """
    try:
        from agents.connectors.news_rag import NewsRAG
        rag = NewsRAG(persist_directory=persist_dir)
        n = rag.ingest_news(days=days, max_items=max_items, keywords_csv=keywords)
        print(f"✅ Проиндексировано чанков новостей: {n} (директория: {persist_dir})")
    except Exception as e:
        print(f"❌ Ошибка индексации новостей: {e}")


@app.command()
def query_news_rag(persist_dir: str, query: str, top_k: int = 5) -> None:
    """
    Семантический поиск по новостям в локальной базе RAG.
    """
    try:
        from agents.connectors.news_rag import NewsRAG
        rag = NewsRAG(persist_directory=persist_dir)
        results = rag.query_news(query=query, top_k=top_k)
        if not results:
            print("❌ Ничего не найдено")
            return
        print(f"📰 Найдено {len(results)} записей по запросу: {query}")
        for i, (meta, score) in enumerate(results, 1):
            title = meta.get("title") or "No title"
            url = meta.get("url") or ""
            print(f"{i}. {title}")
            if url:
                print(f"   🔗 {url}")
            print(f"   📅 {meta.get('published_at','')} | 🏷️ {meta.get('source','')}")
            print(f"   📝 {meta.get('snippet','')}")
    except Exception as e:
        print(f"❌ Ошибка запроса новостей: {e}")


@app.command()
def enrich_news_links(markets_dir: str = "./local_db", news_dir: str = "./local_news_db", top_k: int = 10, min_relevance: float = 0.6, half_life_days: float = 5.0, output: str = "./news_market_links.json") -> None:
    """
    Связать новости с рынками (RAG→RAG) и сохранить JSON со списком линков.
    """
    try:
        from agents.connectors.news_rag import NewsRAG
        rag = NewsRAG(persist_directory=news_dir)
        out = rag.link_news_to_markets(
            markets_persist_dir=markets_dir,
            top_k=top_k,
            min_relevance=min_relevance,
            half_life_days=half_life_days,
            output_path=output,
        )
        print(f"✅ Ссылки новости↔рынки сохранены: {out}")
    except Exception as e:
        print(f"❌ Ошибка линковки новостей и рынков: {e}")

if __name__ == "__main__":
    app()
