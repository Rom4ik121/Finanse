# KODA.md — Контекст проекта FinWise (finanse)

## Обзор проекта

**FinWise** — кроссплатформенное приложение учёта личных финансов. Написано на **Python 3.11+** с использованием UI-фреймворка **Flet 0.83–0.86**. Данные хранятся локально в **SQLite** через **SQLAlchemy 2.x**. Поддерживаются десктоп (Windows / macOS / Linux), Android (APK) и iOS (IPA).

### Назначение

Приложение позволяет вести учёт доходов и расходов, управлять счетами, целями, долгами, подписками и бюджетами. Поддерживается мультивалютность с автоматическим обновлением курсов (fiat через open.er-api.com, крипта через Binance), локализация (русский / английский / узбекский), аналитика с графиками, экспорт данных (JSON / CSV / PDF), резервное копирование и защита данных (PIN-код с PBKDF2-хэшированием, биометрия).

### Архитектура

Проект следует **Clean Architecture**. Зависимости направлены внутрь: `presentation → use_cases → entities/ports ← infrastructure`.

```
lib/
  core/             # конфигурация, БД, DI-контейнер, логирование
  domain/           # сущности, репозитории (ABC), use cases, RateBook
    entities/       # Account, Transaction, Goal, Debt, Subscription, Currency, …
    repositories/   # абстрактные контракты (без SQLAlchemy)
    use_cases/      # CRUD + бизнес-логика (async)
    services/       # RateBook — конвертация валют в памяти
  infrastructure/   # SQLAlchemy ORM, HTTP FX API, локализация, уведомления, шифрование
    db_models.py    # ORM-модели
    repositories/   # реализации репозиториев на SQLAlchemy
    api/            # клиенты курсов валют (er-api, Binance, CoinGecko)
    services/       # localization, encryption, biometric, notifications, backup, export
  presentation/     # Flet UI
    app.py          # оболочка: 4 вкладки, вторичные экраны, блокировка
    state/          # AppState — язык, тема, валюта, токены обновления
    pages/          # экраны (dashboard, transactions, accounts, settings, analytics, …)
    widgets/        # карточки, графики, splash, lock, quick-add
    i18n/           # локализация UI
    utils.py        # tr(), format_money(), safe_convert(), load_rate_book()
  main.py           # bootstrap: логирование → БД → DI → фоновые задачи → Flet
main.py             # точка входа
```

### Ключевые технологии

| Категория | Технологии |
|-----------|------------|
| Язык | Python 3.11+ |
| UI | Flet 0.83–0.86 |
| БД | SQLite + SQLAlchemy 2.x + Alembic (миграции) |
| Валидация | Pydantic 2.x |
| HTTP | httpx |
| Графики | matplotlib |
| Отчёты | reportlab |
| Уведомления | flet-android-notifications, winotify (Windows) |
| Биометрия | flet-local-auth (собственное расширение в `extensions/`) |
| Тесты | pytest 8.x |

## Сборка и запуск

### Установка зависимостей

```powershell
python -m pip install -r requirements.txt
# опционально (Windows-специфичные пакеты):
python -m pip install -e ".[windows]"
```

### Миграция БД

```powershell
python scripts/migrate.py
```

### Запуск (десктоп)

```powershell
python main.py
```

Удобные ярлыки: `scripts/launch_finwise.ps1`, `scripts/launch_finwise.bat`.

### Демо-данные

```powershell
python scripts/seed_demo_data.py --wipe --scale medium --currency UZS
```

Масштабы: `small`, `medium` (~2–3k операций), `large`.

### Тесты

```powershell
python -m pytest -q                                    # все тесты
python -m pytest tests/unit/ -q                        # только модульные
python -m pytest tests/integration/test_currencies.py  # конкретный файл
```

### Сборка APK (Android)

```powershell
.\scripts\build_apk.ps1
```

Артефакт: `build/apk/`.

### Прочие скрипты

| Скрипт | Назначение |
|--------|------------|
| `scripts/migrate.py` | Применение Alembic-миграций |
| `scripts/seed_demo_data.py` | Генерация демо-данных |
| `scripts/build_apk.ps1` | Сборка Android APK |
| `scripts/build_ipa.sh` | Сборка iOS IPA (требуется macOS + Xcode) |
| `scripts/push_github.ps1` | Push в GitHub |
| `scripts/create_desktop_shortcut.ps1` | Ярлык на рабочем столе |
| `scripts/generate_branding_assets.py` | Генерация иконок / splash |

## Структура базы данных

