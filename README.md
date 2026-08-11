# Finanse

Кроссплатформенное приложение для учёта личных финансов на **Python 3.11+** и **Flet 0.83**.

Локальное хранение: SQLite + SQLAlchemy. Архитектура: Clean Architecture (domain → use cases → infrastructure → presentation).

## Быстрый старт

```bash
python -m pip install -r requirements.txt
python scripts/migrate.py
python main.py
```

Первый запуск создаёт каталог данных пользователя (например `~/.finanse` / AppData), БД, настройки и счёт «Наличные».

## Миграция БД

```bash
python scripts/migrate.py
```

Скрипт:

- создаёт таблицы SQLAlchemy;
- загружает валюты из `assets/data/currencies.json`;
- создаёт настройки по умолчанию (язык `ru`, валюта `RUB`);
- добавляет счёт «Наличные», если счетов ещё нет.

## Сборка APK (Flet)

Из корня проекта:

```bash
python -m pip install "flet[all]"
flet build apk
```

Артефакт появится в `build/apk/`. Нужны Android SDK и окружение из [документации Flet](https://flet.dev/docs/publish/android).

### iOS / IPA (только macOS)

`flet build ipa` **нельзя** выполнить на Windows — нужны Mac, Xcode 15+, CocoaPods и аккаунт [Apple Developer Program](https://developer.apple.com/programs/) (~$99/год).

#### 1. Подготовка Apple

1. Зарегистрируйтесь в Apple Developer Program.
2. [Certificates, Identifiers & Profiles](https://developer.apple.com/account/resources/identifiers/list): создайте App ID с Bundle ID `com.finanse.app`.
3. Зарегистрируйте iPhone 12: подключите к Mac → Xcode → Window → Devices and Simulators → скопируйте **Identifier (UDID)**. Добавьте устройство в Developer Portal.
4. Создайте сертификат **Apple Distribution** (или Development) и provisioning profile типа **Ad Hoc** (для установки на свой iPhone) или **Development**. В профиль обязательно включите UDID iPhone 12.
5. Установите `.cer` и `.mobileprovision` на Mac (см. [документацию Flet](https://flet.dev/docs/publish/ios/)).

#### 2. Сборка IPA на Mac

```bash
cd /path/to/finanse
python3 -m pip install -U "flet[all]" -r requirements.txt

export IOS_TEAM_ID=ВАШ_TEAM_ID          # 10 символов, Membership
export IOS_PROVISIONING_PROFILE="Finanse Ad Hoc"
export IOS_EXPORT_METHOD=release-testing  # Ad Hoc на устройство
./scripts/build_ipa.sh
```

Или вручную:

```bash
flet build ipa \
  --org com.finanse.app \
  --product Finanse \
  --ios-team-id ВАШ_TEAM_ID \
  --ios-provisioning-profile "Finanse Ad Hoc" \
  --ios-export-method release-testing \
  --ios-signing-certificate "Apple Distribution"
```

Готовый файл: `build/ipa/*.ipa`.

#### 3. Установка на iPhone 12

**Вариант A — Apple Configurator (удобно с Mac):**

1. Установите [Apple Configurator](https://apps.apple.com/app/apple-configurator/id1037126344) из Mac App Store.
2. Подключите iPhone 12 по USB, разблокируйте, нажмите «Доверять».
3. Перетащите `.ipa` на устройство в Configurator → Install.
4. На iPhone: **Настройки → Основные → VPN и управление устройством** → доверьте сертификат разработчика → откройте Finanse.

**Вариант B — TestFlight (без USB, нужен App Store Connect):**

```bash
flet build ipa ... --ios-export-method app-store-connect
```

Загрузите IPA через приложение Transporter → в [App Store Connect](https://appstoreconnect.apple.com) добавьте себя как внутреннего тестера → установите TestFlight на iPhone и примите приглашение.

**Вариант C — быстрый прогон без IPA (та же Wi‑Fi сеть, Mac):**

```bash
flet run --ios
```

На iPhone откройте показанный URL в Safari (или через QR из терминала).

#### Ограничения зависимостей

Для iOS нужны [готовые wheels](https://flet.dev/docs/publish) у бинарных пакетов (`pydantic-core`, `greenlet`, `matplotlib`, `reportlab` и т.д.). Если сборка упадёт на пакете без iOS-wheel — временно уберите тяжёлую зависимость или замените реализацию под mobile.

### GitHub + Codemagic (IPA без своего Mac)

1. Залить репозиторий на GitHub:

```powershell
.\scripts\push_github.ps1
```

2. Полная пошаговая инструкция: **[docs/CODEMAGIC.md](docs/CODEMAGIC.md)**  
   (Apple Developer, сертификаты, workflow `ios-ipa`, скачивание IPA).

Файл **`codemagic.yaml`** уже в корне — Codemagic подхватит его автоматически.

## Структура проекта

```text
lib/
  core/             # config, database, DI, logging
  domain/           # entities, repository ABCs, use cases
  infrastructure/   # SQLAlchemy repos, API clients, services
  presentation/     # Flet UI: pages, widgets, state, theme
  main.py           # bootstrap (logging, db, background rates, Flet)
main.py             # точка входа
scripts/migrate.py  # миграция и seed
assets/data/        # currencies.json и пр.
```

## Основные экраны

Нижняя навигация (4 вкладки): **Главная**, **Операции**, **Счета**, **Настройки**.

С главной и из настроек открываются: цели, долги, подписки, валюты.

## Тесты

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

Покрытие:

- `tests/unit/` — money, i18n (ru/en/uz), PIN, biometrics stub, backup, notifications, AppState, format helpers, icon keys, UI smoke (карточки/графики)
- `tests/integration/` — счета, операции/статистика, цели, долги, подписки, категории, FX, экспорт, align currency, wipe
- `tests/test_money_and_transactions.py` — базовые денежные сценарии

## Миграции (Alembic)

```bash
alembic upgrade head
```

Для повседневной разработки достаточно `python scripts/migrate.py` (create_all + seed + patch колонок).

## Зависимости

См. `requirements.txt`: Flet, SQLAlchemy, Pydantic, httpx, matplotlib, reportlab, Alembic, pytest и др.

## Безопасность

- PIN сохраняется как PBKDF2-hash и блокирует приложение при старте.
- Биометрия: переключатель в настройках; на desktop это stub (для тестов `FINANCE_BIOMETRIC_OK=1`).
