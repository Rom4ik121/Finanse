# Сборка мобильных приложений

Product: **FinWise**, org: **com.finanse.app**.  
Конфиг: `pyproject.toml` (`[tool.flet]`), `flet.toml`.

---

## Android APK (Windows)

### Требования

- Python 3.11+ с `flet[all]`  
- Android SDK (`%LOCALAPPDATA%\Android\Sdk`)  
- Flutter SDK (скрипт ищет `~\flutter\3.44.8` или `C:\flutter`)

### Команда

Из корня репозитория:

```powershell
.\scripts\build_apk.ps1
```

Скрипт:

1. Настраивает `FLUTTER_ROOT`, `ANDROID_HOME`, UTF-8  
2. Ставит зависимости `flet[all]` + `requirements.txt`  
3. Включает **core library desugaring** (нужно для `flutter_local_notifications`) через Gradle init + патч `build.gradle.kts`  
4. Патчит Android-манифест уведомлений (`flet_android_notifications.patcher --project-root`)  
5. Запускает `flet build apk`; при необходимости дособирает через `flutter build apk`  

Если видите ошибку `requires core library desugaring` — обновите скрипт и перезапустите `.\scripts\build_apk.ps1` (патчи уже внутри).

Вручную:

```powershell
python -m pip install -U "flet[all]" -r requirements.txt
flet build apk --org com.finanse.app --product FinWise
```

### Артефакт

```text
build/apk/*.apk
```

Первая сборка может занять **20–40 минут** (скачивание Flutter/Gradle).

### Permissions (Android)

Заданы в `pyproject.toml` / `flet.toml`:

- биометрия: `USE_BIOMETRIC`, `USE_FINGERPRINT`  
- уведомления: `POST_NOTIFICATIONS`, `VIBRATE`, `RECEIVE_BOOT_COMPLETED`, …  
- точные будильники: `SCHEDULE_EXACT_ALARM`, `USE_EXACT_ALARM`

---

## iOS IPA

**Только macOS** + Xcode 15+ + CocoaPods + Apple Developer Program (~$99/год).

### Подготовка Apple

1. App ID Bundle: `com.finanse.app`  
2. UDID устройства в профиле (Ad Hoc / Development)  
3. Сертификат Apple Distribution / Development  
4. Provisioning profile с этим UDID  

### Сборка на Mac

```bash
cd /path/to/finanse
python3 -m pip install -U "flet[all]" -r requirements.txt

export IOS_TEAM_ID=ВАШ_TEAM_ID
export IOS_PROVISIONING_PROFILE="Finanse Ad Hoc"
export IOS_EXPORT_METHOD=release-testing
./scripts/build_ipa.sh
```

Или:

```bash
flet build ipa \
  --org com.finanse.app \
  --product FinWise \
  --ios-team-id ВАШ_TEAM_ID \
  --ios-provisioning-profile "Finanse Ad Hoc" \
  --ios-export-method release-testing \
  --ios-signing-certificate "Apple Distribution"
```

Артефакт: `build/ipa/*.ipa`.

### Установка на iPhone

| Способ | Как |
|--------|-----|
| Apple Configurator | USB → перетащить IPA → доверить сертификат в Настройках |
| TestFlight | export `app-store-connect` → Transporter → ASC |
| Быстрый прогон | `flet run --ios` в одной Wi‑Fi с Mac |

Face ID: `NSFaceIDUsageDescription` в конфиге Flet.

### Ограничения wheels

Бинарные пакеты (`pydantic-core`, `greenlet`, `matplotlib`, …) должны иметь iOS wheels. Иначе сборка падает — см. [Flet publish](https://flet.dev/docs/publish).

---

## CI без своего Mac (Codemagic)

Пошагово: **[CODEMAGIC.md](CODEMAGIC.md)**.

Кратко:

1. `.\scripts\push_github.ps1`  
2. Codemagic → GitHub → workflow `ios-ipa` из `codemagic.yaml`  
3. Настроить Apple signing / env  
4. Скачать IPA из артефактов  

Бесплатный лимит Codemagic: до ~500 мин/мес (уточнять на сайте).

---

## Брендинг

| Ассет | Путь |
|-------|------|
| Иконка | `assets/icon.png`, `icon.ico`, `icon_android.png` |
| Splash | `assets/splash*.png`, `splash_logo.png` |
| Генерация | `scripts/generate_branding_assets.py` |

Цвет splash в конфиге: чёрный (`#000000`).
