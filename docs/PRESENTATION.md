# Презентационный слой (UI)

## Навигация и корневой контроллер (`app.py`)

`FinanseApp` — корневой контроллер:
- Плавающая `NavigationBar` (4 вкладки: Главная, Операции, Счета, Настройки).
- `AnimatedSwitcher` для плавной смены контента.
- Кэш primary/secondary страниц.
- PIN-гейт: если задан PIN, при старте показывается `LockScreen`.
- Вторичные маршруты: `analytics`, `account:{id}`, `goals`, `debts`,
  `subscriptions`, `currencies`, `budgets`.

## Состояние (`state/app_state.py`)

`AppState` — центральное состояние с Observer-паттерном:
- `subscribe(listener)` / `notify()` — оповещение подписчиков (с coalescing).
- `bump_refresh(*scopes)` — инкремент токенов обновления страниц.
- `set_tab`, `open_secondary`, `close_secondary` — навигация.
- `set_settings`, `set_unlocked`, `push_notification`, `request_view_rebuild`.
- Свойства: `language`, `base_currency`, `theme_mode`.

## Страницы (`pages/`)

| Страница | Назначение |
|---|---|
| `dashboard.py` | Общий баланс, быстрые действия, аналитика, ярлыки, бюджеты месяца |
| `transactions.py` | Список операций: поиск, фильтры, группировка по дню/неделе/месяцу, CRUD, редактор перевода |
| `accounts.py` | CRUD счетов, мультивалютный показ, иконки/цвета, переводы |
| `account_detail.py` | Детали счёта: статистика, графики, операции |
| `analytics.py` | Аналитика: периоды, графики доходов/расходов |
| `goals.py` | Цели: прогресс, взносы, проекция, история, CRUD |
| `debts.py` | Долги: фильтры, погашение, проценты, проекция, история |
| `subscriptions.py` | Подписки: CRUD, автоплатежи, аналитика |
| `currencies.py` | Валюты и курсы: список, обновление |
| `budgets.py` | Бюджеты: лимиты, прогресс, алерты |
| `settings.py` | Настройки: тема, язык, валюта, уведомления, безопасность, экспорт, бэкап, сброс |

## Виджеты (`widgets/`)

| Виджет | Назначение |
|---|---|
| `AccountCard` | Карточка счёта |
| `TransactionTile` | Строка операции |
| `GoalProgress` | Карточка цели с прогресс-баром |
| `DebtCard` | Карточка долга |
| `SubscriptionCard` | Карточка подписки |
| `SummaryCard` | Карточка-сумма (hero) |
| `EmptyState` | Пустое состояние с действием |
| `Loading` | Индикатор загрузки |
| `ConfirmDialog` | Диалог подтверждения |
| `FullscreenForm` | Полноэкранная форма (оверлей) |
| `QuickAddSheet` | Быстрое добавление операции |
| `TransferSheet` | Перевод между счетами |
| `CategoryPicker` | Выбор категории |
| `CurrencyTickerPicker` | Выбор валюты (с поиском) |
| `DateTimeField` | Поле даты/времени |
| `AppearancePicker` | Выбор цвета/иконки |
| `LockScreen` | Экран блокировки (PIN/биометрия) |
| `SplashScreen` | Заставка при запуске |
| `PullToRefresh` | Обновление свайпом |
| `Charts` | Графики (matplotlib) |
| `DualAddButton` | Кнопки «+ Расход / + Доход» |

## Утилиты (`utils.py`)

- `format_money(amount, currency)` — форматирование суммы.
- `format_date(dt)` — форматирование даты.
- `run_async(page, coro, *args)` — запуск корутины в контексте Flet.
- `safe_update(control)` — безопасный `update()`.
- `snack(page, message, error=False)` — всплывающее уведомление.
- `tr(key, lang, **kwargs)` — перевод (обёртка над `localization.t`).
- `load_rate_book(container)` / `invalidate_rate_book_cache()` — кэш курсов.
- `convert_currency_safe(...)` — безопасная конвертация.

## Тема и стили

- `theme.py`: `build_theme(dark)`, `apply_theme(page, mode)`, `page_gradient(dark)`.
- `styles.py`: `card_surface`, `page_header`, `section_title`, `summary_strip`,
  `shortcut_chip`, `muted_text`, `icon_badge`, `amount_color`, `h_scroll`, `v_scroll_body`.

## Иконки

- `icon_registry.py`: `ICON_MAP` (ключ → `ft.IconData`), `resolve_icon(name)`.
- `account_icons.py`: ключи `ccy_<CODE>` для валют/крипто, глифы
  (`₿`, `Ξ`, `₮` …), `account_icon_control()`, `account_icon_groups()`.

## Локализация

- `localization.py`: словарь `_STRINGS` (ru/en/uz), `t(key, lang, **fmt)`,
  `tr(...)`, `normalize_lang()`, `localize_category_name()`.
- Поддерживаемые языки: `ru`, `en`, `uz`.

## Ввод денег (`money_input.py`)

- `make_amount_field(lang, ...)` — текстовое поле с группировкой разрядов.
- `parse_amount(text)` — парсер (поддержка `,`/`.` разделителей).
- `attach_grouped_digits(field, lang, extra_on_change)` — живая группировка.