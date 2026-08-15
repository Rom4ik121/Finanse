# Модель данных

Персистентность: **SQLite** файл `{data_dir}/finanse.db`. ORM: SQLAlchemy 2 (`lib/infrastructure/db_models.py`). Доменные сущности: Pydantic (`lib/domain/entities/`).

## ER (упрощённо)

```text
Account 1──* Transaction
Account 1──* Subscription
Goal 1──* Transaction          (goal_id, optional)
Debt 1──* Transaction          (debt_id, optional)
Currency (справочник)
ExchangeRate (base, quote) UNIQUE
Category (name UNIQUE)
Settings (singleton id='default')
```

## Сущности

### Account

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID str | PK |
| name | str | Название |
| currency | str | Код валюты |
| balance | Decimal(18,2) | Текущий баланс |
| initial_balance | Decimal | Стартовый |
| icon, color | str | UI |
| is_active | bool | |
| created_at | datetime UTC | |

### Transaction

| Поле | Описание |
|------|----------|
| account_id | FK → accounts CASCADE |
| amount | > 0, квант 0.01 |
| category | строка (имя категории) |
| tags | JSON list |
| date | дата операции |
| comment | текст |
| type | `income` \| `expense` |
| currency | код (обычно = счёт) |
| goal_id | FK goals SET NULL |
| debt_id | FK debts SET NULL |

Доход увеличивает balance, расход уменьшает.

### Goal

| Поле | Описание |
|------|----------|
| name | |
| target_amount / current_amount | прогресс |
| deadline | optional |
| priority | 1–5 |
| category_link | optional |
| is_completed | bool |

Взнос создаёт expense + увеличивает `current_amount`.

### Debt

| Поле | Описание |
|------|----------|
| counterparty | контрагент |
| amount / remaining_amount | тело / остаток |
| currency | |
| direction | `i_owe` \| `owed_to_me` |
| status | `active` \| `paid` |
| interest_rate | % годовых, optional |
| due_date / started_at | |
| comment | |

Погашение: I_OWE → expense; OWED_TO_ME → income; уменьшает remaining.

### Subscription

| Поле | Описание |
|------|----------|
| name, amount, currency | |
| account_id | списание |
| category | |
| periodicity | `monthly` \| `yearly` |
| next_billing_date | |
| is_active | |
| last_charged_at | |

### Currency

| Поле | Описание |
|------|----------|
| code | PK |
| name / name_ru / name_en | |
| symbol | |
| is_crypto | |

Сидится из `assets/data/currencies.json`.

### ExchangeRate

Семантика: **1 base = rate quote**.

| Поле | Описание |
|------|----------|
| id | UUID |
| base, quote | UNIQUE пара |
| rate | > 0, высокая точность |
| updated_at | |

### Category

| Поле | Описание |
|------|----------|
| name | UNIQUE |
| icon, color | |
| kind | `expense` \| `income` \| `both` |
| is_system / is_active | |

Системный сид: `DEFAULT_CATEGORY_SEED` в `config.py` (+ «Долг»).

### Settings

Одна строка `id = "default"`:

- `default_currency`, `theme`, `language`  
- `exchange_update_interval_minutes`  
- флаги уведомлений, `reminder_time`  
- `pin_hash`, `pin_salt`, `biometric_enabled`  
- `low_balance_threshold` (optional)

## Квантование

| Что | Точность |
|-----|----------|
| Деньги (balance, amount) | 0.01 (`MONEY_QUANTIZE`) |
| Курсы | до 14 знаков (`FIAT_RATE_QUANTIZE` / crypto) |

## Миграции

| Способ | Когда |
|--------|--------|
| `python scripts/migrate.py` | Обычная разработка: create_all + seed + column patches |
| `alembic upgrade head` | Формальные ревизии `migrations/versions/` |

Ревизии: `0001_initial_schema`, `0002_settings_reminder_time`, `0003_categories`.

При `init_db` также создаются performance-индексы на `transactions` (если SQLite).

## Пути на Windows

```text
%LOCALAPPDATA%\finanse\finanse\
  finanse.db
  backups\
  exports\
  logs\finanse.log
```

Эквивалент: `C:\Users\<User>\AppData\Local\finanse\finanse\`.
