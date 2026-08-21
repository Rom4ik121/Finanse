# База данных и миграции

## SQLite

- Движок: SQLAlchemy 2.0, SQLite, WAL-режим, `PRAGMA foreign_keys=ON`.
- Путь: `AppConfig.db_path` (по умолчанию `%LOCALAPPDATA%/finanse/finanse/finanse.db` на Windows).
- `init_db()` → `Base.metadata.create_all` + патчи колонок для существующих БД.
- `reset_engine()` — освобождает engine (для тестов и восстановления БД).

## ORM-модели (`lib/infrastructure/db_models.py`)

### accounts
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | UUID |
| name | String(128) | Название |
| currency | String(16) | ISO код |
| balance | Numeric(18,2) | Текущий баланс |
| initial_balance | Numeric(18,2) | Начальный баланс |
| icon | String(64) | Ключ иконки |
| color | String(16) | HEX |
| is_active | Boolean | Активен |
| created_at | DateTime(tz) | UTC |

### transactions
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | UUID |
| account_id | String(36) FK→accounts | Счёт |
| amount | Numeric(18,2) | Сумма (>0) |
| category | String(128) | Категория |
| tags | JSON | Теги |
| date | DateTime(tz) | Дата/время |
| comment | Text | Комментарий |
| type | String(16) | income/expense |
| currency | String(16) | Валюта |
| goal_id | String(36) FK→goals | Связь с целью |
| debt_id | String(36) FK→debts | Связь с долгом |
| goal_credit_amount | Numeric(18,2) | Зачислено в цель |
| debt_credit_amount | Numeric(18,2) | Зачислено в долг |
| subscription_id | String(36) FK→subscriptions | Связь с подпиской |
| transfer_id | String(36) | ID перевода (пара) |
| transfer_peer_account_id | String(36) | Счёт-контрагент перевода |
| created_at, updated_at | DateTime(tz) | UTC |

### goals
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | UUID |
| name | String(128) | Название |
| target_amount | Numeric(18,2) | Цель |
| current_amount | Numeric(18,2) | Накоплено |
| currency | String(16) | Валюта |
| deadline | DateTime(tz) | Дедлайн |
| priority | Integer | 1–5 |
| category_link | String(128) | Категория взносов |
| status | String(16) | active/completed/archived |
| is_completed | Boolean | Завершена |
| cached_projection | JSON | Кэш прогноза |
| created_at | DateTime(tz) | UTC |

### debts
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | UUID |
| counterparty | String(256) | Контрагент |
| amount | Numeric(18,2) | Сумма |
| remaining_amount | Numeric(18,2) | Остаток |
| currency | String(16) | Валюта |
| direction | String(32) | i_owe/owed_to_me |
| status | String(16) | active/overdue/paid/archived |
| interest_rate | Numeric(10,4) | Годовая ставка % |
| due_date | DateTime(tz) | Срок |
| started_at | DateTime(tz) | Дата начала |
| comment | Text | Комментарий |
| created_at, updated_at | DateTime(tz) | UTC |

### subscriptions
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | UUID |
| name | String(128) | Название |
| amount | Numeric(18,2) | Сумма |
| currency | String(16) | Валюта |
| account_id | String(36) FK→accounts | Счёт списания |
| category | String(128) | Категория |
| periodicity | String(16) | weekly/monthly/yearly/custom |
| custom_interval_days | Integer | Для custom |
| start_date | Date | Дата начала |
| end_date | Date | Дата окончания |
| max_payments | Integer | Максимум платежей |
| payments_made | Integer | Совершено |
| next_billing_date | DateTime(tz) | Следующий платёж |
| status | String(16) | active/paused/cancelled/completed |
| is_active | Boolean | Активна |
| auto_charge | Boolean | Автоплатеж |
| last_charged_at | DateTime(tz) | Последний платёж |
| last_skip_date | Date | Последний пропуск |
| comment | Text | Комментарий |
| created_at, updated_at | DateTime(tz) | UTC |

### currencies
| Колонка | Тип | Описание |
|---|---|---|
| code | String(16) PK | ISO код |
| name | String(128) | Имя |
| name_ru | String(128) | Русское имя |
| name_en | String(128) | Английское имя |
| symbol | String(16) | Символ |
| is_crypto | Boolean | Криптовалюта |

### exchange_rates
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | UUID |
| base | String(16) | Базовая валюта |
| quote | String(16) | Котируемая |
| rate | Numeric(24,12) | Курс |
| updated_at | DateTime(tz) | UTC |
| UNIQUE(base, quote) | | Уникальная пара |

### categories
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | UUID |
| name | String(128) UNIQUE | Имя |
| icon | String(64) | Иконка |
| color | String(16) | Цвет |
| kind | String(16) | income/expense/both |
| is_system | Boolean | Системная |
| is_active | Boolean | Активна |
| created_at, updated_at | DateTime(tz) | UTC |

### settings (singleton, id="default")
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | "default" |
| default_currency | String(16) | Базовая валюта |
| theme | String(32) | light/dark/system |
| language | String(8) | ru/en/uz |
| exchange_update_interval_minutes | Integer | Интервал обновления курсов |
| notifications_enabled | Boolean | Уведомления |
| subscription_reminders | Boolean | Напоминания о подписках |
| debt_reminders | Boolean | Напоминания о долгах |
| goal_milestones | Boolean | Уведомления о целях |
| budget_alerts | Boolean | Алерты бюджетов |
| low_balance_threshold | Numeric(18,2) | Порог низкого баланса |
| reminder_time | String(8) | HH:MM |
| reminder_days | Integer | За сколько дней напоминать |
| check_balance_before_subscription | Boolean | Проверять баланс перед автоплатежом |
| pin_hash | String(128) | Хэш PIN |
| pin_salt | String(64) | Соль PIN |
| biometric_enabled | Boolean | Биометрия |
| updated_at | DateTime(tz) | UTC |

### budgets
| Колонка | Тип | Описание |
|---|---|---|
| id | String(36) PK | UUID |
| category_id | String(128) FK→categories.name | Категория |
| month | Integer | 1–12 |
| year | Integer | Год |
| amount_limit | Numeric(18,2) | Лимит |
| spent | Numeric(18,2) | Потрачено |
| last_alert_level | Integer | Уровень алерта |
| created_at, updated_at | DateTime(tz) | UTC |
| UNIQUE(category_id, month, year) | | Уникальный бюджет |

## Миграции (Alembic)

9 версий, все идемпотентные (проверяют наличие колонок/индексов):

| Версия | Описание |
|---|---|
| 0001_initial | Базовый schema (create_all) |
| 0002_reminder_time | settings.reminder_time |
| 0003_categories | Таблица categories |
| 0004_goals_currency_status_projection | goals: currency, status, cached_projection; transactions: goal_credit_amount |
| 0005_debts_credit_and_indexes | transactions: debt_credit_amount; debts: индексы status, due_date |
| 0006_subscriptions_flexible | subscriptions: custom_interval_days, start/end_date, max_payments, payments_made, status, last_skip_date; transactions: subscription_id; settings: reminder_days, check_balance_before_subscription |
| 0007_subscription_auto_charge | subscriptions: auto_charge; индекс next_billing |
| 0008_budgets | Таблица budgets; settings: budget_alerts |
| 0009_transfers | transactions: transfer_id, transfer_peer_account_id; индекс transfer_id |

`migrations/env.py` резолвит URL БД из `AppConfig`, использует
`render_as_batch=True` (для SQLite ALTER TABLE).