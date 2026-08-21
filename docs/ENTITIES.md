# Доменные сущности

Все сущности — Pydantic v2 `BaseModel` с `model_config = ConfigDict(from_attributes=True)`.
Денежные поля квантуются через `quantize_money` (2 знака, ROUND_HALF_UP).
Даты нормализуются к UTC.

## Account

```python
class Account(BaseModel):
    id: str               # UUID
    name: str
    currency: str         # ISO 4217 (RUB, USD, UZS, BTC …)
    balance: Decimal      # текущий баланс (квантуется)
    initial_balance: Decimal
    icon: str             # ключ иконки (wallet, credit_card, ccy_USD …)
    color: str            # HEX-цвет
    is_active: bool
    created_at: datetime  # UTC
```

Баланс пересчитывается из транзакций: `initial_balance + incomes − expenses`.
Переводы между счетами создают пару транзакций (expense + income) с общим `transfer_id`.

## Transaction

```python
class Transaction(BaseModel):
    id: str
    account_id: str
    amount: Decimal        # > 0, квантуется
    category: str          # имя категории
    tags: list[str]
    date: datetime         # UTC
    comment: str
    type: TransactionType  # INCOME | EXPENSE
    currency: str
    goal_id: Optional[str]
    debt_id: Optional[str]
    goal_credit_amount: Optional[Decimal]   # зачислено в цель
    debt_credit_amount: Optional[Decimal]   # зачислено в долг
    subscription_id: Optional[str]
    transfer_id: Optional[str]              # связывает пару перевода
    transfer_peer_account_id: Optional[str]
    created_at: datetime
    updated_at: datetime
```

Свойство `is_transfer` — `True`, если есть `transfer_id`.
Обновление суммы перевода напрямую запрещено (бросает `ValueError`).

## Category

```python
class Category(BaseModel):
    id: str
    name: str              # уникальное, case-insensitive
    icon: str
    color: str
    kind: CategoryKind     # INCOME | EXPENSE | BOTH
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

`matches_type(tx_type)` — `True`, если категория подходит для типа операции.

## Currency & ExchangeRate

```python
class Currency(BaseModel):
    code: str              # ISO (USD, BTC …)
    name: str
    name_ru: str
    name_en: str
    symbol: str
    is_crypto: bool

class ExchangeRate(BaseModel):
    base: str              # код базовой валюты
    quote: str             # код котируемой
    rate: Decimal          # 1 base = rate quote (квантуется, 8 знаков)
    updated_at: datetime
```

Курсы хранятся с высокой точностью (`Numeric(24,12)` в БД), чтобы слабые
валюты (UZS→BTC) не округлялись в ноль.

## Goal

```python
class Goal(BaseModel):
    id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    deadline: Optional[datetime]
    priority: int          # 1–5
    category_link: str     # категория для взносов (по умолчанию "Накопление")
    status: GoalStatus     # ACTIVE | COMPLETED | ARCHIVED
    is_completed: bool
    cached_projection: Optional[dict]   # кэш прогноза
    created_at: datetime
```

Свойства:
- `progress_ratio` — `current / target` (0–1+).
- `remaining_amount` — `max(0, target − current)`.
- `model_validator` синхронизирует `status` и `is_completed`.

Взнос (`ContributeToGoalUseCase`): создаёт income-транзакцию с `goal_id` и
`goal_credit_amount`, списывает с счёта, обновляет `current_amount`.

## Debt

```python
class Debt(BaseModel):
    id: str
    counterparty: str
    amount: Decimal
    remaining_amount: Decimal
    currency: str
    direction: DebtDirection   # I_OWE | OWED_TO_ME
    status: DebtStatus         # ACTIVE | OVERDUE | PAID | ARCHIVED
    interest_rate: Optional[Decimal]   # годовая ставка, %
    due_date: Optional[datetime]
    started_at: datetime
    comment: str
    created_at: datetime
    updated_at: datetime
```

Проценты: `compute_debt_interest(debt)` — `principal × rate × days / 365 / 100`.
Погашение (`RepayDebtUseCase`): списывает с счёта, создаёт expense-транзакцию
с `debt_id` и `debt_credit_amount`, уменьшает `remaining_amount`.

## Subscription

```python
class Subscription(BaseModel):
    id: str
    name: str
    amount: Decimal
    currency: str
    account_id: str
    category: str
    periodicity: Periodicity     # WEEKLY | MONTHLY | YEARLY | CUSTOM
    custom_interval_days: Optional[int]
    start_date: date
    end_date: Optional[date]
    max_payments: Optional[int]
    payments_made: int
    next_billing_date: datetime
    status: SubscriptionStatus   # ACTIVE | PAUSED | CANCELLED | COMPLETED
    is_active: bool              # синхронизируется со status
    auto_charge: bool
    last_charged_at: Optional[datetime]
    last_skip_date: Optional[date]
    comment: str
    created_at: datetime
    updated_at: datetime
```

`ProcessDueSubscriptionsUseCase` — обрабатывает наступившие подписки:
создаёт expense-транзакцию, списывает с счёта, сдвигает `next_billing_date`,
инкрементирует `payments_made`, проверяет `max_payments`/`end_date`.

## Budget

```python
class Budget(BaseModel):
    id: str
    category_id: str       # имя категории (FK → categories.name)
    month: int             # 1–12
    year: int
    amount_limit: Decimal  # > 0
    spent: Decimal         # пересчитывается из транзакций
    last_alert_level: int  # 0=ок, 1=80%, 2=100%+
    created_at: datetime
    updated_at: datetime
```

Свойства:
- `percent_used` — `spent / amount_limit × 100`.
- `remaining` — `max(0, amount_limit − spent)`.
- `is_over_budget` — `spent > amount_limit`.

`BudgetProgress` — snapshot для UI/уведомлений.

## AppSettings

```python
class AppSettings(BaseModel):
    id: str = "default"
    default_currency: str
    theme: str              # light | dark | system
    language: str           # ru | en | uz
    exchange_update_interval_minutes: int   # ≥ 5
    notifications_enabled: bool
    subscription_reminders: bool
    debt_reminders: bool
    goal_milestones: bool
    budget_alerts: bool
    low_balance_threshold: Optional[float]
    reminder_time: str      # HH:MM
    reminder_days: int      # 0–365
    check_balance_before_subscription: bool
    biometric_enabled: bool
    updated_at: datetime
```

PIN-credentials (`pin_hash`, `pin_salt`) хранятся в `SettingsModel` (ORM),
но не входят в Pydantic-сущность `AppSettings` — доступны через
`SettingsRepository.get_pin_credentials()` / `set_pin_credentials()`.

## Money

```python
def quantize_money(value) -> Decimal    # 0.01, ROUND_HALF_UP
def quantize_rate(value, *, crypto=False) -> Decimal   # 0.00000001
```

## CurrencyCodes

```python
def normalize_currency_code(code: str | None, *, default="RUB") -> str
```

Алиасы: `₽→RUB`, `$→USD`, `€→EUR`, `₸→KZT`, `СУМ→UZS`, `SOM→UZS` и др.