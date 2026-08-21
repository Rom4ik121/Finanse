# Архитектура FinWise

## 1. Обзор

**FinWise** — кроссплатформенное приложение для учёта личных финансов
(доходы, расходы, счета, цели, долги, подписки, бюджеты, мультивалютность).
Реализовано на **Python + Flet** (UI-фреймворк поверх Flutter), работает на
Windows, Android и iOS (через `flet run --android/--ios/--web`).

Код организован по принципам **чистой архитектуры** (Clean Architecture):

```
main.py                     — точка входа (запускает lib.main.run)
lib/
├── core/                   — конфигурация, БД, DI-контейнер, логирование, палитра
├── domain/                 — бизнес-логика (сущности, репозитории, use cases)
├── infrastructure/         — SQLAlchemy, HTTP-клиенты, сервисы (push, биометрия, экспорт)
└── presentation/           — Flet UI (страницы, виджеты, состояние, темы, i18n)
```

Зависимости направлены **внутрь**: `presentation` → `domain` → (интерфейсы),
`infrastructure` реализует интерфейсы `domain.repositories` и подключается
через DI-контейнер (`lib/core/dependencies.py`).

## 2. Слои и их ответственность

### 2.1 `lib/core` — ядро приложения

| Файл | Назначение |
|---|---|
| `config.py` | Константы (валюта по умолчанию, категории, иконки, палитра), класс `AppConfig` (пути к данным, БД, бэкапам, экспорту, логам) |
| `database.py` | SQLAlchemy engine/session factory, `Base`, `init_db()`, `reset_engine()`, патчи колонок для SQLite |
| `dependencies.py` | DI-контейнер `Container` и фабрика `build_container()` |
| `logging_config.py` | `setup_logging()` — консоль + файл, тихие сторонние логгеры |
| `color_palette.py` | Генерация палитры цветов (HSL→HEX) для счетов и категорий |

### 2.2 `lib/domain` — бизнес-логика

- **`entities/`** — Pydantic-модели:
  - `Account` — счёт (баланс, валюта, иконка, цвет)
  - `Transaction` — операция (доход/расход/перевод, теги, связи с целью/долгом/подпиской)
  - `Category`, `CategoryKind` — категории (income/expense/both)
  - `Currency`, `ExchangeRate` — валюты и курсы
  - `Goal` — цель накопления (с прогрессом и проекцией)
  - `Debt` — долг/заём (направление, проценты, статус)
  - `Subscription` — подписка (периодичность, автоплатежи)
  - `Budget`, `BudgetProgress` — месячный лимит по категории
  - `AppSettings` — настройки (тема, язык, валюта, напоминания, PIN/биометрия)
  - `Money` — хелперы квантования (`quantize_money`, `quantize_rate`)
  - `currency_codes.py` — нормализация кодов валют (алиасы: ₽→RUB, $→USD и т.д.)

- **`repositories/`** — абстрактные порты (ABC) для персистентности:
  `AccountRepository`, `TransactionRepository`, `GoalRepository`,
  `DebtRepository`, `SubscriptionRepository`, `CurrencyRepository`,
  `CategoryRepository`, `SettingsRepository`, `BudgetRepository`, `Repository<T, ID>`.

- **`use_cases/`** — сценарии приложения (все асинхронные):
  - `transactions.py` — добавление/обновление/удаление операций, статистика, переводы между счетами
  - `accounts.py` — CRUD счетов, пересчёт баланса
  - `goals.py` — CRUD целей, взносы, проекция (прогноз), дублирование, архивация
  - `debts.py` — CRUD долгов, погашение, расчёт процентов, проекция
  - `subscriptions.py` — CRUD подписок, обработка наступивших платежей, аналитика
  - `currencies.py` — обновление курсов, конвертация, список валют
  - `budgets.py` — установка лимитов, прогресс, пересчёт потраченного, алерты
  - `categories.py` — CRUD категорий, `find_or_create`
  - `settings.py` — чтение/сохранение настроек
  - `export_data.py` — экспорт всех данных в JSON
  - `align_currencies.py` — выравнивание валюты единственного счёта под базовую

- **`services/rate_book.py`** — in-memory книга курсов (`RateBook`) с кэшем
  и конвертацией через прямые/обратные/промежуточные пары.

### 2.3 `lib/infrastructure` — реализация портов

