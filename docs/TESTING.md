# Тестирование

## Запуск

```bash
pytest                 # все тесты
pytest tests/unit      # юнит-тесты
pytest tests/integration  # интеграционные тесты
```

Конфигурация в `pytest.ini`:
- `testpaths = tests`
- `pythonpath = .`
- игнорирование DeprecationWarning.

## Фикстуры (`tests/conftest.py`)

- `_disable_os_push` (autouse) — ставит `FINANCE_DISABLE_PUSH=1`, чтобы тесты
  не отправляли реальные OS-уведомления.
- `container(tmp_path)` — изолированный SQLite-контейнер в tmp-каталоге
  (сброс engine, init_db, build_container).
- `run_async(coro)` / `async_run` — запуск корутин без pytest-asyncio.

## Фабрики (`tests/factories.py`)

- `make_account(name, currency, balance)`
- `make_transaction(account_id, amount, category, tx_type, currency, goal_id, debt_id)`
- `make_goal(name, target, current, currency)`
- `make_debt(counterparty, amount, direction, currency, interest_rate)`
- `make_subscription(account_id, name, amount, periodicity, next_billing, ...)`
- `make_category(name, kind, is_system)`

## Юнит-тесты (`tests/unit/`)

| Файл | Покрытие |
|---|---|
| `test_money.py` | Квантование денег и курсов |
| `test_budget.py` | Валидация Budget, прогресс, перерасход |
| `test_biometric.py` | Биометрия: env-оверрайд, мобильный probe/auth, статусы |
| `test_encryption.py` | Хэширование/проверка PIN |
| `test_localization.py` | Переводы, normalize_lang, локализация категорий |
| `test_backup_service.py` | Бэкап/восстановление файлов |
| `test_currency_codes.py` | Нормализация кодов валют |
| `test_currency_options.py` | Опции выпадающего списка валют |
| `test_currency_rate_format.py` | Форматирование курсов |
| `test_currency_ticker_search.py` | Поиск валют |
| `test_money_input.py` | Парсер и группировка денег |
| `test_date_time_field.py` | Поле даты/времени |
| `test_goal_projection.py` | Прогноз целей |
| `test_debt_projection.py` | Прогноз долгов |
| `test_subscription_billing.py` | Биллинг подписок |
| `test_reminder_scheduler.py` | Планировщик напоминаний |
| `test_notification_service.py` | Очередь уведомлений |
| `test_push_notifier.py` | Push-уведомления |
| `test_rate_book.py` | Книга курсов |
| `test_app_state.py` | Состояние приложения |
| `test_account_icons.py` | Иконки счетов |
| `test_account_stats.py` | Агрегация статистики счёта |
| `test_analytics_period.py` | Пресеты периодов |
| `test_color_palette.py` | Палитра цветов |
| `test_icon_catalog.py` | Каталог иконок |
| `test_presentation_utils.py` | Утилиты презентации |
| `test_ui_widgets_smoke.py` | Смоук-тесты виджетов |

## Интеграционные тесты (`tests/integration/`)

| Файл | Покрытие |
|---|---|
| `test_accounts.py` | CRUD счетов, пересчёт баланса |
| `test_transactions.py` | Обновление/удаление операций, фильтры, статистика |
| `test_transfers.py` | Переводы: пары, FX-конвертация, ошибки, удаление, исключение из статистики/бюджетов |
| `test_goals.py` | CRUD целей, взносы, проекция |
| `test_debts.py` | CRUD долгов, погашение, проценты |
| `test_subscriptions.py` | CRUD подписок, обработка наступивших |
| `test_budgets.py` | Лимиты, прогресс, пересчёт |
| `test_categories.py` | CRUD категорий, find_or_create |
| `test_currencies.py` | Валюты, курсы |
| `test_exchange_rate_upsert.py` | Upsert курсов |
| `test_safe_convert.py` | Безопасная конвертация |
| `test_settings_export_align.py` | Настройки, экспорт, выравнивание валют |

## Рекомендации

- Новые сценарии добавляйте в `tests/integration/` через фикстуру `container`.
- Чистые функции (квантование, проекции, парсеры) — в `tests/unit/`.
- Для тестов биометрии используйте env `FINANCE_BIOMETRIC_OK=1` или
  подмену `set_local_auth_service()`.
- Не отправляйте реальные push в тестах (авто-фикстура отключает).