# FinWise — глубокое техническое погружение (Deep Dive)

> Этот документ дополняет остальные файлы в `docs/` (`ARCHITECTURE.md`, `FEATURES.md`,
> `DATA_MODEL.md`, `DEVELOPMENT.md`, `BUILD.md`, `CODEMAGIC.md`) деталями, извлечёнными
> непосредственно из исходного кода: точный жизненный цикл запуска, состав DI-контейнера,
> алгоритмы конвертации валют, полные схемы сущностей (включая `Budget`, которого нет в
> `DATA_MODEL.md`), поведение use cases с побочными эффектами и структуру presentation-слоя.
> Актуально на 20.08.2026.

---

## 1. Жизненный цикл запуска приложения

```text
main.py
  └─ lib.main.run(config=None)
       1. get_default_config()               # AppConfig + ensure_directories()
       2. setup_logging(log_dir)              # файл {data_dir}/logs/finanse.log
       3. Нормализация FLET_SERVER_IP/FLET_HOST ("*"/"all" → "0.0.0.0")
       4. Выбор режима запуска Flet по env FLET_VIEW / FLET_FORCE_WEB_SERVER:
            - desktop (по умолчанию)          → ft.run(_flet_main)
            - web/browser                     → AppView.WEB_BROWSER, host/port
            - android/ios/mobile              → AppView.WEB_BROWSER (тот же сервер,
                                                  Flet-клиент подключается по Wi-Fi)
            - hidden                          → AppView.FLET_APP_HIDDEN
       5. ft.run(_flet_main, **kwargs)
```

### `_flet_main(page)` — асинхронная точка входа Flet

1. Показывает splash (`build_launch_splash()`), фон `#000000`.
2. Регистрирует платформенные мосты:
   - `register_local_auth_service(page)` — биометрия на мобильных (flet_local_auth).
   - `register_android_notifications(page)` — Android push-каналы.
3. `config = get_default_config()`, `setup_logging`, `init_db(config)`.
4. `container = build_container(config, init_database=False)` (БД уже инициализирована
   на предыдущем шаге, повторно не пере-инициализируется).
5. `await _seed_if_needed(container)`:
   - Синхронизирует справочник валют из `assets/data/currencies.json`
     (`currency_repository.seed_from_json`, upsert при каждом запуске — так новые
     монеты добавляются без миграций).
   - Загружает/создаёт `Settings` через `get_settings.execute()`.
   - Если счетов нет — создаёт счёт «Наличные» (`t("account.default_cash", lang)`)
     в валюте из настроек.
   - Если счёт уже один — вызывает `align_sole_account_currency(container)`
     (см. `lib/domain/use_cases/align_currencies.py`), которая переименовывает код
     валюты единственного счёта под текущую базовую валюту настроек **без** финансового
     пересчёта суммы (см. раздел «Ограничения»).
6. Запускает два фоновых `page.run_task(...)`, которые живут всё время сессии страницы:
   - `_exchange_rate_loop(container)` — обновление курсов.
   - `_reminder_loop(container)` — ежедневные напоминания.
7. Разово вызывает `process_due_subscriptions.execute(...)` — списывает все просроченные
   подписки при старте (catch-up).
8. Разово вызывает `schedule_reminders(container, settings, language)` — сразу планирует
   напоминания (не дожидаясь `reminder_time`), плюс `request_push_permissions()`, если
   уведомления включены.
9. Создаёт `FinanseApp(page, container)`, чистит `page.controls` (убирает splash) и
   вызывает `await app.start()`.

### Фоновые циклы