- **`db_models.py`** — SQLAlchemy 2.0 ORM-модели (таблицы: `accounts`,
  `transactions`, `goals`, `debts`, `subscriptions`, `currencies`,
  `exchange_rates`, `categories`, `settings`, `budgets`).
- **`repositories/`** — SQLAlchemy-реализации репозиториев
  (`SqlAlchemy*Repository`), работают через `asyncio.to_thread` + `session_scope`.
- **`services/`**:
  - `backup_service.py` — бэкап/восстановление SQLite (с WAL-сайдкарами)
  - `export_service.py` — экспорт CSV и PDF-отчёта (reportlab)
  - `encryption_service.py` — хэширование PIN (PBKDF2), биометрия
  - `biometric.py` — провайдер биометрии (Windows Hello / local_auth / env-оверрайд)
  - `notification_service.py` — in-app уведомления (очередь сообщений)
  - `push_notifier.py` — OS push (Android через `flet_android_notifications`)
  - `reminder_scheduler.py` — планировщик напоминаний (долги, подписки, цели)
  - `exchange_rate_provider.py` — агрегатор курсов (fiat + crypto)
  - `localization.py` — словарь переводов ru/en/uz + `t()`/`tr()`
  - `data_reset_service.py` — полная очистка таблиц
- **`api/`**:
  - `exchange_rate_client.py` — fiat-курсы (open.er-api.com)
  - `crypto_rate_client.py` — крипто-курсы (CoinGecko)
  - `binance_rate_client.py` — крипто-курсы (Binance ticker)

### 2.4 `lib/presentation` — UI (Flet)

- **`app.py`** — корневой контроллер `FinanseApp`: плавающая навигация,
  кэш страниц, PIN-гейт (LockScreen), переключение primary/secondary.
- **`state/app_state.py`** — `AppState`: Observer-паттерн, токены обновления
  страниц, настройки, маршруты.
- **`pages/`** — страницы: `dashboard`, `transactions`, `accounts`,
  `account_detail`, `analytics`, `goals`, `debts`, `subscriptions`,
  `currencies`, `budgets`, `settings`.
- **`widgets/`** — переиспользуемые виджеты: `AccountCard`, `TransactionTile`,
  `GoalProgress`, `DebtCard`, `SubscriptionCard`, `SummaryCard`, `EmptyState`,
  `Loading`, `ConfirmDialog`, `FullscreenForm`, `QuickAddSheet`,
  `TransferSheet`, `CategoryPicker`, `CurrencyTickerPicker`, `DateTimeField`,
  `AppearancePicker`, `LockScreen`, `SplashScreen`, `PullToRefresh`, `Charts`.
- **`theme.py` / `styles.py`** — темы (light/dark), карточки, кнопки, бейджи.
- **`utils.py`** — `format_money`, `format_date`, `run_async`, `snack`, `tr`,
  `load_rate_book`, `safe_update`.
- **`icon_registry.py` / `account_icons.py`** — маппинг ключей иконок → Flet Icons,
  глифы валют/крипто.
- **`money_input.py`** — поле ввода денег с группировкой разрядов и парсером.
- **`analytics_period.py` / `account_stats.py`** — пресеты периодов и агрегация.
- **`notification_badges.py`** — бейджи уведомлений на дашборде.

## 3. Поток запуска

1. `main.py` → `lib.main.run()`.
2. `run()` настраивает логирование, нормализует `FLET_*` env, вызывает
   `ft.run(_flet_main, ...)` (desktop/web/mobile/hidden).
3. `_flet_main(page)`:
   - показывает сплэш-экран;
   - регистрирует биометрию (`register_local_auth_service`) и Android-push;
   - `get_default_config()` → `setup_logging()` → `init_db()` → `build_container()`;
   - `_seed_if_needed()` — сид валют, настроек, дефолтного счёта;
   - запускает фоновые задачи: `_exchange_rate_loop` (курсы) и `_reminder_loop`
     (ежедневные напоминания);
   - обрабатывает наступившие подписки и планирует напоминания;
   - монтирует `FinanseApp`.

## 4. DI-контейнер

`Container` (dataclass) хранит репозитории, сервисы и use cases.
`build_container()` импортирует реализации инфраструктуры и собирает граф
зависимостей. Если модуль недоступен — слот остаётся `None`, имя попадает в
`container.missing`, ошибка — в `container.errors`. Это позволяет частичную
сборку при инкрементальной разработке.

