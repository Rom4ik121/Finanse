# Архитектура FinWise

## Обзор

Приложение следует **Clean Architecture**: домен не зависит от UI и БД; инфраструктура реализует порты; presentation вызывает use cases через DI-контейнер.

```text
┌─────────────────────────────────────────┐
│              presentation               │  Flet UI, AppState, pages, widgets
├─────────────────────────────────────────┤
│               use cases                 │  lib/domain/use_cases
├─────────────────────────────────────────┤
│     entities  +  repository ports       │  lib/domain/entities, repositories
├─────────────────────────────────────────┤
│             infrastructure              │  SQLAlchemy, HTTP FX, services
├─────────────────────────────────────────┤
│                 core                    │  config, database, DI, logging
└─────────────────────────────────────────┘
```

Зависимости направлены **внутрь**: presentation → use cases → entities/ports ← infrastructure.

## Точка входа

1. `main.py` → `lib.main.run()`
2. Логирование (`lib/core/logging_config.py`)
3. `get_default_config()` → каталог данных пользователя
4. `init_db` + `build_container(...)`
5. Seed: валюты JSON, настройки, счёт «Наличные» при пустой БД
6. Фоновые циклы: обновление курсов, напоминания
7. Flet: `FinanseApp` (`lib/presentation/app.py`)

## Слои

### `lib/core`

| Модуль | Назначение |
|--------|------------|
| `config.py` | `AppConfig`, пути, дефолты валюты/языка/темы, сиды категорий и иконок |
| `database.py` | Engine, session factory, `init_db`, SQLite WAL, патчи колонок, индексы |
| `dependencies.py` | `Container`, `build_container()` — wiring репозиториев и use cases |
| `logging_config.py` | Логи в `{data_dir}/logs/finanse.log` |

### `lib/domain`

**Entities** (`entities/`): Account, Transaction, Goal, Debt, Subscription, Currency, ExchangeRate, Category, AppSettings, money helpers, `currency_codes`.

**Repository ABC** (`repositories/`): контракты без SQLAlchemy.

**Use cases** (`use_cases/`):

- счета: create / update / delete / list / recalculate balance  
- операции: add / update / delete / list / stats  
- цели: CRUD + contribute  
- долги: CRUD + repay + interest  
- подписки: CRUD + process due (catch-up по периодам)  
- валюты: update rates, convert, list  
- категории, настройки, export, align currencies  

**Domain service**: `RateBook` (`services/rate_book.py`) — конвертация в памяти (прямой / обратный / cross через USD и др. pivots) без тысяч запросов к БД.

### `lib/infrastructure`

| Область | Модули |
|---------|--------|
| ORM | `db_models.py` |
| Репозитории | `repositories/*_repository.py` |
| FX API | `api/exchange_rate_client.py` (open.er-api.com), `binance_rate_client.py`, `crypto_rate_client.py` |
| FX provider | `services/exchange_rate_provider.py` — fiat + crypto → USD anchor |
| Локализация | `services/localization.py` (ru/en/uz) |
| Безопасность | `encryption_service.py` (PIN PBKDF2), `biometric.py` |
| Уведомления | `notification_service.py`, `push_notifier.py`, `reminder_scheduler.py` |
| Данные | `backup_service.py`, `export_service.py`, `data_reset_service.py` |

### `lib/presentation`

| Модуль | Назначение |
|--------|------------|
| `app.py` | Оболочка: 4 вкладки, secondary routes, lock |
| `state/app_state.py` | Язык, тема, base currency, refresh tokens, unlock |
| `pages/*` | Экраны |
| `widgets/*` | Карточки, графики, splash, lock, quick-add, fullscreen forms |
| `utils.py` | `tr`, `format_money`, `safe_convert`, `load_rate_book`, `run_async` |
| `theme.py`, `styles.py` | Тема Material 3 / визуальные хелперы |

## Навигация

**Нижняя панель (4 вкладки):**

1. Главная (`dashboard`)  
2. Операции (`transactions`)  
3. Счета (`accounts`)  
4. Настройки (`settings`)  

**Вторичные экраны** (поверх / вместо контента, с «Назад»):

- `analytics` — аналитика  
- `goals` — цели  
- `debts` — долги  
- `subscriptions` — подписки  
- `currencies` — валюты  

Обновление списков: `AppState.bump_refresh("dashboard" | "accounts" | …)` + подписки страниц на токены.

## DI-контейнер

`build_container(config)` создаёт:

- репозитории (SQLAlchemy session factory)  
- HTTP FX provider  
- все use cases (`create_account`, `add_transaction`, `convert_currency`, …)  
- сервисы уведомлений / биометрии при наличии  

Presentation получает `container` через `AppState` и вызывает `await container.<use_case>.execute(...)`.

## Денежные потоки (кратко)

```text
AddTransaction
  → создать tx
  → изменить balance счёта
  → если goal_id: увеличить current_amount цели
  → если debt_id: уменьшить remaining_amount долга
```

Contribute / Repay — обёртки, создающие expense/income с нужными связями.

**Валюта:** суммы в одной валюте складываются 1:1. Cross-currency:

- дашборд / аналитика / итоги — через `RateBook` в базовую валюту настроек;  
- взносы в цели и погашение долгов — только со счетов **той же** валюты (защита от смешения единиц).

## Фоновые задачи

| Цикл | Поведение |
|------|-----------|
| Exchange rates | Периодически `UpdateExchangeRatesUseCase` (интервал из настроек, по умолчанию 60 мин) |
| Reminders | Ежедневно около `reminder_time` — долги / подписки → очередь + OS push |

Отключение push в тестах: `FINANCE_DISABLE_PUSH=1`.

## Производительность (важные решения)

1. **RateBook** — один `list_rates()` + конвертация в CPU на аналитике и итогах.  
2. **Пагинация** списка операций (по 60 + «Показать ещё»).  
3. **Debounce** поиска ~350 мс.  
4. **Индексы** SQLite: `(date)`, `(account_id, date)`, `(type, date)`, `(category, date)`.  

Подробнее — в [DEVELOPMENT.md](DEVELOPMENT.md).
