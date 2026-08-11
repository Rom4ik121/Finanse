# Finanse — сборка IPA через Codemagic (бесплатно до 500 мин/мес)

Проект уже содержит `codemagic.yaml` в корне. После push на GitHub остаётся настроить Apple-подпись и запустить workflow **`ios-ipa`**.

## Что нужно заранее

| Требование | Зачем |
|------------|--------|
| Репозиторий на **GitHub** | Codemagic подключается к Git |
| **Apple Developer Program** (~$99/год) | Подпись IPA для iPhone |
| **UDID iPhone 12** | В Ad Hoc профиле |
| App ID `com.finanse.app` | Совпадает с `flet.toml` / `pyproject.toml` |
| **Team ID** (10 символов) | Membership в Apple Developer |

---

## Шаг 1. Залить проект на GitHub (Windows)

В PowerShell из корня проекта:

```powershell
.\scripts\push_github.ps1
```

Или вручную:

```powershell
cd C:\Users\Admin\Desktop\Projects\finanse
gh auth login
gh repo create finanse --private --source=. --remote=origin --push
```

Проверьте на github.com, что в репозитории есть `codemagic.yaml`, `main.py`, `requirements.txt`.

---

## Шаг 2. Регистрация Codemagic

1. Откройте [codemagic.io](https://codemagic.io) → **Sign up with GitHub**.
2. Разрешите доступ к репозиторию **finanse** (или ко всем).
3. **Add application** → выберите репозиторий **finanse**.
4. Тип конфигурации: **codemagic.yaml** (не Flutter workflow editor).

> Бесплатно: **500 минут/мес** на macOS M2 для **личного** аккаунта Codemagic.

---

## Шаг 3. Apple — App ID и устройство

1. [developer.apple.com](https://developer.apple.com/account) → **Certificates, Identifiers & Profiles**.
2. **Identifiers** → **+** → App → Bundle ID: **`com.finanse.app`**.
3. **Devices** → **+** → добавьте iPhone 12 (UDID):
   - Подключите iPhone к Mac → Xcode → Window → Devices and Simulators, или
   - На iPhone: Settings → General → About (UDID через Finder на Mac).
4. Запишите **Team ID**: Membership details (10 символов, например `AB12CD34EF`).

---

## Шаг 4. Сертификат и Ad Hoc профиль

### Сертификат (Distribution)

1. На Mac: Keychain Access → Certificate Assistant → **Request a Certificate** → сохраните `.certSigningRequest`.
2. Developer Portal → **Certificates** → **+** → **Apple Distribution** → загрузите CSR → скачайте `.cer` → двойной клик (в Keychain).
3. Keychain → сертификат **Apple Distribution** → Export → **.p12** (задайте пароль).

### Provisioning Profile (Ad Hoc)

1. **Profiles** → **+** → **Ad Hoc** → App ID `com.finanse.app`.
2. Выберите Distribution certificate.
3. Отметьте **iPhone 12** (UDID).
4. Скачайте `.mobileprovision`.

---

## Шаг 5. Загрузка подписи в Codemagic

1. Codemagic → **Teams** → ваш team → **codemagic.yaml settings** → **Code signing identities**.
2. Вкладка **iOS certificates** → загрузите `.p12`, пароль, reference name: `finanse_distribution`.
3. Вкладка **iOS provisioning profiles** → загрузите `.mobileprovision`, reference: `finanse_adhoc`.
4. У профиля тип **ad_hoc**, Bundle ID **`com.finanse.app`**.

**Альтернатива (без ручного .p12):** подключить **App Store Connect API key** в Integrations и использовать `app-store-connect fetch-signing-files` — см. [доку Codemagic](https://docs.codemagic.io/yaml-code-signing/signing-ios/).

---

## Шаг 6. Переменные окружения

1. Codemagic → **Environment variables** → группа **`finanse_ios`** (имя из `codemagic.yaml`).
2. Добавьте:

| Variable | Value | Secure |
|----------|--------|--------|
| `APPLE_TEAM_ID` | ваш Team ID | нет |

3. В workflow **ios-ipa** укажите группу `finanse_ios` (уже в yaml).

---

## Шаг 7. Запуск сборки

1. В приложении **finanse** → **Start new build**.
2. Workflow: **`ios-ipa`** (Finanse iOS IPA Ad Hoc).
3. Branch: **main** → **Start build**.

Первая сборка может занять **30–60+ минут** (зависимости Flet + Xcode).

### Если подпись ещё не готова

Запустите **`ios-smoke`** — проверка, что проект собирается на macOS (без гарантии IPA).

---

## Шаг 8. Скачать IPA

1. После успешного билда → **Artifacts** → скачайте `*.ipa`.
2. Установка на iPhone 12:
   - **Mac + Apple Configurator**: USB → перетащить IPA на устройство;
   - или **TestFlight** (нужен workflow с `app-store-connect` export).

На iPhone: **Settings → General → VPN & Device Management** → Trust developer.

---

## Установка IPA без Mac

Codemagic только **собирает** IPA. На Windows без Mac:

1. **TestFlight** — загрузите IPA через Transporter (нужен Mac один раз или CI step `app-store-connect publish`).
2. **AltStore / Sideloadly** — для Ad Hoc, если IPA подписан под ваш UDID (ограничения Apple).
3. Попросить друга с Mac установить через Apple Configurator.

---

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| `APPLE_TEAM_ID is missing` | Группа `finanse_ios` + переменная в UI |
| No matching provisioning profile | Bundle ID / тип ad_hoc / UDID в профиле |
| Binary wheel not found for iOS | Пакет без iOS wheel — см. лог; упростить deps |
| Build timeout | Увеличить `max_build_duration` в yaml |
| 500 min exhausted | Ждать новый месяц или включить billing |

---

## Полезные ссылки

- [Codemagic — iOS signing](https://docs.codemagic.io/yaml-code-signing/signing-ios/)
- [Flet — iOS publish](https://flet.dev/docs/publish/ios/)
- [Codemagic pricing (500 free min)](https://docs.codemagic.io/billing/pricing/)