| Цикл | Логика |
|------|--------|
| `_exchange_rate_loop` | `while True`: читает `settings.exchange_update_interval_minutes` и `default_currency`, вызывает `update_exchange_rates.execute(base=...)`, инвалидирует кэш `RateBook` (`invalidate_rate_book_cache()`), спит `max(5, minutes) * 60` секунд. Ошибки логируются, но не прерывают цикл (кроме `CancelledError`). |
| `_reminder_loop` | `while True`: раз в минуту проверяет, не настал ли `reminder_time` (`HH:MM`, локальное время) и не был ли сегодняшний прогон уже выполнен (`last_run_date`). При совпадении — `schedule_reminders(...)`, иначе рассчитывает `sleep_for` до цели (максимум 15 минут, минимум 20 секунд), чтобы быстро подхватывать изменения настроек. Если уведомления выключены — спит 5 минут. |

### `FinanseApp.start()` (presentation/app.py)

1. `page.title = "FinWise"`, `page.padding = 0`, кастомный `NavigationBar` (без
   scaffold), устанавливает `page.window.icon` из `assets/icon.ico`, минимальный размер
   окна 320×560, дефолтный десктопный размер 420×780.
2. Загружает `AppSettings` через `container.get_settings`, иначе — дефолтные значения.
3. `apply_theme(page, theme_mode)` — Material 3 (light/dark/system).
4. `_load_pin_gate()` — читает `pin_hash`/`pin_salt`/`biometric_enabled` из
   `settings_repository.get_pin_credentials()`. Если PIN задан — сессия стартует
   заблокированной (`is_unlocked = False`), иначе разблокирована.
5. Строит `NavigationBar` (4 таба, иконки Material, `label_behavior=ALWAYS_SHOW`).
6. Подписывается на `AppState` (`subscribe(self._on_state_changed)`).
7. `page.add(self._shell)`, первый `_render(force=True)`, сброс отложенных
   уведомлений (`_flush_notifications`).

### Рендеринг / кэш страниц

`FinanseApp` держит `_primary_cache` (4 вкладки) и `_secondary_cache` (`analytics`,
`account:<id>`, `goals`, `debts`, `subscriptions`, `currencies`, `budgets`) — страницы
конструируются один раз и переиспользуются между показами (Flet-контролы не создаются
заново на каждое переключение). Кэш полностью сбрасывается при:
- смене языка (нужно перестроить все текстовые строки),
- `AppState.view_rebuild_token` (например, после смены темы).

Если `is_unlocked=False` и есть `pin_hash`/`pin_salt` — вместо контента показывается
`LockScreen` (PIN + опциональная биометрия), нижняя навигация скрывается.

---

## 2. DI-контейнер (`lib/core/dependencies.py`)

`build_container(config, init_database=True)` — не «настоящий» DI-фреймворк, а
**самодостаточный билдер с диагностикой отказов**:

- `_construct(container, attr, module_path, class_name, *args, **kwargs)` —
  пытается импортировать и создать инфраструктурный класс. При ошибке импорта/конструктора
  не поднимает исключение, а записывает имя в `container.missing` и текст ошибки в
  `container.errors[attr]`. Это позволяет частично собранному контейнеру оставаться
  рабочим во время разработки (например, если реализация репозитория ещё не написана).
- `_wire(attr, factory, *dep_names)` — универсальная обёртка: берёт зависимости по
  именам атрибутов контейнера, если хоть одна `None` — записывает `missing`/`errors` и
  не конструирует use case.
- `_wire_transaction(attr, factory)` — специальный wiring для `Add/Update/DeleteTransactionUseCase`:
  обязательные зависимости `transaction_repository, account_repository, goal_repository,
  debt_repository` + опциональные keyword-зависимости `budgets`, `settings`,
  `notifications` (могут быть `None` без ошибки).
- `Container.require(name)` — достаёт зависимость или бросает `RuntimeError` с текстом
  причины отказа (используется там, где отсутствие зависимости критично).
- `Container.rebind_session_factory(session_factory)` — после `reset_engine()` +
  восстановления БД из бэкапа перепривязывает `_session_factory` у всех SQLAlchemy-репозиториев,
  чтобы не держать ссылку на закрытый engine.

### Состав контейнера

**Репозитории** (все SQLAlchemy, session factory через `get_session_factory(cfg)`):
`transaction`, `account`, `goal`, `debt`, `subscription`, `currency`, `category`,
`settings`, `budget`.

