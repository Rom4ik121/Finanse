# FinWise (finanse)

Кроссплатформенное приложение учёта личных финансов на **Python 3.11+** и **Flet 0.83–0.86**.

Локальное хранение: SQLite + SQLAlchemy. Архитектура: Clean Architecture  
(`domain` → use cases → `infrastructure` → `presentation`).

**Полная документация:** [`docs/README.md`](docs/README.md)

| Раздел | Ссылка |
|--------|--------|
| Архитектура | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Возможности | [docs/FEATURES.md](docs/FEATURES.md) |
| Модель данных | [docs/DATA_MODEL.md](docs/DATA_MODEL.md) |
| Разработка | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Сборка APK/IPA | [docs/BUILD.md](docs/BUILD.md) |
| Codemagic (IPA) | [docs/CODEMAGIC.md](docs/CODEMAGIC.md) |
| Глубокий технический разбор | [docs/DEEP_DIVE.md](docs/DEEP_DIVE.md) |

## Быстрый старт

```powershell
python -m pip install -r requirements.txt
python scripts/migrate.py
python main.py
```

Первый запуск создаёт каталог данных (Windows:  
`%LOCALAPPDATA%\finanse\finanse\`), БД, настройки и счёт «Наличные».

### Демо-данные

```powershell
python scripts/seed_demo_data.py --wipe --scale medium --currency UZS
```

### Тесты

```powershell
python -m pytest -q
```

### APK

```powershell
.\scripts\build_apk.ps1
```

Артефакт: `build/apk/`. Подробности — [docs/BUILD.md](docs/BUILD.md).

## Экраны

Нижняя навигация: **Главная · Операции · Счета · Настройки**.

Дополнительно: аналитика, цели, долги, подписки, валюты.

## Структура

```text
lib/
  core/             # config, database, DI, logging
  domain/           # entities, repositories (ABC), use cases, RateBook
  infrastructure/   # SQLAlchemy, FX API, localization, notifications
  presentation/     # Flet UI
  main.py           # bootstrap
main.py             # entry
scripts/            # migrate, seed_demo_data, build_apk, …
assets/data/        # currencies.json
docs/               # документация
tests/              # unit + integration
```

## Безопасность

- PIN: PBKDF2-hash, экран блокировки при старте.  
- Биометрия: настройки; desktop stub / Windows Hello / mobile `flet-local-auth`.  
- Тесты: `FINANCE_BIOMETRIC_OK=1`, `FINANCE_DISABLE_PUSH=1`.

## Зависимости

См. `requirements.txt` и `pyproject.toml` (`flet`, SQLAlchemy, Pydantic, httpx, matplotlib, reportlab, Alembic, …).




