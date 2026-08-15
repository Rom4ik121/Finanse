# Разработка FinWise

## Требования

- Python **3.11+**
- Windows / macOS / Linux (desktop Flet)
- Для Android-сборки: Android SDK + Flutter (см. [BUILD.md](BUILD.md))

## Установка

```powershell
cd C:\Users\Admin\Desktop\Projects\finanse
python -m pip install -r requirements.txt
# опционально Windows:
python -m pip install -e ".[windows]"
```

Локальное расширение биометрии подключается через `pyproject.toml` → `flet-local-auth = ./extensions/flet_local_auth`.

## Запуск desktop

```powershell
python scripts/migrate.py   # первый раз / после клонирования
python main.py
```

Удобные ярлыки:

- `scripts/launch_finwise.ps1` / `launch_finwise.bat`  
- `scripts/create_desktop_shortcut.ps1`

## Структура репозитория

```text
main.py                 # entry
lib/
  main.py               # bootstrap
  core/                 # config, db, DI, logging
  domain/               # entities, ports, use cases, RateBook
  infrastructure/       # ORM, repos, API, services
  presentation/         # Flet UI
scripts/                # migrate, seed, build, launch
tests/                  # unit + integration
migrations/             # Alembic
assets/                 # currencies.json, icons, splash
docs/                   # эта документация
extensions/             # flet_local_auth
```

## База данных

| Параметр | Значение |
|----------|----------|
| Файл | `%LOCALAPPDATA%\finanse\finanse\finanse.db` |
| URL | `sqlite:///{path}` |
| Init | `init_db()` + индексы + column patches |

Сброс всех данных из UI: Настройки → удалить всё.  
Программно: `DataResetService.wipe_all(session_factory)`.

## Демо-данные (нагрузка)

Закройте приложение, затем:

```powershell
# medium ≈ 2–3k операций за ~2.5 года
python scripts/seed_demo_data.py --wipe --scale medium --currency UZS

# large — больше дней и txs/день
python scripts/seed_demo_data.py --wipe --scale large --currency UZS

# small — быстрее
python scripts/seed_demo_data.py --wipe --scale small
```

Скрипт заливает: счета (UZS/USD/RUB/…), категории, курсы, операции по годам, цели, долги, подписки.

## Тесты

```powershell
python -m pytest -q
```

| Каталог | Содержание |
|---------|------------|
| `tests/unit/` | money, RateBook, i18n, biometric stub, notifications, widgets smoke, … |
| `tests/integration/` | счета, txs, цели, долги, подписки, FX, export, wipe, … |
| `tests/factories.py` | билдеры сущностей |
| `tests/conftest.py` | временная БД на тест, `FINANCE_DISABLE_PUSH=1` |

Запуск подмножества:

```powershell
python -m pytest tests/integration/test_currencies.py -q
```

## Переменные окружения

| Переменная | Эффект |
|------------|--------|
| `FINANCE_DISABLE_PUSH=1` | Не слать OS push |
| `FINANCE_BIOMETRIC_OK=1` | Stub биометрии «успех» в тестах |
| `FLET_PLATFORM` | Платформа Flet (задаётся рантаймом) |
| `PYTHONUTF8=1` | Рекомендуется на Windows для сборки |

## Курсы валют

Источник:

1. Fiat: `https://open.er-api.com/v6/latest/USD`  
2. Crypto: Binance ticker → пробелы CoinGecko  

Провайдер считает всё через USD, пишет пары `base→quote` (+ USD-якоря).  
Конвертер: `ConvertCurrencyUseCase` / `RateBook` — direct, inverse, one-hop pivot.

Обновление:

- фон при старте + по интервалу из настроек;  
- кнопка «Обновить курсы» на экране валют.

## Производительность при больших данных

Сделано:

- RateBook вместо `get_rate` на каждую сумму;  
- пагинация операций + debounce поиска;  
- индексы на `transactions`.

Рекомендации при разработке UI:

- не вызывать `safe_convert` в цикле без `load_rate_book`;  
- не грузить `list_transactions` без `limit` для списков;  
- не строить тысячи Flet-контролов за раз.

## Локализация

Строки: `lib/infrastructure/services/localization.py` → `STRINGS`.  
UI: `tr("key", lang, **kwargs)`.  
Категории-сиды: `localize_category_name(name, lang)`.

Добавление ключа:

```python
"my.key": {"ru": "...", "en": "...", "uz": "..."},
```

## Экспорт и бэкап

- JSON / CSV / PDF — из настроек (`ExportDataUseCase` / export service).  
- Backup SQLite → `{data_dir}/backups/`.  
- Restore — через UI настроек.

## Частые команды

```powershell
# тесты
python -m pytest -q

# миграция + seed справочников
python scripts/migrate.py

# демо
python scripts/seed_demo_data.py --wipe --scale medium --currency UZS

# APK
.\scripts\build_apk.ps1

# push на GitHub
.\scripts\push_github.ps1
```

## Стиль кода

- Use cases async; репозитории sync SQLAlchemy через `asyncio.to_thread`.  
- Flet Icons: `.icon =`, не `.name`.  
- Не коммитить `.env` с секретами; не коммитить `__pycache__` / локальную БД.  
- Коммиты — только по явной просьбе пользователя.