**Инфраструктурные сервисы:** `exchange_rate_provider` (HttpExchangeRateProvider,
`api_key=cfg.exchange_rate_api_key`), `notification_service`, `backup_service` (`cfg`),
`export_service` (`cfg`), `encryption_service`.

**Use cases** (полный список — см. таблицу ниже) собираются в конце функции; при сборке
транзакционных use cases передаются keyword-зависимости `budgets`/`settings`/`notifications`,
поэтому изменение расхода **синхронно** обновляет месячный бюджет категории и,
при необходимости, отправляет push через `NotificationService`.

`TransferAccountsUseCase` собирается только если одновременно есть `add_transaction`,
`delete_transaction`, `account_repository`, `currency_repository` (плюс опционально
`find_or_create_category`).

При завершении сборки в лог пишется либо «Container built successfully», либо список
недостающих зависимостей — удобно для диагностики после рефакторинга репозиториев.

---

## 3. Полная карта Use Cases (`lib/domain/use_cases/`)

| Модуль | Классы | Побочные эффекты |
|--------|--------|-------------------|
| `accounts.py` | `CreateAccountUseCase`, `UpdateAccountUseCase`, `DeleteAccountUseCase`, `ListAccountsUseCase`, `RecalculateAccountBalanceUseCase` | `RecalculateAccountBalanceUseCase` пересчитывает `balance = initial_balance + Σincome − Σexpense` по всем транзакциям счёта — используется как «ремонт» после сбоев синхронизации. |
| `transactions.py` | `AddTransactionUseCase`, `UpdateTransactionUseCase`, `DeleteTransactionUseCase`, `ListTransactionsUseCase`, `GetTransactionStatsUseCase`, `TransferAccountsUseCase` | Каждая операция создания/изменения/удаления транзакции атомарно (на уровне вызовов, не БД-транзакции) корректирует: 1) баланс счёта, 2) `current_amount` цели (если `goal_id`), 3) `remaining_amount` + `status` долга (если `debt_id`), 4) `spent`/`last_alert_level` месячного бюджета через `apply_expense_delta` (только для расходов без `transfer_id`). |
| `goals.py` | `CreateGoalUseCase`, `UpdateGoalUseCase`, `DeleteGoalUseCase`, `ListGoalsUseCase`, `ContributeToGoalUseCase`, `GetGoalProjectionUseCase`, `ArchiveGoalUseCase`, `DuplicateGoalUseCase`, `DeleteGoalContributionUseCase` | `ContributeToGoalUseCase` создаёт `expense`-транзакцию со связью `goal_id` через `add_transaction`, проверяя, что валюта счёта совпадает с валютой цели (иначе — конвертация запрещена в UI-сценарии). `goal_credit_amount(tx)` определяет сумму зачёта с учётом FX. |
| `debts.py` | `CreateDebtUseCase`, `UpdateDebtUseCase`, `DeleteDebtUseCase`, `ListDebtsUseCase`, `RepayDebtUseCase`, `CalculateDebtInterestUseCase`, `GetDebtProjectionUseCase`, `ArchiveDebtUseCase`, `DeleteDebtPaymentUseCase`, `MarkOverdueDebtsUseCase` | `RepayDebtUseCase`: `I_OWE` → создаёт `expense`; `OWED_TO_ME` → создаёт `income`; уменьшает `remaining_amount`, обновляет `status` через `resolve_debt_status`. `MarkOverdueDebtsUseCase` — пакетное обновление статуса `ACTIVE → OVERDUE` по `due_date` (для напоминаний). |
| `subscriptions.py` | `CreateSubscriptionUseCase`, `UpdateSubscriptionUseCase`, `DeleteSubscriptionUseCase`, `ListSubscriptionsUseCase`, `ProcessDueSubscriptionsUseCase`, `PauseSubscriptionUseCase`, `ResumeSubscriptionUseCase`, `ChargeSubscriptionNowUseCase`, `DeleteSubscriptionChargeUseCase`, `GetSubscriptionAnalyticsUseCase` | `ProcessDueSubscriptionsUseCase` — «catch-up»: создаёт по одной транзакции-списанию **за каждый** пропущенный расчётный период между `next_billing_date` и «сейчас», продвигая дату вперёд, пока не догонит текущий момент (не создаёт один большой платёж). |
| `currencies.py` | `UpdateExchangeRatesUseCase`, `ConvertCurrencyUseCase`, `ListCurrenciesUseCase` | `UpdateExchangeRatesUseCase` опционально принимает `provider`; без него просто перечитывает то, что уже в БД. `ConvertCurrencyUseCase` делегирует в репозиторий (прямой/обратный курс), в отличие от `RateBook`, который умеет cross через pivot **в памяти** (для batch-конвертации в аналитике/дашборде). |
| `categories.py` | `CreateCategoryUseCase`, `UpdateCategoryUseCase`, `DeleteCategoryUseCase`, `ListCategoriesUseCase`, `FindOrCreateCategoryUseCase` | `Update/DeleteCategoryUseCase` принимают опциональную зависимость `budgets` — переименование/удаление категории синхронизирует связанные бюджеты (FK `budgets.category_id → categories.name`, `ondelete=CASCADE, onupdate=CASCADE` на уровне SQLAlchemy, но use case дублирует логику для консистентности домена). |
| `settings.py` | `GetSettingsUseCase`, `UpdateSettingsUseCase` | `GetSettingsUseCase` создаёт singleton-запись `id="default"`, если её ещё нет (ленивый сид). |
| `budgets.py` | `SetBudgetUseCase`, `DeleteBudgetUseCase`, `GetBudgetProgressUseCase`, `GetBudgetsForMonthUseCase`, `RecalculateBudgetSpentUseCase`, + хелперы `apply_expense_delta`, `_sum_expenses`, `month_bounds` | См. раздел 5. |
| `export_data.py` | `ExportDataUseCase` | Собирает полный дамп (accounts/transactions/goals/debts/subscriptions/currencies/settings) для JSON/CSV/PDF экспорта. |
| `align_currencies.py` | `align_sole_account_currency(container)` | Если у пользователя ровно один счёт и его валюта отличается от `settings.default_currency` — переименовывает код валюты счёта (без конвертации суммы!). Вызывается автоматически при старте и при смене базовой валюты в настройках. |

