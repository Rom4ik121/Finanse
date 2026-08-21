# FinWise — Полная документация

> Кроссплатформенное приложение для учёта личных финансов (Python + Flet).
> Windows · Android · iOS

## Документация

| Раздел | Файл | Содержание |
|---|---|---|
| Архитектура | [ARCHITECTURE.md](ARCHITECTURE.md) | Обзор, слои, поток запуска, DI, БД, мультивалютность, уведомления, безопасность, экспорт, CI/CD |
| Сущности | [ENTITIES.md](ENTITIES.md) | Account, Transaction, Category, Currency, Goal, Debt, Subscription, Budget, AppSettings, Money |
| Use Cases | [USE_CASES.md](USE_CASES.md) | Все сценарии: транзакции, счета, цели, долги, подписки, валюты, бюджеты, категории, настройки, экспорт |
| Инфраструктура | [INFRASTRUCTURE.md](INFRASTRUCTURE.md) | SQLAlchemy-репозитории, API-клиенты, сервисы (бэкап, экспорт, шифрование, биометрия, push, напоминания), ORM-модели |
| Презентация | [PRESENTATION.md](PRESENTATION.md) | Навигация, состояние, страницы, виджеты, утилиты, темы, иконки, локализация |
| База данных | [DATABASE.md](DATABASE.md) | SQLite, все таблицы с колонками, миграции Alembic (9 версий) |
| Тестирование | [TESTING.md](TESTING.md) | Запуск, фикстуры, фабрики, список юнит/интеграционных тестов |

## Быстрый старт

### Установка зависимостей

```bash
pip install -r requirements.txt
pip install -e ./extensions/flet_local_auth
```

### Запуск (desktop)

```bash
python main.py
# или
flet run main.py
```

### Запуск (Android/iOS/Web)

```bash
flet run --android main.py
flet run --ios main.py
flet run --web --host 0.0.0.0 --port 8550 main.py
```

### Миграция БД + сид

```bash
python scripts/migrate.py
```

### Демо-данные

```bash
python scripts/seed_demo_data.py --wipe --scale medium --currency UZS
```

### Тесты

```bash
pytest
```

## Технологии

- **Python 3.12+**, **Flet ≥0.83** (UI)
- **SQLAlchemy 2.0** (ORM), **SQLite** (БД), **Alembic** (миграции)
- **Pydantic v2** (сущности)
- **httpx** (HTTP-клиенты), **matplotlib** (графики), **reportlab** (PDF)
- **platformdirs** (пути), **winrt** (Windows Hello), **winotify** (Windows push)
- **flet_android_notifications** (Android push)
- **pytest** (тесты)

## Структура проекта

```
finanse/
├── main.py                          — точка входа
├── pyproject.toml / requirements.txt — зависимости
├── flet.toml                        — конфигурация Flet
├── alembic.ini                      — конфигурация Alembic
├── pytest.ini                       — конфигурация pytest
├── assets/                          — иконки, сплэши, currencies.json
├── docs/                            — документация (этот каталог)
├── extensions/flet_local_auth/      — расширение биометрии
├── lib/
│   ├── main.py                      — bootstrap (логирование, БД, DI, фон)
│   ├── core/                        — config, database, dependencies, logging
│   ├── domain/                      — entities, repositories (ABC), use_cases, services
│   ├── infrastructure/              — db_models, repositories (SQLAlchemy), services, api
│   └── presentation/                — app, state, pages, widgets, theme, styles, utils, i18n
├── migrations/                      — Alembic (env.py + 9 версий)
├── scripts/                         — migrate, seed_demo, build_apk/ipa, launch
└── tests/                           — conftest, factories, unit/, integration/
```

## Лицензия

Проект FinWise.