`container.require(name)` бросает `RuntimeError`, если зависимость не собрана.
`container.rebind_session_factory(factory)` перенаправляет все репозитории на
новую фабрику сессий (используется после восстановления БД).

## 5. База данных

- SQLite (путь из `AppConfig.db_path`), WAL-режим, `PRAGMA foreign_keys=ON`.
- `init_db()` создаёт таблицы через `Base.metadata.create_all` и применяет
  патчи колонок для существующих БД (`_apply_sqlite_column_patches`).
- Миграции Alembic (9 версий) — см. `migrations/`; `env.py` резолвит URL из
  конфигурации приложения.
- Репозитории используют `session_scope` (commit/rollback/close) и
  `asyncio.to_thread` для неблокирующего доступа.

## 6. Мультивалютность и курсы

- Базовая валюта — из настроек (`default_currency`).
- Курсы: fiat (open.er-api.com) + крипто (CoinGecko, Binance), агрегируются
  в `HttpExchangeRateProvider`, сохраняются в `exchange_rates`.
- Конвертация: `RateBook` (in-memory кэш) или `ConvertCurrencyUseCase`
  (прямые пары → обратные → через USD-пивот).
- Слабая валюта (UZS) не округляется в 0: курсы хранятся с 12 знаками,
  квантование `quantize_rate` — 8 знаков.

## 7. Уведомления и напоминания

- `NotificationService` — in-app очередь сообщений (title/body/kind/related_id).
- `PushNotifier` — OS-уведомления (Android через `flet_android_notifications`,
  Windows — winotify; отключаются env `FINANCE_DISABLE_PUSH=1`).
- `ReminderScheduler` — напоминания о долгах, подписках, целях (off-track).
- Фоновый цикл `_reminder_loop` срабатывает в `reminder_time` (HH:MM) раз в день.
- Бейджи на дашборде считаются через `notification_badges.py`.

## 8. Безопасность

- PIN: `EncryptionService.hash_pin()` (PBKDF2 + соль), хранится в `settings`
  (`pin_hash`, `pin_salt`).
- Биометрия: Windows Hello (winrt), мобильный `local_auth` (расширение
  `extensions/flet_local_auth`), env-оверрайд `FINANCE_BIOMETRIC_OK=1` для тестов.
- LockScreen показывается при старте, если задан PIN.

## 9. Экспорт и бэкап

- JSON: `ExportDataUseCase` (все сущности + курсы + настройки).
- CSV: `ExportService.export_transactions_csv`.
- PDF: `ExportService.export_summary_pdf` (reportlab).
- Бэкап: `BackupService` — копия `.db` + `-wal`/`-shm` в `backup_dir`,
  восстановление с опциональной safety-копией.

## 10. Тестирование

- `pytest` (конфиг в `pytest.ini`, `testpaths=tests`).
- `tests/conftest.py` — фикстуры: изолированный `container` (SQLite в tmp),
  `run_async`, отключение OS-push.
- `tests/factories.py` — фабрики сущностей.
- `tests/unit/` — юнит-тесты (money, budget, биометрия, шифрование,
  локализация, бэкап, виджеты и др.).
- `tests/integration/` — интеграционные тесты (счета, операции, переводы,
  цели, долги, подписки, бюджеты, валюты, экспорт).

## 11. Скрипты

| Скрипт | Назначение |
|---|---|
| `scripts/migrate.py` | Инициализация БД + сид валют/настроек/счёта |
| `scripts/seed_demo_data.py` | Генерация демо-данных (--wipe, --scale, --currency) |
| `scripts/build_apk.ps1` | Сборка Android APK |
| `scripts/build_ipa.sh` | Сборка iOS IPA |
| `scripts/launch_finwise.bat/.ps1` | Запуск приложения |
| `scripts/create_desktop_shortcut.ps1` | Ярлык на рабочем столе |
| `scripts/generate_branding_assets.py` | Генерация иконок/сплэшей |
| `scripts/push_github.ps1` | Публикация в GitHub |
| `scripts/patch_android_desugar.py` | Патч desugar для Android |

## 12. CI/CD

- `codemagic.yaml` — сборка iOS/Android в Codemagic.
- `.github/workflows/build-ios.yml` — GitHub Actions для iOS.
- `flet.toml` — конфигурация Flet (разрешения Android, splash, iOS Info.plist).