---

## 4. Модель данных — уточнения и недокументированные детали

### 4.1 Таблица `Budget` (отсутствует в `DATA_MODEL.md`, добавлена в БД `0008_budgets.py`)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID str | PK |
| `category_id` | str | FK → `categories.name` (`CASCADE` delete/update) |
| `month` | int 1–12 | |
| `year` | int 1970–2100 | |
| `amount_limit` | Decimal(18,2) | Лимит на месяц, > 0 |
| `spent` | Decimal(18,2) | Автоматически считается по расходным транзакциям без `transfer_id` |
| `last_alert_level` | int `{0, 80, 100}` | Анти-дублирование уведомлений о превышении |
| `created_at` / `updated_at` | datetime UTC | |

Уникальность: `(category_id, month, year)`. Индексы: `(month, year)`, `(category_id, month, year)`.

Вычисляемые свойства сущности `Budget`: `percent_used`, `remaining` (не отрицательный),
`is_over_budget`. `BudgetProgress` — DTO для UI/уведомлений (снапшот с уже посчитанным
`percent` с округлением до 0.01).

### 4.2 `AppSettings` — полный набор полей (Pydantic, `lib/domain/entities/settings.py`)

```text
id: str = "default"
default_currency: str            # верхний регистр, нормализуется валидатором
theme: str                        # "light" | "dark" | "system"
language: str                     # "ru" | "en" | "uz"
exchange_update_interval_minutes: int
notifications_enabled: bool
subscription_reminders: bool
debt_reminders: bool
goal_milestones: bool
budget_alerts: bool
low_balance_threshold: float | None
reminder_time: str = "09:00"      # валидируется как HH:MM, 0–23 / 0–59
reminder_days: int = 3            # 0–365, дней до списания подписки для напоминания
check_balance_before_subscription: bool = True
biometric_enabled: bool = False
updated_at: datetime
```

