"""RU/EN/UZ UI string dictionaries and translation helper."""

from __future__ import annotations

import logging
from typing import Mapping

logger = logging.getLogger("finanse.infrastructure.services.localization")

SUPPORTED_LANGS = ("ru", "en", "uz")
DEFAULT_LANG = "ru"

STRINGS: dict[str, dict[str, str]] = {
    "account.balance": {
        "ru": "Баланс",
        "en": "Balance",
        "uz": "Balans",
    },
    "account.default_cash": {
        "ru": "Наличные",
        "en": "Cash",
        "uz": "Naqd pul",
    },
    "action.add": {
        "ru": "Добавить",
        "en": "Add",
        "uz": "Qo‘shish",
    },
    "action.apply": {
        "ru": "Применить",
        "en": "Apply",
        "uz": "Qo‘llash",
    },
    "action.backup": {
        "ru": "Резервная копия",
        "en": "Backup",
        "uz": "Zaxira nusxa",
    },
    "action.cancel": {
        "ru": "Отмена",
        "en": "Cancel",
        "uz": "Bekor qilish",
    },
    "action.confirm_delete": {
        "ru": "Подтвердите удаление",
        "en": "Confirm delete",
        "uz": "O‘chirishni tasdiqlang",
    },
    "action.delete": {
        "ru": "Удалить",
        "en": "Delete",
        "uz": "O‘chirish",
    },
    "action.edit": {
        "ru": "Изменить",
        "en": "Edit",
        "uz": "Tahrirlash",
    },
    "action.export": {
        "ru": "Экспорт",
        "en": "Export",
        "uz": "Eksport",
    },
    "action.filters": {
        "ru": "Фильтры",
        "en": "Filters",
        "uz": "Filtrlar",
    },
    "action.quick_add": {
        "ru": "Быстрый доход / расход",
        "en": "Quick income / expense",
        "uz": "Tezkor daromad / xarajat",
    },
    "action.refresh": {
        "ru": "Обновить",
        "en": "Refresh",
        "uz": "Yangilash",
    },
    "action.reset": {
        "ru": "Сбросить",
        "en": "Reset",
        "uz": "Tozalash",
    },
    "action.restore": {
        "ru": "Восстановить",
        "en": "Restore",
        "uz": "Tiklash",
    },
    "action.save": {
        "ru": "Сохранить",
        "en": "Save",
        "uz": "Saqlash",
    },
    "action.saved": {
        "ru": "Сохранено",
        "en": "Saved",
        "uz": "Saqlandi",
    },
    "app.name": {
        "ru": "FinWise",
        "en": "FinWise",
        "uz": "FinWise",
    },
    "app.tagline": {
        "ru": "Личный учёт финансов",
        "en": "Personal finance tracking",
        "uz": "Shaxsiy moliya hisobi",
    },
    "category.both": {
        "ru": "Доход и расход",
        "en": "Income & expense",
        "uz": "Daromad va xarajat",
    },
    "category.create": {
        "ru": "+ Новая категория",
        "en": "+ New category",
        "uz": "+ Yangi kategoriya",
    },
    "category.edit": {
        "ru": "Категория",
        "en": "Category",
        "uz": "Kategoriya",
    },
    "category.other": {
        "ru": "Прочее",
        "en": "Other",
        "uz": "Boshqa",
    },
    "category.savings": {
        "ru": "Накопление",
        "en": "Savings",
        "uz": "Jamg‘arma",
    },
    "chart.add_month_ops": {
        "ru": "Добавьте операции за месяц",
        "en": "Add transactions for the month",
        "uz": "Oy uchun amaliyotlar qo‘shing",
    },
    "chart.dynamics_empty": {
        "ru": "Динамика появится после операций",
        "en": "Trend appears after transactions",
        "uz": "Dinamika amaliyotlardan keyin paydo bo‘ladi",
    },
    "chart.no_data": {
        "ru": "Нет данных",
        "en": "No data",
        "uz": "Ma’lumot yo‘q",
    },
    "chart.no_expenses": {
        "ru": "Нет расходов",
        "en": "No expenses",
        "uz": "Xarajatlar yo‘q",
    },
    "chart.total": {
        "ru": "Всего",
        "en": "Total",
        "uz": "Jami",
    },
    "currencies.crypto": {
        "ru": "Криптовалюты",
        "en": "Cryptocurrencies",
        "uz": "Kriptovalyutalar",
    },
    "currencies.fiat": {
        "ru": "Фиатные валюты",
        "en": "Fiat currencies",
        "uz": "Fiat valyutalar",
    },
    "currencies.refresh": {
        "ru": "Обновить курсы",
        "en": "Refresh rates",
        "uz": "Kurslarni yangilash",
    },
    "currencies.compare": {
        "ru": "Сравнение валют",
        "en": "Compare currencies",
        "uz": "Valyutalarni solishtirish",
    },
    "currencies.compare_hint": {
        "ru": "Введите сумму и выберите пару валют",
        "en": "Enter an amount and pick a currency pair",
        "uz": "Summani kiriting va valyuta juftligini tanlang",
    },
    "currencies.amount": {
        "ru": "Сумма",
        "en": "Amount",
        "uz": "Summa",
    },
    "currencies.from": {
        "ru": "Из",
        "en": "From",
        "uz": "Dan",
    },
    "currencies.to": {
        "ru": "В",
        "en": "To",
        "uz": "Ga",
    },
    "currencies.swap": {
        "ru": "Поменять местами",
        "en": "Swap",
        "uz": "Almashtirish",
    },
    "currencies.result": {
        "ru": "Результат",
        "en": "Result",
        "uz": "Natija",
    },
    "currencies.unit_rate": {
        "ru": "1 {src} = {rate} {dst}",
        "en": "1 {src} = {rate} {dst}",
        "uz": "1 {src} = {rate} {dst}",
    },
    "currencies.no_rate": {
        "ru": "Нет курса для этой пары — обновите курсы",
        "en": "No rate for this pair — refresh rates",
        "uz": "Bu juftlik uchun kurs yo‘q — kurslarni yangilang",
    },
    "currencies.base_rates": {
        "ru": "Курсы к {base}",
        "en": "Rates vs {base}",
        "uz": "{base} ga nisbatan kurslar",
    },
    "currencies.search": {
        "ru": "Поиск тикера",
        "en": "Search ticker",
        "uz": "Ticker qidirish",
    },
    "currencies.search_hint": {
        "ru": "USD, EUR, BTC…",
        "en": "USD, EUR, BTC…",
        "uz": "USD, EUR, BTC…",
    },
    "currencies.not_found": {
        "ru": "Валюты не найдены",
        "en": "No currencies found",
        "uz": "Valyutalar topilmadi",
    },
    "dashboard.charts": {
        "ru": "Аналитика",
        "en": "Analytics",
        "uz": "Tahlil",
    },
    "dashboard.dynamics": {
        "ru": "Динамика за период",
        "en": "Trend over time",
        "uz": "Davr dinamikasi",
    },
    "dashboard.dynamics_hint": {
        "ru": "Зелёный — доходы, красный — расходы по дням",
        "en": "Green — income, red — expenses by day",
        "uz": "Yashil — daromad, qizil — kunlik xarajatlar",
    },
    "dashboard.expense_hint": {
        "ru": "Доли категорий в расходах за текущий месяц",
        "en": "Category share of expenses this month",
        "uz": "Joriy oy xarajatlarida kategoriyalar ulushi",
    },
    "dashboard.month_expense": {
        "ru": "Расход за месяц",
        "en": "Month expense",
        "uz": "Oy xarajati",
    },
    "dashboard.month_income": {
        "ru": "Доход за месяц",
        "en": "Month income",
        "uz": "Oy daromadi",
    },
    "dashboard.shortcuts": {
        "ru": "Разделы",
        "en": "Sections",
        "uz": "Bo‘limlar",
    },
    "dashboard.total_balance": {
        "ru": "Общий баланс",
        "en": "Total balance",
        "uz": "Umumiy balans",
    },
    "debt.due_by": {
        "ru": "До {date}",
        "en": "Due {date}",
        "uz": "Muddat: {date}",
    },
    "debt.i_owe": {
        "ru": "Я должен",
        "en": "I owe",
        "uz": "Men qarzdorman",
    },
    "debt.interest_per_year": {
        "ru": "{rate}% / год",
        "en": "{rate}% / year",
        "uz": "{rate}% / yil",
    },
    "debt.no_due_date": {
        "ru": "Без срока",
        "en": "No due date",
        "uz": "Muddat yo‘q",
    },
    "debt.owed_to_me": {
        "ru": "Мне должны",
        "en": "Owed to me",
        "uz": "Menga qarzdorlar",
    },
    "debt.receive": {
        "ru": "Получить",
        "en": "Receive",
        "uz": "Olish",
    },
    "debt.record_cash": {
        "ru": "Сразу провести по счёту",
        "en": "Post to account now",
        "uz": "Hisobga darhol o‘tkazish",
    },
    "debt.repay": {
        "ru": "Погасить",
        "en": "Repay",
        "uz": "To‘lash",
    },
    "debt.status.active": {
        "ru": "Активен",
        "en": "Active",
        "uz": "Faol",
    },
    "debt.status.paid": {
        "ru": "Погашен",
        "en": "Paid",
        "uz": "To‘langan",
    },
    "debts.reminders": {
        "ru": "Ближайшие платежи по долгам",
        "en": "Upcoming debt payments",
        "uz": "Yaqinlashayotgan qarz to‘lovlari",
    },
    "debts.total_i_owe": {
        "ru": "Я должен",
        "en": "I owe",
        "uz": "Men qarzdorman",
    },
    "debts.total_owed_to_me": {
        "ru": "Мне должны",
        "en": "Owed to me",
        "uz": "Menga qarzdorlar",
    },
    "empty.accounts": {
        "ru": "Добавьте первый счёт",
        "en": "Add your first account",
        "uz": "Birinchi hisobni qo‘shing",
    },
    "empty.debts": {
        "ru": "Долгов пока нет",
        "en": "No debts yet",
        "uz": "Hali qarzlar yo‘q",
    },
    "empty.goals": {
        "ru": "Целей пока нет",
        "en": "No goals yet",
        "uz": "Hali maqsadlar yo‘q",
    },
    "empty.subscriptions": {
        "ru": "Подписок пока нет",
        "en": "No subscriptions yet",
        "uz": "Hali obunalar yo‘q",
    },
    "empty.transactions": {
        "ru": "Операций пока нет",
        "en": "No transactions yet",
        "uz": "Hali amaliyotlar yo‘q",
    },
    "error.generic": {
        "ru": "Произошла ошибка",
        "en": "Something went wrong",
        "uz": "Xatolik yuz berdi",
    },
    "error.insufficient_funds": {
        "ru": "Недостаточно средств на счёте",
        "en": "Insufficient account balance",
        "uz": "Hisobda mablag‘ yetarli emas",
    },
    "error.network": {
        "ru": "Ошибка сети",
        "en": "Network error",
        "uz": "Tarmoq xatosi",
    },
    "error.no_accounts": {
        "ru": "Сначала добавьте счёт",
        "en": "Add an account first",
        "uz": "Avval hisob qo‘shing",
    },
    "field.account": {
        "ru": "Счёт",
        "en": "Account",
        "uz": "Hisob",
    },
    "field.active": {
        "ru": "Активна",
        "en": "Active",
        "uz": "Faol",
    },
    "field.amount": {
        "ru": "Сумма",
        "en": "Amount",
        "uz": "Summa",
    },
    "field.category": {
        "ru": "Категория",
        "en": "Category",
        "uz": "Kategoriya",
    },
    "field.color": {
        "ru": "Цвет",
        "en": "Color",
        "uz": "Rang",
    },
    "field.comment": {
        "ru": "Комментарий",
        "en": "Comment",
        "uz": "Izoh",
    },
    "field.currency": {
        "ru": "Валюта",
        "en": "Currency",
        "uz": "Valyuta",
    },
    "field.date": {
        "ru": "Дата",
        "en": "Date",
        "uz": "Sana",
    },
    "field.time": {
        "ru": "Время",
        "en": "Time",
        "uz": "Vaqt",
    },
    "date.pick": {
        "ru": "Выберите дату",
        "en": "Pick a date",
        "uz": "Sanani tanlang",
    },
    "date.clear": {
        "ru": "Очистить дату",
        "en": "Clear date",
        "uz": "Sanani tozalash",
    },
    "date.not_set": {
        "ru": "Не указана",
        "en": "Not set",
        "uz": "Belgilanmagan",
    },
    "date.set": {
        "ru": "Указать дату",
        "en": "Set date",
        "uz": "Sanani belgilash",
    },
    "date.set_with_time": {
        "ru": "Указать дату и время",
        "en": "Set date and time",
        "uz": "Sana va vaqtni belgilash",
    },
    "date.change": {
        "ru": "Изменить",
        "en": "Change",
        "uz": "O‘zgartirish",
    },
    "date.hour": {
        "ru": "Час",
        "en": "Hour",
        "uz": "Soat",
    },
    "date.minute": {
        "ru": "Минута",
        "en": "Minute",
        "uz": "Daqiqa",
    },
    "field.direction": {
        "ru": "Направление",
        "en": "Direction",
        "uz": "Yo‘nalish",
    },
    "field.goal": {
        "ru": "Цель накопления",
        "en": "Savings goal",
        "uz": "Jamg‘arma maqsadi",
    },
    "field.icon": {
        "ru": "Иконка",
        "en": "Icon",
        "uz": "Belgisi",
    },
    "field.interest": {
        "ru": "% годовых",
        "en": "Annual %",
        "uz": "Yillik %",
    },
    "field.name": {
        "ru": "Название",
        "en": "Name",
        "uz": "Nomi",
    },
    "field.period": {
        "ru": "Период",
        "en": "Period",
        "uz": "Davr",
    },
    "field.priority": {
        "ru": "Приоритет",
        "en": "Priority",
        "uz": "Muhimlik",
    },
    "field.remaining": {
        "ru": "Остаток",
        "en": "Remaining",
        "uz": "Qoldiq",
    },
    "field.search": {
        "ru": "Поиск",
        "en": "Search",
        "uz": "Qidiruv",
    },
    "field.tags": {
        "ru": "Теги",
        "en": "Tags",
        "uz": "Teglar",
    },
    "field.type": {
        "ru": "Тип",
        "en": "Type",
        "uz": "Tur",
    },
    "filter.all": {
        "ru": "Все",
        "en": "All",
        "uz": "Hammasi",
    },
    "filter.date_from": {
        "ru": "Дата с",
        "en": "From date",
        "uz": "Sana dan",
    },
    "filter.date_to": {
        "ru": "Дата по",
        "en": "To date",
        "uz": "Sana gacha",
    },
    "filter.group.day": {
        "ru": "Дни",
        "en": "Days",
        "uz": "Kunlar",
    },
    "filter.group.month": {
        "ru": "Месяцы",
        "en": "Months",
        "uz": "Oylar",
    },
    "filter.group.week": {
        "ru": "Недели",
        "en": "Weeks",
        "uz": "Haftalar",
    },
    "filter.group_by": {
        "ru": "Группировка",
        "en": "Group by",
        "uz": "Guruhlash",
    },
    "fx.missing_rates": {
        "ru": "Нет курса валют. Откройте «Валюты» и обновите курсы, либо смените валюту счёта.",
        "en": "Missing exchange rates. Open Currencies and refresh, or change the account currency.",
        "uz": "Valyuta kursi yo‘q. «Valyutalar»ni ochib yangilang yoki hisob valyutasini o‘zgartiring.",
    },
    "goal.contribute": {
        "ru": "Внести",
        "en": "Contribute",
        "uz": "Qo‘shish",
    },
    "goal.progress": {
        "ru": "Прогресс",
        "en": "Progress",
        "uz": "Jarayon",
    },
    "goal.progress_hint": {
        "ru": "Прогресс меняется только взносами со счёта",
        "en": "Progress changes only via account contributions",
        "uz": "Jarayon faqat hisobdan badallar orqali o‘zgaradi",
    },
    "goal.target": {
        "ru": "Цель",
        "en": "Target",
        "uz": "Maqsad",
    },
    "goals.total_remaining": {
        "ru": "Ещё нужно",
        "en": "Still needed",
        "uz": "Hali kerak",
    },
    "goals.total_saved": {
        "ru": "Накоплено",
        "en": "Saved",
        "uz": "Yig‘ilgan",
    },
    "goals.total_target": {
        "ru": "Всего по целям",
        "en": "Goals total",
        "uz": "Maqsadlar jami",
    },
    "icon_group.cards": {
        "ru": "Карты и кошельки",
        "en": "Cards & wallets",
        "uz": "Kartalar va hamyonlar",
    },
    "icon_group.crypto": {
        "ru": "Криптовалюты",
        "en": "Cryptocurrencies",
        "uz": "Kriptovalyutalar",
    },
    "icon_group.entertainment": {
        "ru": "Развлечения",
        "en": "Entertainment",
        "uz": "Ko‘ngilochar",
    },
    "icon_group.family": {
        "ru": "Семья и люди",
        "en": "Family & people",
        "uz": "Oila va odamlar",
    },
    "icon_group.fiat": {
        "ru": "Валюты",
        "en": "Currencies",
        "uz": "Valyutalar",
    },
    "icon_group.finance": {
        "ru": "Финансы",
        "en": "Finance",
        "uz": "Moliya",
    },
    "icon_group.food": {
        "ru": "Еда и напитки",
        "en": "Food & drinks",
        "uz": "Oziq-ovqat va ichimliklar",
    },
    "icon_group.health": {
        "ru": "Здоровье",
        "en": "Health",
        "uz": "Salomatlik",
    },
    "icon_group.home": {
        "ru": "Дом и быт",
        "en": "Home & utilities",
        "uz": "Uy va kommunal",
    },
    "icon_group.other": {
        "ru": "Прочее",
        "en": "Other",
        "uz": "Boshqa",
    },
    "icon_group.shopping": {
        "ru": "Покупки",
        "en": "Shopping",
        "uz": "Xaridlar",
    },
    "icon_group.tech": {
        "ru": "Техника",
        "en": "Tech",
        "uz": "Texnika",
    },
    "icon_group.transport": {
        "ru": "Транспорт",
        "en": "Transport",
        "uz": "Transport",
    },
    "icon_group.travel": {
        "ru": "Путешествия",
        "en": "Travel",
        "uz": "Sayohat",
    },
    "icon_group.work": {
        "ru": "Работа и учёба",
        "en": "Work & study",
        "uz": "Ish va o‘qish",
    },
    "invalid_amount": {
        "ru": "Введите корректную сумму",
        "en": "Enter a valid amount",
        "uz": "To‘g‘ri summa kiriting",
    },
    "invalid_date": {
        "ru": "Дата: YYYY-MM-DD или YYYY-MM-DD HH:MM",
        "en": "Date: YYYY-MM-DD or YYYY-MM-DD HH:MM",
        "uz": "Sana: YYYY-MM-DD yoki YYYY-MM-DD HH:MM",
    },
    "lang.en": {
        "ru": "English",
        "en": "English",
        "uz": "English",
    },
    "lang.ru": {
        "ru": "Русский",
        "en": "Русский",
        "uz": "Русский",
    },
    "lang.uz": {
        "ru": "Oʻzbekcha",
        "en": "Oʻzbekcha",
        "uz": "Oʻzbekcha",
    },
    "loading": {
        "ru": "Загрузка…",
        "en": "Loading…",
        "uz": "Yuklanmoqda…",
    },
    "lock.biometric_busy": {
        "ru": "Устройство занято — попробуйте снова",
        "en": "Biometric device is busy — try again",
        "uz": "Qurilma band — qayta urinib ko‘ring",
    },
    "lock.biometric_canceled": {
        "ru": "Вход по биометрии отменён",
        "en": "Biometric sign-in canceled",
        "uz": "Biometrik kirish bekor qilindi",
    },
    "lock.biometric_failed": {
        "ru": "Не удалось подтвердить биометрию — используйте PIN",
        "en": "Biometric verification failed — use PIN",
        "uz": "Biometriyani tasdiqlab bo‘lmadi — PIN dan foydalaning",
    },
    "lock.biometric_no_device": {
        "ru": "Биометрия недоступна на этом устройстве — настройте отпечаток или Face ID",
        "en": "No biometric hardware — enroll fingerprint or Face ID in system settings",
        "uz": "Biometriya qurilmasi yo‘q — tizim sozlamalarida barmoq izi yoki Face ID qo‘shing",
    },
    "lock.biometric_not_configured": {
        "ru": "Биометрия не настроена — добавьте отпечаток или лицо в настройках телефона",
        "en": "Biometrics not set up — enroll fingerprint or face in device settings",
        "uz": "Biometriya sozlanmagan — qurilma sozlamalarida barmoq izi yoki yuz qo‘shing",
    },
    "lock.biometric_policy": {
        "ru": "Биометрия отключена политикой системы",
        "en": "Biometrics disabled by system policy",
        "uz": "Biometriya tizim siyosati bilan o‘chirilgan",
    },
    "lock.biometric_prompt": {
        "ru": "Разблокировать FinWise",
        "en": "Unlock FinWise",
        "uz": "FinWise qulfini ochish",
    },
    "lock.biometric_retries": {
        "ru": "Слишком много попыток — используйте PIN",
        "en": "Too many attempts — use PIN",
        "uz": "Juda ko‘p urinish — PIN dan foydalaning",
    },
    "lock.biometric_unavailable": {
        "ru": "Биометрия недоступна — используйте PIN",
        "en": "Biometrics unavailable — use PIN",
        "uz": "Biometriya mavjud emas — PIN dan foydalaning",
    },
    "lock.subtitle": {
        "ru": "Введите PIN для входа",
        "en": "Enter PIN to continue",
        "uz": "Kirish uchun PIN kiriting",
    },
    "lock.subtitle_bio": {
        "ru": "Подтвердите вход биометрией или введите PIN",
        "en": "Confirm with biometrics or enter your PIN",
        "uz": "Biometriya bilan tasdiqlang yoki PIN kiriting",
    },
    "lock.unlock": {
        "ru": "Разблокировать",
        "en": "Unlock",
        "uz": "Qulfni ochish",
    },
    "lock.wrong_pin": {
        "ru": "Неверный PIN",
        "en": "Incorrect PIN",
        "uz": "Noto‘g‘ri PIN",
    },
    "nav.accounts": {
        "ru": "Счета",
        "en": "Accounts",
        "uz": "Hisoblar",
    },
    "nav.currencies": {
        "ru": "Валюты",
        "en": "Currencies",
        "uz": "Valyutalar",
    },
    "nav.debts": {
        "ru": "Долги",
        "en": "Debts",
        "uz": "Qarzlar",
    },
    "nav.goals": {
        "ru": "Цели",
        "en": "Goals",
        "uz": "Maqsadlar",
    },
    "nav.home": {
        "ru": "Главная",
        "en": "Home",
        "uz": "Bosh sahifa",
    },
    "nav.reports": {
        "ru": "Отчёты",
        "en": "Reports",
        "uz": "Hisobotlar",
    },
    "nav.settings": {
        "ru": "Настройки",
        "en": "Settings",
        "uz": "Sozlamalar",
    },
    "nav.subscriptions": {
        "ru": "Подписки",
        "en": "Subscriptions",
        "uz": "Obunalar",
    },
    "nav.transactions": {
        "ru": "Операции",
        "en": "Transactions",
        "uz": "Amaliyotlar",
    },
    "none": {
        "ru": "Нет",
        "en": "None",
        "uz": "Yo‘q",
    },
    "notify.debt_due": {
        "ru": "Скоро срок погашения долга",
        "en": "Debt due soon",
        "uz": "Qarz to‘lash muddati yaqinlashmoqda",
    },
    "notify.goal_reached": {
        "ru": "Цель достигнута!",
        "en": "Goal reached!",
        "uz": "Maqsadga erishildi!",
    },
    "notify.subscription_due": {
        "ru": "Скоро списание подписки",
        "en": "Subscription billing soon",
        "uz": "Obuna yechib olish yaqinlashmoqda",
    },
    "picker.choose_color": {
        "ru": "Выбрать цвет",
        "en": "Choose color",
        "uz": "Rangni tanlash",
    },
    "picker.choose_icon": {
        "ru": "Выбрать иконку",
        "en": "Choose icon",
        "uz": "Belgini tanlash",
    },
    "picker.close": {
        "ru": "Свернуть",
        "en": "Collapse",
        "uz": "Yig‘ish",
    },
    "settings.appearance": {
        "ru": "Внешний вид",
        "en": "Appearance",
        "uz": "Ko‘rinish",
    },
    "settings.backup_restore": {
        "ru": "Резервные копии",
        "en": "Backups",
        "uz": "Zaxira nusxalar",
    },
    "settings.basics": {
        "ru": "Основные",
        "en": "Basics",
        "uz": "Asosiy",
    },
    "settings.biometric": {
        "ru": "Биометрия",
        "en": "Biometrics",
        "uz": "Biometriya",
    },
    "settings.biometric_hint_missing": {
        "ru": "Сканер не найден. Добавьте отпечаток или Face ID в настройках устройства",
        "en": "No biometric sensor. Enroll fingerprint or Face ID in device settings",
        "uz": "Biometriya sensori topilmadi. Qurilma sozlamalarida barmoq izi yoki Face ID qo‘shing",
    },
    "settings.biometric_hint_ok": {
        "ru": "Отпечаток / Face ID готовы — можно входить по биометрии",
        "en": "Fingerprint / Face ID is ready for unlock",
        "uz": "Barmoq izi / Face ID qulfni ochish uchun tayyor",
    },
    "settings.biometric_hint_unconfigured": {
        "ru": "Добавьте отпечаток или лицо в настройках устройства, затем включите снова",
        "en": "Enroll a fingerprint or face in device settings, then enable again",
        "uz": "Qurilma sozlamalarida barmoq izi yoki yuz qo‘shing, keyin qayta yoqing",
    },
    "settings.biometric_need_pin": {
        "ru": "Сначала установите PIN — биометрия работает вместе с ним",
        "en": "Set a PIN first — biometrics work together with it",
        "uz": "Avval PIN o‘rnating — biometriya u bilan birga ishlaydi",
    },
    "settings.biometric_unsupported": {
        "ru": "Биометрия недоступна на этой платформе",
        "en": "Biometrics are not available on this platform",
        "uz": "Bu platformada biometriya mavjud emas",
    },
    "settings.clear_pin": {
        "ru": "Сбросить PIN",
        "en": "Clear PIN",
        "uz": "PIN ni tozalash",
    },
    "settings.currency_hint": {
        "ru": "Валюта отображения. Операции идут в валюте выбранного счёта.",
        "en": "Display currency. Transactions use the selected account currency.",
        "uz": "Ko‘rsatish valyutasi. Amaliyotlar tanlangan hisob valyutasida.",
    },
    "settings.danger": {
        "ru": "Опасная зона",
        "en": "Danger zone",
        "uz": "Xavfli zona",
    },
    "settings.data": {
        "ru": "Данные",
        "en": "Data",
        "uz": "Ma’lumotlar",
    },
    "settings.default_currency": {
        "ru": "Валюта по умолчанию",
        "en": "Default currency",
        "uz": "Standart valyuta",
    },
    "settings.delete_all_confirm": {
        "ru": "Будут удалены все счета, операции, цели, долги, подписки, курсы и PIN. Это нельзя отменить.",
        "en": "This will delete all accounts, transactions, goals, debts, subscriptions, rates, and PIN. This cannot be undone.",
        "uz": "Barcha hisoblar, amaliyotlar, maqsadlar, qarzlar, obunalar, kurslar va PIN o‘chiriladi. Buni bekor qilib bo‘lmaydi.",
    },
    "settings.delete_all_data": {
        "ru": "Удалить все данные",
        "en": "Delete all data",
        "uz": "Barcha ma’lumotlarni o‘chirish",
    },
    "settings.delete_all_done": {
        "ru": "Все данные удалены",
        "en": "All data deleted",
        "uz": "Barcha ma’lumotlar o‘chirildi",
    },
    "settings.exchange_interval": {
        "ru": "Интервал обновления курсов (мин)",
        "en": "Exchange update interval (min)",
        "uz": "Kurs yangilash oralig‘i (daq)",
    },
    "settings.export": {
        "ru": "Экспорт",
        "en": "Export",
        "uz": "Eksport",
    },
    "settings.export_csv": {
        "ru": "Экспорт CSV",
        "en": "Export CSV",
        "uz": "CSV eksport",
    },
    "settings.export_json": {
        "ru": "Экспорт JSON",
        "en": "Export JSON",
        "uz": "JSON eksport",
    },
    "settings.export_pdf": {
        "ru": "Экспорт PDF",
        "en": "Export PDF",
        "uz": "PDF eksport",
    },
    "settings.goal_milestones": {
        "ru": "Уведомления о целях",
        "en": "Goal milestone alerts",
        "uz": "Maqsad haqida bildirishnomalar",
    },
    "settings.language": {
        "ru": "Язык",
        "en": "Language",
        "uz": "Til",
    },
    "settings.no_backups": {
        "ru": "Нет резервных копий",
        "en": "No backups found",
        "uz": "Zaxira nusxalar topilmadi",
    },
    "settings.restore_confirm": {
        "ru": "Текущие данные будут заменены последней резервной копией. Продолжить?",
        "en": "Current data will be replaced with the latest backup. Continue?",
        "uz": "Joriy ma'lumotlar oxirgi zaxira nusxa bilan almashtiriladi. Davom etasizmi?",
    },
    "settings.restore_done": {
        "ru": "Данные восстановлены",
        "en": "Data restored",
        "uz": "Ma'lumotlar tiklandi",
    },
    "settings.notifications": {
        "ru": "Уведомления",
        "en": "Notifications",
        "uz": "Bildirishnomalar",
    },
    "settings.pin": {
        "ru": "PIN-код",
        "en": "PIN code",
        "uz": "PIN-kod",
    },
    "settings.pin_cleared": {
        "ru": "PIN сброшен",
        "en": "PIN cleared",
        "uz": "PIN tozalandi",
    },
    "settings.pin_min": {
        "ru": "PIN: минимум 4 символа",
        "en": "PIN: at least 4 digits",
        "uz": "PIN: kamida 4 belgi",
    },
    "settings.pin_saved": {
        "ru": "PIN сохранён",
        "en": "PIN saved",
        "uz": "PIN saqlandi",
    },
    "settings.rates": {
        "ru": "Курсы валют",
        "en": "Exchange rates",
        "uz": "Valyuta kurslari",
    },
    "settings.reminder_time": {
        "ru": "Время напоминаний (ЧЧ:ММ)",
        "en": "Reminder time (HH:MM)",
        "uz": "Eslatma vaqti (SS:DD)",
    },
    "settings.sections": {
        "ru": "Разделы",
        "en": "Sections",
        "uz": "Bo‘limlar",
    },
    "settings.security": {
        "ru": "Безопасность",
        "en": "Security",
        "uz": "Xavfsizlik",
    },
    "settings.set_pin": {
        "ru": "Установить PIN",
        "en": "Set PIN",
        "uz": "PIN o‘rnatish",
    },
    "settings.theme": {
        "ru": "Тема",
        "en": "Theme",
        "uz": "Mavzu",
    },
    "settings.theme.dark": {
        "ru": "Тёмная",
        "en": "Dark",
        "uz": "Qorong‘u",
    },
    "settings.theme.light": {
        "ru": "Светлая",
        "en": "Light",
        "uz": "Yorug‘",
    },
    "settings.theme.system": {
        "ru": "Системная",
        "en": "System",
        "uz": "Tizim",
    },
    "subscription.monthly": {
        "ru": "Ежемесячно",
        "en": "Monthly",
        "uz": "Har oy",
    },
    "subscription.next_billing": {
        "ru": "Следующее списание: {date}",
        "en": "Next billing: {date}",
        "uz": "Keyingi yechib olish: {date}",
    },
    "subscription.yearly": {
        "ru": "Ежегодно",
        "en": "Yearly",
        "uz": "Har yil",
    },
    "subscriptions.calendar": {
        "ru": "Календарь списаний",
        "en": "Billing calendar",
        "uz": "To‘lovlar taqvimi",
    },
    "subscriptions.monthly_total": {
        "ru": "В месяц (активные)",
        "en": "Monthly (active)",
        "uz": "Oyiga (faol)",
    },
    "subscriptions.yearly_total": {
        "ru": "В год (активные)",
        "en": "Yearly (active)",
        "uz": "Yiliga (faol)",
    },
    "tags.hint": {
        "ru": "еда, такси",
        "en": "food, taxi",
        "uz": "ovqat, taksi",
    },
    "transaction.expense": {
        "ru": "Расход",
        "en": "Expense",
        "uz": "Xarajat",
    },
    "transaction.income": {
        "ru": "Доход",
        "en": "Income",
        "uz": "Daromad",
    },
}


