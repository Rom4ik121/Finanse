# Документация FinWise

**FinWise** — кроссплатформенное приложение учёта личных финансов.  
Пакет / репозиторий / каталог данных: **`finanse`**. Bundle ID: **`com.finanse.app`**.

| | |
|--|--|
| Версия | 0.1.0 |
| Язык | Python ≥ 3.11 |
| UI | Flet ≥ 0.83 (рекомендуется 0.83–0.86) |
| БД | SQLite + SQLAlchemy 2 |
| Архитектура | Clean Architecture |
| Языки UI | русский, English, o‘zbek |

## Содержание

| Документ | О чём |
|----------|--------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Слои, DI, bootstrap, навигация |
| [FEATURES.md](FEATURES.md) | Экраны и возможности |
| [DATA_MODEL.md](DATA_MODEL.md) | Сущности, таблицы, связи |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Запуск, тесты, seed, пути БД, env |
| [BUILD.md](BUILD.md) | Сборка APK / IPA |
| [CODEMAGIC.md](CODEMAGIC.md) | CI: IPA через Codemagic |

## Быстрый старт

```powershell
cd C:\Users\Admin\Desktop\Projects\finanse
python -m pip install -r requirements.txt
python scripts/migrate.py
python main.py
```

Демо-данные для стресс-теста:

```powershell
python scripts/seed_demo_data.py --wipe --scale medium --currency UZS
```

Сборка APK:

```powershell
.\scripts\build_apk.ps1
```

## Именование

- **FinWise** — имя продукта в UI и сборках Flet  
- **finanse** — имя пакета Python, `data_dir`, логи (`finanse.*`)  
- **com.finanse.app** — org / package name Android и iOS  