Важно: PIN (`pin_hash`, `pin_salt`) **не входит** в Pydantic-модель `AppSettings` —
хранится только на уровне ORM (`SettingsModel.pin_hash`/`pin_salt`) и читается отдельным
методом репозитория `get_pin_credentials()` (см. `SqlAlchemySettingsRepository`), минуя
доменную сущность. Это осознанное разделение: доменные use cases настроек никогда не
видят и не сериализуют хэш PIN.

### 4.3 Квантование и точность

| Величина | Точность | Константа |
|----------|----------|-----------|
| Деньги (balance, amount, лимиты бюджета) | 0.01, `ROUND_HALF_UP` | `MONEY_QUANTIZE` |
| Курс валют (fiat) | 14 знаков после запятой | `FIAT_RATE_QUANTIZE` |
| Курс валют (crypto) | 14 знаков после запятой | `CRYPTO_RATE_QUANTIZE` |

В БД `ExchangeRateModel.rate` хранится как `Numeric(24, 12)` — то есть на уровне SQLite
точность до 12 знаков после запятой (домен квантует до 14, но колонка их обрежет; это
достаточно для UZS↔BTC на практике).

### 4.4 Нормализация валютных алиасов

`lib/domain/entities/currency_codes.py::normalize_currency_code()` разруливает то, что
реально вводят пользователи: `SOM/SO'M/SUM/СЎМ/СУМ → UZS`, `₽/РУБ/РУБЛЬ/RUR → RUB`,
`$ → USD`, `€ → EUR`, `£ → GBP`, `₸/ТЕНГЕ → KZT`. Используется во всех местах, где валюта
приходит от пользователя (Account, Debt, Goal, RateBook.factor/convert).

### 4.5 Статусы и переходы

- **DebtStatus**: `active → overdue` (по `due_date < now`, если не `archived`),
  `active/overdue → paid` (когда `remaining_amount <= 0`), `archived` — «залипает» и не
  меняется автоматически (`resolve_debt_status` явно проверяет `current == ARCHIVED`).
- **GoalStatus**: `active ⇄ completed` синхронизируется автоматически при каждом
  изменении `current_amount` (`model_validator` в `Goal` + `_mark_goal_progress` в use
  cases); `archived` хранит `is_completed` по факту суммы, но не меняется обратно в
  `active`/`completed` автоматически.
- **SubscriptionStatus**: `active | paused | expired | cancelled`; `is_active` всегда
  синхронизирован как `status == ACTIVE` (модель не позволяет им расходиться).

---

## 5. Бюджеты — сквозной механизм (не описан в `FEATURES.md`)

1. Пользователь задаёт месячный лимит на категорию через `SetBudgetUseCase` (только для
   категорий `kind in {expense, both}`); при создании тут же пересчитывается `spent` по
   уже существующим расходам месяца (`_sum_expenses`).
2. При каждом `AddTransactionUseCase`/`UpdateTransactionUseCase`/`DeleteTransactionUseCase`
   для операции типа `expense` **без** `transfer_id` вызывается
   `_sync_budget_expense(...) → apply_expense_delta(...)`:
   - находит бюджет по `(category, month, year)` транзакции;
   - прибавляет/вычитает `amount` (`sign=+1` создание, `sign=-1` откат при
     удалении/редактировании) с квантованием и защитой от отрицательного `spent`;
   - вычисляет уровень тревоги: `>=100% → 100`, `>=80% → 80`, иначе `0`;
   - шлёт push только если уровень **вырос** относительно `last_alert_level` (защита от
     повторных уведомлений на каждую операцию);
   - при возврате уровня к `0` (например, транзакцию удалили) сбрасывает
     `last_alert_level`, чтобы следующий пересечение порога снова уведомило.