def normalize_lang(lang: str | None) -> str:
    """Normalize language codes to ``ru`` / ``en`` / ``uz``."""
    if not lang:
        return DEFAULT_LANG
    code = lang.strip().lower().replace("_", "-")
    if code.startswith("ru"):
        return "ru"
    if code.startswith("en"):
        return "en"
    if code.startswith("uz"):
        return "uz"
    logger.debug("Unsupported language %r; falling back to %s", lang, DEFAULT_LANG)
    return DEFAULT_LANG


def t(key: str, lang: str | None = None, *, default: str | None = None) -> str:
    """Translate ``key`` into ``lang``.

    Falls back to English, then Russian, then the key itself (or ``default``).
    """
    code = normalize_lang(lang)
    entry = STRINGS.get(key)
    if entry is None:
        logger.debug("Missing localization key: %s", key)
        return default if default is not None else key
    if code in entry:
        return entry[code]
    if "en" in entry:
        return entry["en"]
    if "ru" in entry:
        return entry["ru"]
    return default if default is not None else key


def available_keys() -> list[str]:
    """Return sorted localization keys."""
    return sorted(STRINGS.keys())


def merge_strings(extra: Mapping[str, Mapping[str, str]]) -> None:
    """Merge additional dictionaries into the global table (in-place)."""
    for key, translations in extra.items():
        bucket = STRINGS.setdefault(key, {})
        for lang, value in translations.items():
            bucket[normalize_lang(lang)] = value


