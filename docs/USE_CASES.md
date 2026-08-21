# Use Cases (сценарии приложения)

Все use cases — асинхронные классы с методом `execute()`. Инжектируются в
`Container` через `build_container()`.

## Transactions (`lib/domain/use_cases/transactions.py`)

| Use Case | Метод | Описание |
|---|---|---|
| `AddTransactionUseCase` | `execute(tx)` | Создаёт операцию, обновляет баланс счёта, списывает/зачисляет в цель/долг, обновляет бюджет |
| `UpdateTransactionUseCase` | `execute(tx)` | Обновляет операцию (пересчёт баланса; перевод нельзя редактировать по сумме) |
| `DeleteTransactionUseCase` | `execute(id)` | Удаляет операцию, реверсирует баланс/цель/долг/бюджет; для перевода удаляет обе ноги |
| `ListTransactionsUseCase` | `execute(**filters)` | Фильтры: account_id, category, type, date_from/to, tags, goal_id, debt_id, subscription_id, transfer_id, limit/offset |
| `GetTransactionStatsUseCase` | `execute(account_id?, group_by)` | Агрегация: total_income/expense, by_category, by_period (DAY/WEEK/MONTH) |
| `TransferAccountsUseCase` | `execute(from_id, to_id, amount, comment?)` | Создаёт пару связанных транзакций (expense + income); конвертация при разных валютах |

**Переводы**:
- Создаётся `transfer_id` (UUID), обе ноги получают одинаковый ID.
- При разных валютах сумма назначения конвертируется через `RateBook`/use case.
- Удаление одной ноги удаляет обе и реверсирует балансы.
- Переводы исключаются из статистики и бюджетов.

## Accounts (`lib/domain/use_cases/accounts.py`)

| Use Case | Описание |
|---|---|
| `CreateAccountUseCase` | Создаёт счёт |
| `UpdateAccountUseCase` | Обновляет счёт |
| `DeleteAccountUseCase` | Удаляет счёт (каскадно транзакции и подписки) |
| `ListAccountsUseCase` | Список счетов (active_only) |
| `RecalculateAccountBalanceUseCase` | Пересчёт: `initial + incomes − expenses` |

## Goals (`lib/domain/use_cases/goals.py`)

| Use Case | Описание |
|---|---|
| `CreateGoalUseCase` | Создаёт цель |
| `UpdateGoalUseCase` | Обновляет цель |
| `DeleteGoalUseCase` | Удаляет цель |
| `ListGoalsUseCase` | Фильтры: status, currency, min_priority, sort_by |
| `ContributeToGoalUseCase` | Взнос: списывает с счёта, создаёт income-транзакцию с `goal_id`, обновляет `current_amount` |
| `GetGoalProjectionUseCase` | Прогноз: required_monthly_contribution, projected_completion_date, is_on_track |
| `ArchiveGoalUseCase` | Архирует цель |
| `DuplicateGoalUseCase` | Дублирует цель (current_amount=0) |
| `DeleteGoalContributionUseCase` | Удаляет взнос (через DeleteTransactionUseCase) |

## Debts (`lib/domain/use_cases/debts.py`)

| Use Case | Описание |
|---|---|
| `CreateDebtUseCase` | Создаёт долг (опционально с cash-движением) |
| `UpdateDebtUseCase` | Обновляет долг |
| `DeleteDebtUseCase` | Удаляет долг |
| `ListDebtsUseCase` | Фильтры: status, direction, currency, sort_by |
| `RepayDebtUseCase` | Погашение: списывает с счёта, создаёт expense-транзакцию с `debt_id`, уменьшает `remaining_amount` |
| `CalculateDebtInterestUseCase` | Расчёт процентов: `principal × rate × days / 365 / 100` |
| `GetDebtProjectionUseCase` | Прогноз: recommended_monthly_payment, projected_payoff_date, is_on_track |
| `ArchiveDebtUseCase` | Архирует долг |
| `DeleteDebtPaymentUseCase` | Удаляет платёж (через DeleteTransactionUseCase) |
| `MarkOverdueDebtsUseCase` | Помечает просроченные долги (due_date < now) |

## Subscriptions (`lib/domain/use_cases/subscriptions.py`)

| Use Case | Описание |
|---|---|
| `CreateSubscriptionUseCase` | Создаёт подписку |
| `UpdateSubscriptionUseCase` | Обновляет подписку |
| `DeleteSubscriptionUseCase` | Удаляет подписку |
| `ListSubscriptionsUseCase` | Фильтры: active_only, account_id, status |
| `ProcessDueSubscriptionsUseCase` | Обрабатывает наступившие: создаёт expense-транзакцию, списывает, сдвигает next_billing_date |
| `PauseSubscriptionUseCase` | Ставит на паузу (status=PAUSED) |
| `ResumeSubscriptionUseCase` | Возобновляет (status=ACTIVE) |
| `ChargeSubscriptionNowUseCase` | Ручной платёж сейчас |
| `DeleteSubscriptionChargeUseCase` | Удаляет платёж подписки |
| `GetSubscriptionAnalyticsUseCase` | Аналитика: total_spent, monthly_trend, top_subscriptions, total_monthly_cost |

## Currencies (`lib/domain/use_cases/currencies.py`)

| Use Case | Описание |
|---|---|
| `UpdateExchangeRatesUseCase` | Загружает fiat + crypto курсы, сохраняет в БД |
| `ConvertCurrencyUseCase` | Конвертация: прямая пара → обратная → через пивот (USD) |
| `ListCurrenciesUseCase` | Список валют (include_crypto) |

## Budgets (`lib/domain/use_cases/budgets.py`)

| Use Case / Функция | Описание |
|---|---|
| `SetBudgetUseCase` | Устанавливает лимит на категорию/месяц |
| `DeleteBudgetUseCase` | Удаляет бюджет |
| `GetBudgetProgressUseCase` | Возвращает `BudgetProgress` (с пересчётом spent) |
| `GetBudgetsForMonthUseCase` | Список бюджетов на месяц |
| `RecalculateBudgetSpentUseCase` | Пересчёт spent из транзакций (исключая переводы) |
| `check_budget_alerts()` | Проверка порогов (80%, 100%) и push-уведомления |

## Categories (`lib/domain/use_cases/categories.py`)

| Use Case | Описание |
|---|---|
| `CreateCategoryUseCase` | Создаёт категорию |
| `UpdateCategoryUseCase` | Обновляет категорию (с переименованием в бюджетах) |
| `DeleteCategoryUseCase` | Удаляет категорию |
| `ListCategoriesUseCase` | Список (kind, active_only) |
| `FindOrCreateCategoryUseCase` | Найти по имени или создать |

## Settings (`lib/domain/use_cases/settings.py`)

| Use Case | Описание |
|---|---|
| `GetSettingsUseCase` | Возвращает настройки (создаёт дефолтные если нет) |
| `UpdateSettingsUseCase` | Сохраняет настройки (updated_at = UTC) |

## Export (`lib/domain/use_cases/export_data.py`)

| Use Case | Описание |
|---|---|
| `ExportDataUseCase` | Экспорт всех данных в JSON (accounts, transactions, goals, debts, subscriptions, currencies, rates, settings) |

## Align Currencies (`lib/domain/use_cases/align_currencies.py`)

| Функция | Описание |
|---|---|
| `align_sole_account_currency(container)` | Если единственный счёт в валюте ≠ базовой, переключает счёт и его транзакции на базовую (без конвертации сумм) |