3. `RecalculateBudgetSpentUseCase` — «ремонтная» пересборка `spent` с нуля по реальным
   транзакциям (на случай рассинхронизации, миграции данных или ручного вмешательства в БД).
4. `GetBudgetsForMonthUseCase` возвращает список, отсортированный по `percent_used`
   по убыванию — самые «горящие» категории показываются первыми в UI (`BudgetsPage`).

---

## 6. Валютные курсы: провайдеры и конвертация

### 6.1 Источники (`lib/infrastructure/api/`)

| Клиент | Источник | Назначение |
|--------|----------|------------|
| `exchange_rate_client.py` | `https://open.er-api.com/v6/latest/USD` | Fiat-курсы к USD |
| `binance_rate_client.py` | Binance public ticker API | Крипто-курсы (приоритетный источник) |
| `crypto_rate_client.py` | CoinGecko (fallback) | Крипто-курсы, когда Binance недоступен/не покрывает монету |

`HttpExchangeRateProvider` (`lib/infrastructure/services/exchange_rate_provider.py`)
объединяет оба мира: тянет fiat-книгу от USD и крипто-тикеры, приводит всё к единому
«USD-якорю» и отдаёт `UpdateExchangeRatesUseCase` пары `base → quote` для записи в
`ExchangeRateModel` (плюс сохраняет сами USD-курсы — удобно для прямых пар вида
BTC↔UZS при базовой валюте UZS, чтобы не терять точность через длинные цепочки pivot).

### 6.2 `RateBook` — конвертация в памяти (`lib/domain/services/rate_book.py`)

Ключевая оптимизация производительности: вместо N обращений к БД на каждую сумму
(аналитика, суммарный баланс, итоги долгов/подписок) один раз вызывается
`currency_repository.list_rates()`, и все дальнейшие конвертации идут через `RateBook`
в CPU:

- `_direct: dict[(base, quote), Decimal]` — прямые котировки из БД.
- `factor(src, dst)`:
  1. `src == dst` → `1`.
  2. Прямая пара `(src, dst)` в `_direct`.
  3. Обратная пара `(dst, src)` → `1 / rate`.
  4. **One-hop pivot**: перебирает `_PIVOTS = ("USD", "USDT", "EUR", "UZS", "RUB", "KZT", "GBP")`
     и ищет `factor(src, pivot) * factor(pivot, dst)` — то есть поддерживается ровно
     один промежуточный переход, не полный граф Дейкстры/Беллмана-Форда.
  5. Результат кэшируется в `_factors` (мемоизация на весь срок жизни объекта `RateBook`).
- `convert(amount, src, dst, quantize=True)` — возвращает `None`, если путь конвертации
  не найден (UI обязан показывать предупреждение «нет курса», а не подставлять 0).

`invalidate_rate_book_cache()` (presentation/utils.py) сбрасывает закэшированный
`RateBook` в presentation-слое после фонового обновления курсов, чтобы UI не показывал
устаревшие агрегаты до следующей явной перезагрузки данных.

---

## 7. Presentation layer — состав и паттерны

### 7.1 `AppState` (Observer)

Простой Observer без внешних зависимостей (`subscribe/unsubscribe/notify`). Отдельные
«токены обновления» на каждый экран (`dashboard_token`, `transactions_token`,
`accounts_token`, `goals_token`, `debts_token`, `subscriptions_token`,
`analytics_token`, `budgets_token`) — конкретная страница подписывается только на свой
токен и не перерисовывается при изменениях, не влияющих на неё.

`notify(coalesce=True)` — используется в `bump_refresh()`: если за один тик event-loop
случилось несколько `bump_refresh`, они схлопываются в одно `notify()` через
`loop.call_soon`, что не даёт мобильному UI переигрывать каскад ре-рендеров.

