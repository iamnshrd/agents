# Advanced Trading Agents

Специализированные AI агенты для AlphaAgents - системы автономной торговли на prediction markets. Каждый агент является экспертом в своей области финансов и trading.

## 🎯 Специализация

Эти агенты созданы специально для:
- **Финансовых рынков** - понимание рыночной динамики
- **Prediction markets** - специфика Polymarket и подобных платформ
- **Kelly criterion** - оптимальное управление позициями
- **Risk management** - управление рисками и капиталом
- **Market data analysis** - анализ рыночных данных
- **Trading strategy validation** - валидация торговых стратегий
- **Financial performance optimization** - оптимизация финансовых показателей

## 📁 Структура агентов

```
advanced_agents/
├── trading/           # Торговые агенты
│   ├── market-maker.md
│   ├── trend-follower.md
│   └── arbitrage-hunter.md
├── risk/              # Управление рисками
│   ├── risk-manager.md
│   ├── position-sizer.md
│   └── drawdown-controller.md
├── analysis/          # Анализ данных
│   ├── market-analyzer.md
│   ├── sentiment-analyzer.md
│   └── correlation-finder.md
├── optimization/      # Оптимизация
│   ├── strategy-optimizer.md
│   ├── portfolio-balancer.md
│   └── performance-enhancer.md
└── validation/        # Валидация
    ├── backtester.md
    ├── stress-tester.md
    └── strategy-validator.md
```

## 🚀 Быстрый старт

Агенты автоматически доступны в системе. Просто опишите задачу, и соответствующий агент будет активирован.

### Примеры использования:
- "Проанализируй риск для рынка election-2024" → `risk-manager`
- "Оптимизируй размер позиции по Kelly criterion" → `position-sizer`
- "Валидируй стратегию на исторических данных" → `backtester`
- "Найди корреляции между рынками" → `correlation-finder`

## 📋 Полный список агентов

### Trading Department (`trading/`)
- **market-maker** - Создание ликвидности и управление спредом
- **trend-follower** - Следование трендам с адаптивными параметрами
- **arbitrage-hunter** - Поиск арбитражных возможностей

### Risk Management (`risk/`)
- **risk-manager** - Комплексное управление рисками
- **position-sizer** - Расчет размера позиции по Kelly criterion
- **drawdown-controller** - Контроль просадок и стоп-лоссов

### Market Analysis (`analysis/`)
- **market-analyzer** - Анализ рыночных данных и паттернов
- **sentiment-analyzer** - Анализ настроений и новостей
- **correlation-finder** - Поиск корреляций между активами

### Strategy Optimization (`optimization/`)
- **strategy-optimizer** - Оптимизация параметров стратегий
- **portfolio-balancer** - Балансировка портфеля
- **performance-enhancer** - Улучшение финансовых показателей

### Validation & Testing (`validation/`)
- **backtester** - Бэктестинг стратегий на исторических данных
- **stress-tester** - Стресс-тестирование в экстремальных условиях
- **strategy-validator** - Валидация торговых стратегий

## 🔧 Технические детали

### Структура агента
Каждый агент включает:
- **name**: Уникальный идентификатор
- **description**: Когда использовать агента с примерами
- **color**: Визуальная идентификация
- **tools**: Специфичные инструменты
- **System prompt**: Детальная экспертиза и инструкции

### Интеграция с системой
Агенты интегрированы с:
- Value Betting Engine
- Research Team
- Risk Management System
- Market Data Sources
- LLM Client

## 📊 Производительность агентов

Отслеживание эффективности через:
- Время выполнения задач
- Точность прогнозов
- Финансовые результаты
- Управление рисками
- Оптимизация стратегий

## 🚦 Статус

- ✅ **Active**: Полностью функциональны и протестированы
- 🚧 **Coming Soon**: В разработке
- 🧪 **Beta**: Тестирование с ограниченной функциональностью

## 💡 Лучшие практики

1. **Позвольте агентам работать вместе** - Многие задачи требуют нескольких агентов
2. **Будьте конкретны** - Четкие описания задач помогают агентам работать лучше
3. **Доверяйте экспертизе** - Агенты созданы для своих специфических областей
4. **Итерируйте быстро** - Агенты поддерживают философию быстрого развития

## 🎁 Бонусные агенты

- **trading-coach** - Координация торговых агентов
- **market-psychologist** - Анализ рыночной психологии
