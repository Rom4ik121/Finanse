# Инфраструктурный слой

## Репозитории (SQLAlchemy)

Все `SqlAlchemy*Repository` реализуют абстрактные порты из `lib/domain/repositories/`
и работают через `asyncio.to_thread` + `session_scope` (commit/rollback/close).

| Репозиторий | Таблица | Особенности |
|---|---|---|
| `SqlAlchemyAccountRepository` | accounts | CRUD, list(active_only) |
| `SqlAlchemyTransactionRepository` | transactions | CRUD, list() с фильтрами, теги фильтруются в Python |
| `SqlAlchemyGoalRepository` | goals | CRUD, list(status/currency/min_priority), сортировка (priority/deadline/progress/created_at) |
| `SqlAlchemyDebtRepository` | debts | CRUD, list(status/direction/currency), сортировка (due_date/remaining/amount/interest/created_at/counterparty/status) |
| `SqlAlchemySubscriptionRepository` | subscriptions | CRUD, list(active_only/account_id/status), list_due(as_of) |
| `SqlAlchemyCurrencyRepository` | currencies + exchange_rates | upsert, list, seed_from_json |
| `SqlAlchemyCategoryRepository` | categories | CRUD, find_or_create, get_by_name (case-insensitive для кириллицы) |
| `SqlAlchemySettingsRepository` | settings | get/update, PIN-credentials |
| `SqlAlchemyBudgetRepository` | budgets | save, delete, update_spent, delete_for_category, reassign_category |

## API-клиенты

| Клиент | Источник | Метод | Описание |
|---|---|---|---|
| `ExchangeRateClient` | open.er-api.com | `fetch_latest(base)` | Fiat-курсы относительно base |
| `CryptoRateClient` | CoinGecko | `fetch_prices(symbols)` | Крипто-цены в USD |
| `BinanceRateClient` | Binance | `fetch_prices(symbols)` | Крипто-цены в USDT≈USD |

Все клиенты — асинхронные, с таймаутами и обработкой ошибок. Поддерживают
внедрение собственного `httpx.AsyncClient` (для тестов) и `aclose()`.

## Сервисы

### BackupService
- `backup(label?)` — копия `.db` + `-wal`/`-shm` в `backup_dir` с таймстампом.
- `restore(path, make_safety_copy=True)` — восстановление (с опциональной safety-копией).
- `list_backups()`, `delete_backup(path)`.
- Ошибки → `BackupServiceError`.

### ExportService
- `export_transactions_csv(txs)` — CSV всех операций.
- `export_summary_pdf(accounts, transactions, goals, debts, subscriptions, title)` —
  PDF-отчёт (reportlab) с разделами: счета, операции, цели, долги, подписки.

### EncryptionService
- `hash_pin(pin)` → `PinCredentials(pin_hash, pin_salt)` (PBKDF2).
- `verify_pin(pin, pin_hash, pin_salt)` → bool.
- Биометрия: `refresh_biometric_status()`, `biometric_available()`,
  `authenticate_biometric(message)`.

### Biometric
- `probe_biometric_status()` → `BiometricStatus` (AVAILABLE, NOT_CONFIGURED,
  DEVICE_NOT_PRESENT, UNSUPPORTED, DISABLED_BY_POLICY, DEVICE_BUSY).
- `request_biometric_verification(message)` → `BiometricResult`.
- `register_local_auth_service(page)` — подключает расширение `flet_local_auth`.
- env-оверрайд `FINANCE_BIOMETRIC_OK=1` — принудительно AVAILABLE/VERIFIED (тесты).
- Windows: winrt `UserConsentVerifier` (Windows Hello). Мобильные: local_auth.

### NotificationService
- In-app очередь сообщений: `push(title, body, kind, related_id)`, `list_all`,
  `list_pending`, `mark_read`, `list_due`.
- `NotificationKind`: BUDGET_ALERT, DEBT_REMINDER, SUBSCRIPTION_REMINDER,
  GOAL_OFF_TRACK, GOAL_MILESTONE и др.

### PushNotifier
- `request_push_permissions()` — запрос разрешений.
- `register_android_notifications(page)` — Android push через `flet_android_notifications`.
- Windows: winotify. Отключение: env `FINANCE_DISABLE_PUSH=1`.

### ReminderScheduler
- `schedule_reminders(container, settings, language)` — создаёт напоминания о
  долгах (за `reminder_days` до due), подписках (за `reminder_days`),
  целях off-track.

### ExchangeRateProvider
- `HttpExchangeRateProvider` — агрегирует fiat (open.er-api) + crypto
  (CoinGecko/Binance), строит пары base→quote и обратные, сохраняет в БД.

### DataResetService
- `wipe_all(session_factory)` — удаляет все строки из всех таблиц (в обратном
  порядке FK).

## ORM-модели (`db_models.py`)

| Таблица | Ключевые поля |
|---|---|
| `accounts` | name, currency, balance, initial_balance, icon, color, is_active |
| `transactions` | account_id(FK), amount, category, tags(JSON), date, type, currency, goal_id, debt_id, subscription_id, transfer_id, goal/debt_credit_amount |
| `goals` | name, target/current_amount, currency, deadline, priority, category_link, status, is_completed, cached_projection |
| `debts` | counterparty, amount, remaining_amount, currency, direction, status, interest_rate, due_date, started_at |
| `subscriptions` | name, amount, currency, account_id(FK), category, periodicity, custom_interval_days, start/end_date, max_payments, payments_made, next_billing_date, status, auto_charge |
| `currencies` | code(PK), name, name_ru, name_en, symbol, is_crypto |
| `exchange_rates` | base, quote, rate(Numeric(24,12)), updated_at; UNIQUE(base,quote) |
| `categories` | name(UNIQUE), icon, color, kind, is_system, is_active |
| `settings` | id="default", default_currency, theme, language, интервалы, флаги уведомлений, reminder_time/days, pin_hash, pin_salt, biometric_enabled, budget_alerts |
| `budgets` | category_id(FK→categories.name), month, year, amount_limit, spent, last_alert_level; UNIQUE(category_id,month,year) |