`open_secondary(route)` / `close_secondary()` — навигация на «вторичные» экраны
(`analytics`, `goals`, `debts`, `subscriptions`, `currencies`, `budgets`,
`account:<id>`) поверх/вместо основной вкладки, с явной кнопкой «Назад» внутри самих
страниц (не через системный `page.go`).

### 7.2 Страницы (`lib/presentation/pages/`)

`account_detail.py`, `accounts.py`, `analytics.py`, `budgets.py`, `currencies.py`,
`dashboard.py`, `debts.py`, `goals.py`, `settings.py`, `subscriptions.py`,
`transactions.py` — каждая принимает `(page: ft.Page, state: AppState)` и обычно
принимает опциональный `account_id` (для `AccountDetailPage`).

### 7.3 Виджеты (`lib/presentation/widgets/`)

| Виджет | Назначение |
|--------|------------|
| `account_card.py` | Карточка счёта (баланс, иконка, цвет) |
| `appearance_picker.py` | Выбор темы light/dark/system |
| `category_picker.py` | Полноэкранный выбор категории с группами иконок |
| `charts.py` | Круговая/линейная диаграммы (аналитика), на базе matplotlib |
| `confirm_dialog.py` | Диалог подтверждения удаления/сброса |
| `currency_ticker_picker.py` | Поиск/выбор валюты (fiat + crypto) |
| `date_time_field.py` | Поле выбора даты/времени |
| `debt_card.py` | Карточка долга |
| `dual_add_button.py` | Кнопка быстрого добавления дохода/расхода |
| `empty_state.py` | Заглушка для пустых списков |
| `fullscreen_form.py` | Базовый каркас полноэкранных форм CRUD |
| `goal_progress.py` | Прогресс-бар цели |
| `loading.py` | Индикаторы загрузки |
| `lock_screen.py` | Экран PIN/биометрии |
| `pull_to_refresh.py` | Свайп-обновление списков |
| `quick_add_sheet.py` | Bottom-sheet быстрого добавления операции |
| `splash_screen.py` | Экран заставки при старте |
| `subscription_card.py` | Карточка подписки |
| `summary_card.py` | Карточка сводки (баланс/итоги) |
| `transaction_tile.py` | Строка операции в списке |
| `transfer_sheet.py` | Форма перевода между счетами |

### 7.4 Утилиты (`lib/presentation/utils.py`)

`tr(key, lang, **kwargs)` — обёртка над `localization.t`. `format_money(...)` —
форматирование сумм с учётом валюты. `safe_convert(...)` — безопасная конвертация с
обработкой `None` (нет курса). `load_rate_book(container)` — построение/кэш `RateBook`
для текущего запроса. `run_async(...)` — мост sync callback → async use case внутри
Flet-обработчиков событий.

---

## 8. Безопасность — точный механизм

1. **PIN**: `EncryptionService.hash_pin(pin, salt=None)` — PBKDF2-HMAC-SHA256,
   **120 000 итераций**, случайная соль 16 байт (`secrets.token_bytes`), длина ключа
   32 байта. Хэш и соль хранятся в hex в `SettingsModel.pin_hash` / `pin_salt` —
   отдельно от домена `AppSettings` (см. §4.2). Проверка — `hmac.compare_digest`
   (защита от timing-атак).
2. **Биометрия**: единая точка `lib/infrastructure/services/biometric.py`:
   - `FINANCE_BIOMETRIC_OK=1` — тестовый override, форсирует `VERIFIED`/`AVAILABLE`
     без обращения к ОС (используется в pytest и в CI).
   - Windows: `winrt.windows.security.credentials.ui.UserConsentVerifier` (Windows Hello).
   - Android/iOS: мост `flet_local_auth.FinanseLocalAuth`, регистрируемый в `page` через
     `register_local_auth_service(page)`, только если `is_mobile_platform(page)`.
   - Статусы (`BiometricStatus`) и результаты (`BiometricResult`) — насыщенные enum'ы,
     покрывающие «устройство не поддерживает», «не настроено», «заблокировано
     политикой», «занято», «попытки исчерпаны» и т.д. — UI показывает разный текст для
     каждого случая, а не общий «ошибка».