| Параметр | Значение |
|----------|----------|
| Файл | `%LOCALAPPDATA%\finanse\finanse\finanse.db` (Windows) |
| URL | `sqlite:///{path}` |
| Режим | WAL |
| Миграции | Alembic, 9 версий (`migrations/versions/0001`–`0009`) |

Индексы: `(date)`, `(account_id, date)`, `(type, date)`, `(category, date)` на таблице `transactions`.

## Правила разработки

### Стиль кода

- **Use cases — async**; репозитории — sync SQLAlchemy, вызываются через `asyncio.to_thread`.
- Сущности — Pydantic `BaseModel` с `ConfigDict(from_attributes=True)`.
- Денежные суммы — `Decimal` с квантизацией `0.01`; курсы — до 14 знаков.
- Flet-иконки: использовать `.icon =`, не `.name`.
- Локализация: `tr("key", lang, **kwargs)`; строки в `lib/infrastructure/services/localization.py` → `STRINGS` (ru / en / uz).
- Конфигурация: `AppConfig` (dataclass, `slots=True`) в `lib/core/config.py`.
- DI: `build_container(config)` создаёт `Container` с репозиториями, use cases и сервисами; presentation получает контейнер через `AppState`.

### Тестирование

- Тесты в `tests/unit/` (модульные) и `tests/integration/` (интеграционные с временной БД).
- `tests/conftest.py` создаёт изолированный `Container` с временной SQLite-БД на каждый тест.
- `tests/factories.py` — билдеры сущностей для тестов.
- Фикстура `async_run` запускает корутины без `pytest-asyncio`.
- Переменная `FINANCE_DISABLE_PUSH=1` отключает OS-уведомления в тестах (устанавливается автоматически через `autouse`-фикстуру).
- `FINANCE_BIOMETRIC_OK=1` — stub биометрии «успех».

### Производительность

- `RateBook` загружает все курсы одним запросом и конвертирует в памяти (не вызывает `get_rate` на каждую сумму).
- Пагинация списка операций (по 60 + «Показать ещё»).
- Debounce поиска ~350 мс.
- Не вызывать `safe_convert` в цикле без `load_rate_book`.
- Не грузить `list_transactions` без `limit` для списков.
- Не строить тысячи Flet-контролов за раз.

### Безопасность

- PIN: PBKDF2-хэш, экран блокировки при старте.
- Биометрия: Windows Hello / mobile `flet-local-auth` / desktop stub.
- Не коммитить `.env` с секретами, `__pycache__`, локальную БД.
- Коммиты — только по явной просьбе пользователя.

### Переменные окружения

| Переменная | Эффект |
|------------|--------|
| `FINANCE_DISABLE_PUSH=1` | Отключить OS push-уведомления |
| `FINANCE_BIOMETRIC_OK=1` | Stub биометрии «успех» |
| `FLET_VIEW` | Платформа Flet (`web`, `android`, `ios`, `desktop`, `hidden`) |
| `FLET_HOST` / `FLET_PORT` | Хост и порт для web/mobile режима |
| `PYTHONUTF8=1` | Рекомендуется на Windows для сборки |

### Навигация в приложении

**Нижняя панель (4 вкладки):** Главная · Операции · Счета · Настройки.

**Вторичные экраны:** Аналитика · Цели · Долги · Подписки · Валюты.

Обновление списков: `AppState.bump_refresh("dashboard" | "accounts" | …)` + подписки страниц на токены.

### Фоновые задачи

| Цикл | Поведение |
|------|-----------|
| Обновление курсов | Периодически `UpdateExchangeRatesUseCase` (интервал из настроек, по умолчанию 60 мин) |
| Напоминания | Ежедневно около `reminder_time` — долги / подписки → очередь + OS push |

### Денежные потоки

```
AddTransaction
  → создать tx
  → изменить balance счёта
  → если goal_id: увеличить current_amount цели
  → если debt_id: уменьшить remaining_amount долга
```

Взносы в цели и погашение долгов — только со счетов **той же** валюты. Cross-currency-конвертация для дашборда / аналитики — через `RateBook` в базовую валюту настроек.

## Документация

Подробная документация в `docs/`:

| Файл | Содержание |
|------|------------|
| `ARCHITECTURE.md` | Архитектура Clean Architecture, слои, DI, навигация |
| `FEATURES.md` | Возможности приложения |
| `DATA_MODEL.md` | Модель данных |
| `DEVELOPMENT.md` | Разработка, тесты, переменные окружения, стиль кода |
| `BUILD.md` | Сборка APK / IPA |
| `CODEMAGIC.md` | CI/CD через Codemagic |
| `DEEP_DIVE.md` | Глубокий технический разбор |