# Default category labels keyed by the Russian seed name.
_CATEGORY_NAME_I18N: dict[str, dict[str, str]] = {
    "Еда": {"en": "Food", "uz": "Ovqat"},
    "Транспорт": {"en": "Transport", "uz": "Transport"},
    "Жильё": {"en": "Housing", "uz": "Uy-joy"},
    "Коммунальные": {"en": "Utilities", "uz": "Kommunal"},
    "Здоровье": {"en": "Health", "uz": "Salomatlik"},
    "Развлечения": {"en": "Entertainment", "uz": "Ko‘ngilochar"},
    "Одежда": {"en": "Clothes", "uz": "Kiyim"},
    "Образование": {"en": "Education", "uz": "Ta’lim"},
    "Зарплата": {"en": "Salary", "uz": "Maosh"},
    "Подарки": {"en": "Gifts", "uz": "Sovg‘alar"},
    "Накопление": {"en": "Savings", "uz": "Jamg‘arma"},
    "Инвестиции": {"en": "Investments", "uz": "Investitsiyalar"},
    "Прочее": {"en": "Other", "uz": "Boshqa"},
}


def localize_category_name(name: str, lang: str | None) -> str:
    """Translate a known default category name into ``lang``."""
    code = normalize_lang(lang)
    if code == "ru":
        return name
    mapped = _CATEGORY_NAME_I18N.get(name)
    if not mapped:
        return name
    return mapped.get(code) or mapped.get("en") or name