3. **LockScreen** (`presentation/widgets/lock_screen.py`) — рисуется вместо основного
   контента, пока `AppState.is_unlocked is False`; авто-запрос биометрии подавляется в
   режиме `FLET_FORCE_WEB_SERVER` (Windows Hello бессмысленен для удалённой веб/мобильной
   сессии, привязанной к чужому ПК).

---

## 9. Уведомления

| Компонент | Роль |
|-----------|------|
| `notification_service.py` | Внутренняя очередь уведомлений (`NotificationKind`, `push`, `list_pending`), потребляется UI-баннерами дашборда. |
| `push_notifier.py` | Обёртка над `winotify` (Windows toast) и `flet-android-notifications` (Android); `request_push_permissions()`, `register_android_notifications(page)`. |
| `reminder_scheduler.py` | `schedule_reminders(container, settings, language)` — раз в сутки (или eager при старте) собирает предстоящие долги/подписки/цели и кладёт уведомления в очередь + шлёт OS push. |
| `budgets.py::apply_expense_delta` | Отдельный канал уведомлений о превышении бюджета (80% / 100%), не связанный с ежедневным reminder-sweep — срабатывает **сразу** при операции. |

`FINANCE_DISABLE_PUSH=1` полностью отключает OS-push (используется в тестах и CI, чтобы
не дёргать `winotify`/системные API).

---

## 10. Тестовая инфраструктура

- `tests/conftest.py` — создаёт временную SQLite БД на каждый тест (изоляция), выставляет
  `FINANCE_DISABLE_PUSH=1`.
- `tests/factories.py` — билдеры доменных сущностей с разумными дефолтами (упрощают
  Arrange-часть тестов).
- `tests/unit/` — чистая логика без БД: `RateBook`, quantization, i18n, biometric-stub,
  проекции целей/долгов, billing-логика подписок, презентационные утилиты, smoke-тест
  виджетов.
- `tests/integration/` — полный цикл use case → repository → SQLite: счета, транзакции,
  переводы, цели, долги, подписки, валюты/курсы, экспорт, `align_currencies`, wipe.

Запуск: `python -m pytest -q`; отдельный файл — `python -m pytest tests/integration/test_currencies.py -q`.

---

## 11. Быстрые ссылки на код по темам

| Тема | Файл(ы) |
|------|---------|
| Конфигурация и пути | `lib/core/config.py` |
| Инициализация БД, WAL, индексы | `lib/core/database.py` |
| DI-контейнер | `lib/core/dependencies.py` |
| Логирование | `lib/core/logging_config.py` |
| ORM-модели | `lib/infrastructure/db_models.py` |
| Курсы валют (API) | `lib/infrastructure/api/*.py` |
| Курсы валют (провайдер) | `lib/infrastructure/services/exchange_rate_provider.py` |
| RateBook (in-memory FX) | `lib/domain/services/rate_book.py` |
| PIN / биометрия | `lib/infrastructure/services/encryption_service.py`, `biometric.py` |
| Бэкап / восстановление | `lib/infrastructure/services/backup_service.py` |
| Полный сброс данных | `lib/infrastructure/services/data_reset_service.py` |
| Экспорт (JSON/CSV/PDF) | `lib/domain/use_cases/export_data.py`, `lib/infrastructure/services/export_service.py` |
| Локализация | `lib/infrastructure/services/localization.py` |
| Bootstrap приложения | `lib/main.py` |
| Оболочка UI / навигация | `lib/presentation/app.py` |
| Состояние UI | `lib/presentation/state/app_state.py` |
| Демо-данные | `scripts/seed_demo_data.py` |
| Миграции (dev) | `scripts/migrate.py` |
| Миграции (Alembic) | `migrations/versions/*.py` |
