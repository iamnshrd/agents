# Advanced Trading Agents - Index

Полный каталог специализированных AI агентов для AlphaAgents - системы автономной торговли на prediction markets.

## 🎯 Быстрый поиск агента

### По задаче:
- **Risk Management** → `risk-manager`, `position-sizer`, `drawdown-controller`
- **Market Analysis** → `market-analyzer`, `sentiment-analyzer`, `correlation-finder`
- **Strategy Optimization** → `strategy-optimizer`, `portfolio-balancer`, `performance-enhancer`
- **Validation & Testing** → `backtester`, `stress-tester`, `strategy-validator`
- **Trading Execution** → `market-maker`, `trend-follower`, `arbitrage-hunter`
- **Coordination** → `trading-coach`

### По специализации:
- **Финансовые рынки** → Все агенты
- **Prediction markets** → Все агенты
- **Kelly criterion** → `risk-manager`, `position-sizer`, `strategy-optimizer`
- **Risk management** → `risk-manager`, `position-sizer`, `stress-tester`
- **Market data analysis** → `market-analyzer`, `sentiment-analyzer`, `correlation-finder`
- **Trading strategy validation** → `backtester`, `stress-tester`, `strategy-validator`
- **Financial performance optimization** → `strategy-optimizer`, `portfolio-balancer`, `performance-enhancer`

## 📁 Полная структура агентов

### Risk Management (`risk/`)
- **[risk-manager](risk/risk-manager.md)** - Комплексное управление рисками
- **[position-sizer](risk/position-sizer.md)** - Расчет размеров позиций по Kelly
- **[drawdown-controller](risk/drawdown-controller.md)** - Контроль просадок

### Market Analysis (`analysis/`)
- **[market-analyzer](analysis/market-analyzer.md)** - Анализ рыночных данных
- **[sentiment-analyzer](analysis/sentiment-analyzer.md)** - Анализ настроений
- **[correlation-finder](analysis/correlation-finder.md)** - Поиск корреляций

### Strategy Optimization (`optimization/`)
- **[strategy-optimizer](optimization/strategy-optimizer.md)** - Оптимизация стратегий
- **[portfolio-balancer](optimization/portfolio-balancer.md)** - Балансировка портфеля
- **[performance-enhancer](optimization/performance-enhancer.md)** - Улучшение производительности

### Validation & Testing (`validation/`)
- **[backtester](validation/backtester.md)** - Бэктестинг стратегий
- **[stress-tester](validation/stress-tester.md)** - Стресс-тестирование
- **[strategy-validator](validation/strategy-validator.md)** - Валидация стратегий

### Trading Execution (`trading/`)
- **[market-maker](trading/market-maker.md)** - Создание ликвидности
- **[trend-follower](trading/trend-follower.md)** - Следование трендам
- **[arbitrage-hunter](trading/arbitrage-hunter.md)** - Поиск арбитража

### Bonus Agents (`bonus/`)
- **[trading-coach](bonus/trading-coach.md)** - Координация агентов

## 🚀 Примеры использования

### Комплексный анализ рынка:
```
1. market-analyzer → Анализ рыночных данных
2. sentiment-analyzer → Анализ настроений
3. correlation-finder → Поиск корреляций
4. risk-manager → Оценка рисков
5. trading-coach → Координация и рекомендации
```

### Оптимизация стратегии:
```
1. backtester → Тестирование на исторических данных
2. strategy-optimizer → Оптимизация параметров
3. stress-tester → Стресс-тестирование
4. strategy-validator → Финальная валидация
5. trading-coach → Внедрение и мониторинг
```

### Управление портфелем:
```
1. portfolio-balancer → Анализ текущего портфеля
2. correlation-finder → Анализ корреляций
3. risk-manager → Оценка рисков
4. position-sizer → Расчет размеров позиций
5. portfolio-balancer → Ребалансировка
```

## 🔧 Интеграция с системой

### Основные компоненты:
- **Value Betting Engine** - Основной движок
- **Research Team** - Команда исследователей
- **Market Data Sources** - Источники данных
- **LLM Client** - Клиент для LLM
- **Risk Management System** - Система управления рисками

### Поток данных:
```
Data Sources → Market Data Agent → Analysis Agents → Research Team → Risk Manager → Portfolio Balancer → Execution Engine
```

## 📊 Статус агентов

### ✅ Активные (созданы):
- `risk-manager` - Комплексное управление рисками
- `market-analyzer` - Анализ рыночных данных
- `backtester` - Бэктестинг стратегий
- `strategy-optimizer` - Оптимизация стратегий
- `trading-coach` - Координация агентов
- `position-sizer` - Расчет размеров позиций
- `sentiment-analyzer` - Анализ настроений
- `correlation-finder` - Поиск корреляций
- `portfolio-balancer` - Балансировка портфеля
- `stress-tester` - Стресс-тестирование

### 🚧 В разработке:
- `drawdown-controller` - Контроль просадок
- `performance-enhancer` - Улучшение производительности
- `strategy-validator` - Валидация стратегий
- `market-maker` - Создание ликвидности
- `trend-follower` - Следование трендам
- `arbitrage-hunter` - Поиск арбитража

## 💡 Лучшие практики

### 1. Комбинируйте агентов:
- Многие задачи требуют нескольких агентов
- Используйте `trading-coach` для координации
- Создавайте workflows для complex tasks

### 2. Будьте конкретны:
- Четко описывайте задачу
- Указывайте контекст и ограничения
- Определяйте expected outcomes

### 3. Итерируйте быстро:
- Начинайте с простых задач
- Постепенно усложняйте
- Используйте feedback для improvement

### 4. Мониторьте производительность:
- Отслеживайте результаты агентов
- Анализируйте effectiveness
- Оптимизируйте workflows

## 🎁 Бонусные возможности

### Trading Coach:
- Координация всех агентов
- Performance monitoring
- Quality control
- Excellence framework

### Advanced Analytics:
- Machine learning integration
- Statistical analysis
- Risk modeling
- Performance optimization

### Crisis Management:
- Stress testing
- Risk mitigation
- Crisis response
- Recovery planning

## 🔗 Связанные ресурсы

- **[README](README.md)** - Основная документация
- **[tech_agents](../tech_agents/)** - Общие технические агенты
- **[Value Betting Engine](../../services/value_betting_engine/)** - Основной движок
- **[Data Sources](../../data_sources/)** - Источники данных

---

**Создано для AlphaAgents** - Система автономной торговли на prediction markets с AI-powered analysis и risk management.
