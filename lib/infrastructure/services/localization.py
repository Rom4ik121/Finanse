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
    "account.stats.title": {
        "ru": "Счёт",
        "en": "Account",
        "uz": "Hisob",
    },
    "account.stats.missing": {
        "ru": "Счёт не найден",
        "en": "Account not found",
        "uz": "Hisob topilmadi",
    },
    "account.stats.empty": {
        "ru": "За этот период операций нет",
        "en": "No activity in this period",
        "uz": "Bu davrda operatsiyalar yo‘q",
    },
    "account.stats.count": {
        "ru": "{count} операций",
        "en": "{count} transactions",
        "uz": "{count} ta operatsiya",
    },
    "account.stats.transfer_in": {
        "ru": "Переводы входящие",
        "en": "Transfers in",
        "uz": "Kiruvchi o‘tkazmalar",
    },
    "account.stats.transfer_out": {
        "ru": "Переводы исходящие",
        "en": "Transfers out",
        "uz": "Chiquvchi o‘tkazmalar",
    },
    "account.stats.spend_chart": {
        "ru": "Расходы по категориям",
        "en": "Spending by category",
        "uz": "Turkumlar bo‘yicha xarajat",
    },
    "account.stats.spend_hint": {
        "ru": "Без переводов между счетами",
        "en": "Excluding transfers between accounts",
        "uz": "Hisoblar o‘rtasidagi o‘tkazmalarsiz",
    },
    "account.stats.recent": {
        "ru": "Последние операции",
        "en": "Recent activity",
        "uz": "So‘nggi operatsiyalar",
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
    "action.select": {
        "ru": "Выбрать",
        "en": "Select",
        "uz": "Tanlash",
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
    "category.empty_hint": {
        "ru": "Категорий пока нет — создайте свою первую, она сохранится для быстрого ввода",
        "en": "No categories yet — create your first one; it will be saved for quick entry",
        "uz": "Hali kategoriyalar yo‘q — birinchisini yarating, keyingi amaliyotlar uchun saqlanadi",
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
    "dashboard.dynamics_hint_month": {
        "ru": "Зелёный — доходы, красный — расходы по месяцам",
        "en": "Green — income, red — expenses by month",
        "uz": "Yashil — daromad, qizil — oylik xarajatlar",
    },
    "dashboard.dynamics_hint_week": {
        "ru": "Зелёный — доходы, красный — расходы по неделям",
        "en": "Green — income, red — expenses by week",
        "uz": "Yashil — daromad, qizil — haftalik xarajatlar",
    },
    "dashboard.expense_hint": {
        "ru": "Доли категорий в расходах за {period}",
        "en": "Category share of expenses for {period}",
        "uz": "{period} davrida xarajatlar bo‘yicha kategoriyalar ulushi",
    },
    "dashboard.expense_for_period": {
        "ru": "Расходы · {period}",
        "en": "Expenses · {period}",
        "uz": "Xarajatlar · {period}",
    },
    "dashboard.period.180d": {
        "ru": "6 месяцев",
        "en": "6 months",
        "uz": "6 oy",
    },
    "dashboard.period.30d": {
        "ru": "30 дней",
        "en": "30 days",
        "uz": "30 kun",
    },
    "dashboard.period.365d": {
        "ru": "Год",
        "en": "1 year",
        "uz": "1 yil",
    },
    "dashboard.period.7d": {
        "ru": "7 дней",
        "en": "7 days",
        "uz": "7 kun",
    },
    "dashboard.period.90d": {
        "ru": "3 месяца",
        "en": "3 months",
        "uz": "3 oy",
    },
    "dashboard.period.all": {
        "ru": "Всё время",
        "en": "All time",
        "uz": "Butun davr",
    },
    "dashboard.period_filter": {
        "ru": "Период",
        "en": "Period",
        "uz": "Davr",
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
    "dashboard.month_net": {
        "ru": "Итог за месяц",
        "en": "Month net",
        "uz": "Oy yakuni",
    },
    "dashboard.month_summary": {
        "ru": "Этот месяц",
        "en": "This month",
        "uz": "Shu oy",
    },
    "dashboard.period_expense": {
        "ru": "Расход · {period}",
        "en": "Expense · {period}",
        "uz": "Xarajat · {period}",
    },
    "dashboard.period_income": {
        "ru": "Доход · {period}",
        "en": "Income · {period}",
        "uz": "Daromad · {period}",
    },
    "dashboard.period_net": {
        "ru": "Итог · {period}",
        "en": "Net · {period}",
        "uz": "Yakun · {period}",
    },
    "dashboard.period_summary": {
        "ru": "Сводка · {period}",
        "en": "Summary · {period}",
        "uz": "Xulosa · {period}",
    },
    "dashboard.shortcuts": {
        "ru": "Разделы",
        "en": "Sections",
        "uz": "Bo‘limlar",
    },
    "dashboard.budgets": {
        "ru": "Бюджеты месяца",
        "en": "This month's budgets",
        "uz": "Oy byudjetlari",
    },
    "dashboard.budgets_empty": {
        "ru": "Задайте лимиты по категориям",
        "en": "Set category spending limits",
        "uz": "Kategoriyalar uchun limit belgilang",
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
    "debt.status.overdue": {
        "ru": "Просрочен",
        "en": "Overdue",
        "uz": "Muddati o‘tgan",
    },
    "debt.status.paid": {
        "ru": "Погашен",
        "en": "Paid",
        "uz": "To‘langan",
    },
    "debt.status.archived": {
        "ru": "В архиве",
        "en": "Archived",
        "uz": "Arxivda",
    },
    "debt.filter.active": {
        "ru": "Активные",
        "en": "Active",
        "uz": "Faol",
    },
    "debt.filter.overdue": {
        "ru": "Просроченные",
        "en": "Overdue",
        "uz": "Muddati o‘tgan",
    },
    "debt.filter.paid": {
        "ru": "Погашенные",
        "en": "Paid",
        "uz": "To‘langan",
    },
    "debt.filter.archived": {
        "ru": "Архив",
        "en": "Archived",
        "uz": "Arxiv",
    },
    "debt.filter_status": {
        "ru": "Статус",
        "en": "Status",
        "uz": "Holat",
    },
    "debt.filter_direction": {
        "ru": "Направление",
        "en": "Direction",
        "uz": "Yo‘nalish",
    },
    "debt.filter_sort": {
        "ru": "Сортировка",
        "en": "Sort",
        "uz": "Saralash",
    },
    "debt.filter_all_directions": {
        "ru": "Все направления",
        "en": "All directions",
        "uz": "Barcha yo‘nalishlar",
    },
    "debt.sort.due_date": {
        "ru": "По дедлайну",
        "en": "By due date",
        "uz": "Muddat bo‘yicha",
    },
    "debt.sort.remaining": {
        "ru": "По остатку",
        "en": "By remaining",
        "uz": "Qoldiq bo‘yicha",
    },
    "debt.sort.amount": {
        "ru": "По сумме",
        "en": "By amount",
        "uz": "Summa bo‘yicha",
    },
    "debt.sort.interest": {
        "ru": "По проценту",
        "en": "By interest",
        "uz": "Foiz bo‘yicha",
    },
    "debt.sort.created_at": {
        "ru": "По дате создания",
        "en": "By created date",
        "uz": "Yaratilgan sana bo‘yicha",
    },
    "debt.sort.counterparty": {
        "ru": "По контрагенту",
        "en": "By counterparty",
        "uz": "Kontragent bo‘yicha",
    },
    "debt.sort.status": {
        "ru": "По статусу",
        "en": "By status",
        "uz": "Holat bo‘yicha",
    },
    "debt.archive": {
        "ru": "Архивировать",
        "en": "Archive",
        "uz": "Arxivlash",
    },
    "debt.projection": {
        "ru": "Прогноз погашения",
        "en": "Payoff projection",
        "uz": "To‘lash prognozi",
    },
    "debt.recommended_monthly": {
        "ru": "Рекомендуемый платёж в месяц",
        "en": "Recommended monthly payment",
        "uz": "Tavsiya etilgan oylik to‘lov",
    },
    "debt.projected_date": {
        "ru": "Прогноз полного погашения",
        "en": "Projected payoff date",
        "uz": "To‘liq to‘lash prognozi",
    },
    "debt.on_track": {
        "ru": "В графике",
        "en": "On track",
        "uz": "Jadvalda",
    },
    "debt.off_track": {
        "ru": "Отстаёт от графика",
        "en": "Behind schedule",
        "uz": "Jadvaldan orqada",
    },
    "debt.payments": {
        "ru": "История платежей",
        "en": "Payment history",
        "uz": "To‘lovlar tarixi",
    },
    "debt.payment_type": {
        "ru": "Погашение",
        "en": "Repayment",
        "uz": "To‘lov",
    },
    "debt.converted_amount": {
        "ru": "В валюте долга: {amount}",
        "en": "In debt currency: {amount}",
        "uz": "Qarz valyutasida: {amount}",
    },
    "debt.no_rate": {
        "ru": "Нет курса для {pair}. Погашение невозможно.",
        "en": "No rate for {pair}. Repayment blocked.",
        "uz": "{pair} kursi yo‘q. To‘lov mumkin emas.",
    },
    "debt.principal_amount": {
        "ru": "В счёт основного долга",
        "en": "Toward principal",
        "uz": "Asosiy qarz hisobiga",
    },
    "debt.interest_amount": {
        "ru": "В счёт процентов",
        "en": "Toward interest",
        "uz": "Foiz hisobiga",
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
    "empty.budgets": {
        "ru": "Нет бюджетов на этот месяц",
        "en": "No budgets for this month",
        "uz": "Bu oy uchun byudjetlar yo‘q",
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
    "error.currency_mismatch": {
        "ru": "Нужен счёт в валюте {currency}",
        "en": "Need an account in {currency}",
        "uz": "{currency} valyutasidagi hisob kerak",
    },
    "action.load_more": {
        "ru": "Показать ещё",
        "en": "Load more",
        "uz": "Yana ko‘rsatish",
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
    "goal.currency": {
        "ru": "Валюта цели",
        "en": "Goal currency",
        "uz": "Maqsad valyutasi",
    },
    "goal.copy_suffix": {
        "ru": " (копия)",
        "en": " (copy)",
        "uz": " (nusxa)",
    },
    "goal.archive": {
        "ru": "Архивировать",
        "en": "Archive",
        "uz": "Arxivlash",
    },
    "goal.duplicate": {
        "ru": "Создать похожую",
        "en": "Create similar",
        "uz": "O‘xshashini yaratish",
    },
    "goal.status.active": {
        "ru": "Активные",
        "en": "Active",
        "uz": "Faol",
    },
    "goal.status.completed": {
        "ru": "Завершённые",
        "en": "Completed",
        "uz": "Tugallangan",
    },
    "goal.status.archived": {
        "ru": "Архив",
        "en": "Archived",
        "uz": "Arxiv",
    },
    "goal.deadline_by": {
        "ru": "до {date}",
        "en": "by {date}",
        "uz": "{date} gacha",
    },
    "goal.no_deadline": {
        "ru": "Без срока",
        "en": "No deadline",
        "uz": "Muddat yo‘q",
    },
    "goal.badge.active": {
        "ru": "Активна",
        "en": "Active",
        "uz": "Faol",
    },
    "goal.badge.completed": {
        "ru": "Завершена",
        "en": "Completed",
        "uz": "Tugallangan",
    },
    "goal.badge.archived": {
        "ru": "В архиве",
        "en": "Archived",
        "uz": "Arxivda",
    },
    "goal.filter_status": {
        "ru": "Статус",
        "en": "Status",
        "uz": "Holat",
    },
    "goal.filter_sort": {
        "ru": "Сортировка",
        "en": "Sort",
        "uz": "Saralash",
    },
    "goal.sort.priority": {
        "ru": "По приоритету",
        "en": "By priority",
        "uz": "Muhimlik bo‘yicha",
    },
    "goal.sort.deadline": {
        "ru": "По дедлайну",
        "en": "By deadline",
        "uz": "Muddat bo‘yicha",
    },
    "goal.sort.progress": {
        "ru": "По прогрессу",
        "en": "By progress",
        "uz": "Jarayon bo‘yicha",
    },
    "goal.sort.created_at": {
        "ru": "По дате создания",
        "en": "By created date",
        "uz": "Yaratilgan sana bo‘yicha",
    },
    "goal.group_by_category": {
        "ru": "Группировать по категориям",
        "en": "Group by category",
        "uz": "Kategoriya bo‘yicha guruhlash",
    },
    "goal.uncategorized": {
        "ru": "Без категории",
        "en": "Uncategorized",
        "uz": "Kategoriyasiz",
    },
    "goal.projection": {
        "ru": "Прогноз",
        "en": "Projection",
        "uz": "Prognoz",
    },
    "goal.required_monthly": {
        "ru": "Нужно в месяц",
        "en": "Required monthly",
        "uz": "Oyiga kerak",
    },
    "goal.projected_date": {
        "ru": "Прогноз завершения",
        "en": "Projected completion",
        "uz": "Tugash prognozi",
    },
    "goal.on_track": {
        "ru": "В графике",
        "en": "On track",
        "uz": "Jadvalda",
    },
    "goal.off_track": {
        "ru": "Отстаёт от графика",
        "en": "Behind schedule",
        "uz": "Jadvaldan orqada",
    },
    "goal.contributions": {
        "ru": "История взносов",
        "en": "Contribution history",
        "uz": "Badallar tarixi",
    },
    "goal.converted_amount": {
        "ru": "В валюте цели: {amount}",
        "en": "In goal currency: {amount}",
        "uz": "Maqsad valyutasida: {amount}",
    },
    "goal.no_rate": {
        "ru": "Нет курса для {pair}. Взнос невозможен.",
        "en": "No rate for {pair}. Contribution blocked.",
        "uz": "{pair} kursi yo‘q. Badal mumkin emas.",
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
    "icon_group.beauty": {
        "ru": "Красота",
        "en": "Beauty",
        "uz": "Go‘zallik",
    },
    "icon_group.bills": {
        "ru": "Счета",
        "en": "Bills",
        "uz": "To‘lovlar",
    },
    "icon_group.education": {
        "ru": "Образование",
        "en": "Education",
        "uz": "Ta’lim",
    },
    "icon_group.family": {
        "ru": "Семья, дети",
        "en": "Family & kids",
        "uz": "Oila va bolalar",
    },
    "icon_group.farm": {
        "ru": "Ферма",
        "en": "Farm",
        "uz": "Fermerlik",
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
        "ru": "Дом",
        "en": "Home",
        "uz": "Uy",
    },
    "icon_group.leisure": {
        "ru": "Отдых",
        "en": "Leisure",
        "uz": "Dam olish",
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
    "icon_group.sport": {
        "ru": "Спорт",
        "en": "Sport",
        "uz": "Sport",
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
        "ru": "Работа",
        "en": "Work",
        "uz": "Ish",
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
    "nav.analytics": {
        "ru": "Аналитика",
        "en": "Analytics",
        "uz": "Tahlil",
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
    "nav.budgets": {
        "ru": "Бюджеты",
        "en": "Budgets",
        "uz": "Byudjetlar",
    },
    "budgets.title": {
        "ru": "Бюджеты",
        "en": "Budgets",
        "uz": "Byudjetlar",
    },
    "budgets.add": {
        "ru": "Добавить бюджет",
        "en": "Add budget",
        "uz": "Byudjet qo‘shish",
    },
    "budgets.edit": {
        "ru": "Редактировать",
        "en": "Edit",
        "uz": "Tahrirlash",
    },
    "budgets.delete": {
        "ru": "Удалить",
        "en": "Delete",
        "uz": "O‘chirish",
    },
    "budgets.delete_confirm": {
        "ru": "Удалить бюджет категории «{category}»?",
        "en": "Delete the budget for \"{category}\"?",
        "uz": "\"{category}\" byudjetini o‘chirasizmi?",
    },
    "budgets.deleted": {
        "ru": "Бюджет удалён",
        "en": "Budget deleted",
        "uz": "Byudjet o‘chirildi",
    },
    "budgets.saved": {
        "ru": "Бюджет сохранён",
        "en": "Budget saved",
        "uz": "Byudjet saqlandi",
    },
    "budgets.limit": {
        "ru": "Лимит",
        "en": "Limit",
        "uz": "Limit",
    },
    "budgets.spent": {
        "ru": "Потрачено",
        "en": "Spent",
        "uz": "Sarflandi",
    },
    "budgets.total_limit": {
        "ru": "Всего лимит",
        "en": "Total limit",
        "uz": "Jami limit",
    },
    "budgets.total_spent": {
        "ru": "Всего потрачено",
        "en": "Total spent",
        "uz": "Jami sarflandi",
    },
    "budgets.remaining": {
        "ru": "Осталось",
        "en": "Remaining",
        "uz": "Qoldi",
    },
    "budgets.percent": {
        "ru": "Использовано",
        "en": "Used",
        "uz": "Ishlatildi",
    },
    "budgets.over_budget": {
        "ru": "Превышение",
        "en": "Over budget",
        "uz": "Limitdan oshdi",
    },
    "budgets.no_budgets": {
        "ru": "Нет бюджетов на этот месяц",
        "en": "No budgets for this month",
        "uz": "Bu oy uchun byudjetlar yo‘q",
    },
    "budgets.category_required": {
        "ru": "Выберите категорию",
        "en": "Choose a category",
        "uz": "Kategoriyani tanlang",
    },
    "budgets.limit_required": {
        "ru": "Введите лимит",
        "en": "Enter a limit",
        "uz": "Limitni kiriting",
    },
    "budgets.month": {
        "ru": "Месяц",
        "en": "Month",
        "uz": "Oy",
    },
    "budgets.year": {
        "ru": "Год",
        "en": "Year",
        "uz": "Yil",
    },
    "budgets.month.1": {"ru": "Январь", "en": "January", "uz": "Yanvar"},
    "budgets.month.2": {"ru": "Февраль", "en": "February", "uz": "Fevral"},
    "budgets.month.3": {"ru": "Март", "en": "March", "uz": "Mart"},
    "budgets.month.4": {"ru": "Апрель", "en": "April", "uz": "Aprel"},
    "budgets.month.5": {"ru": "Май", "en": "May", "uz": "May"},
    "budgets.month.6": {"ru": "Июнь", "en": "June", "uz": "Iyun"},
    "budgets.month.7": {"ru": "Июль", "en": "July", "uz": "Iyul"},
    "budgets.month.8": {"ru": "Август", "en": "August", "uz": "Avgust"},
    "budgets.month.9": {"ru": "Сентябрь", "en": "September", "uz": "Sentabr"},
    "budgets.month.10": {"ru": "Октябрь", "en": "October", "uz": "Oktabr"},
    "budgets.month.11": {"ru": "Ноябрь", "en": "November", "uz": "Noyabr"},
    "budgets.month.12": {"ru": "Декабрь", "en": "December", "uz": "Dekabr"},
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
    "notify.debt_overdue_title": {
        "ru": "Долг просрочен",
        "en": "Debt overdue",
        "uz": "Qarz muddati o‘tgan",
    },
    "notify.debt_overdue_body": {
        "ru": "Долг \"{name}\" просрочен. Остаток: {amount}",
        "en": "Debt \"{name}\" is overdue. Remaining: {amount}",
        "uz": "\"{name}\" qarzi muddati o‘tgan. Qoldiq: {amount}",
    },
    "notify.debt_idle_title": {
        "ru": "Нет платежей по долгу",
        "en": "No debt payments lately",
        "uz": "Qarz bo‘yicha to‘lov yo‘q",
    },
    "notify.debt_idle_body": {
        "ru": "По долгу \"{name}\" не было платежей более 30 дней",
        "en": "No payments on debt \"{name}\" for over 30 days",
        "uz": "\"{name}\" qarzi bo‘yicha 30 kundan ortiq to‘lov yo‘q",
    },
    "notify.goal_reached": {
        "ru": "Цель достигнута!",
        "en": "Goal reached!",
        "uz": "Maqsadga erishildi!",
    },
    "notify.goal_off_track_title": {
        "ru": "Цель отстаёт от графика",
        "en": "Goal behind schedule",
        "uz": "Maqsad jadvaldan orqada",
    },
    "notify.goal_off_track_body": {
        "ru": "Цель \"{name}\" отстаёт от графика. Требуется вносить по {amount} в месяц",
        "en": "Goal \"{name}\" is behind schedule. Contribute about {amount} per month",
        "uz": "\"{name}\" maqsadi jadvaldan orqada. Oyiga taxminan {amount} kerak",
    },
    "notify.budget_80_title": {
        "ru": "Бюджет почти исчерпан",
        "en": "Budget nearly used up",
        "uz": "Byudjet deyarli tugadi",
    },
    "notify.budget_100_title": {
        "ru": "Бюджет превышен",
        "en": "Budget exceeded",
        "uz": "Byudjet oshib ketdi",
    },
    "notifications.budget_80": {
        "ru": "Бюджет категории {category} израсходован на 80%. Осталось: {remaining} {currency}",
        "en": "Budget for \"{category}\" is 80% used. Remaining: {remaining} {currency}",
        "uz": "\"{category}\" byudjeti 80% ishlatildi. Qoldi: {remaining} {currency}",
    },
    "notifications.budget_100": {
        "ru": "Бюджет категории {category} превышен! Потрачено: {spent} из {limit} {currency}",
        "en": "Budget for \"{category}\" exceeded! Spent {spent} of {limit} {currency}",
        "uz": "\"{category}\" byudjeti oshib ketdi! Sarflandi: {spent} / {limit} {currency}",
    },
    "notify.subscription_due": {
        "ru": "Скоро списание подписки",
        "en": "Subscription billing soon",
        "uz": "Obuna yechib olish yaqinlashmoqda",
    },
    "notify.subscription_due_body": {
        "ru": "Подписка \"{name}\" будет списана {amount} {currency} со счёта \"{account}\" через {days} дн.",
        "en": "Subscription \"{name}\" will charge {amount} {currency} from \"{account}\" in {days} day(s).",
        "uz": "\"{name}\" obunasi \"{account}\" hisobidan {amount} {currency} {days} kundan keyin yechib olinadi.",
    },
    "notify.subscription_insufficient": {
        "ru": "На счету недостаточно средств!",
        "en": "Insufficient account balance!",
        "uz": "Hisobda mablag‘ yetarli emas!",
    },
    "notify.subscription_skipped": {
        "ru": "Подписка не списана",
        "en": "Subscription charge skipped",
        "uz": "Obuna yechilmadi",
    },
    "notify.subscription_skipped_body": {
        "ru": "Недостаточно средств для подписки \"{name}\" ({amount} {currency}) на счёте \"{account}\".",
        "en": "Insufficient funds for \"{name}\" ({amount} {currency}) on account \"{account}\".",
        "uz": "\"{name}\" ({amount} {currency}) uchun \"{account}\" hisobida mablag‘ yetarli emas.",
    },
    "notify.subscription_expired": {
        "ru": "Подписка завершена",
        "en": "Subscription expired",
        "uz": "Obuna tugadi",
    },
    "notify.subscription_expired_body": {
        "ru": "Подписка \"{name}\" истекла (дата окончания или лимит платежей).",
        "en": "Subscription \"{name}\" expired (end date or payment limit).",
        "uz": "\"{name}\" obunasi tugadi (tugash sanasi yoki to‘lov limiti).",
    },
    "picker.choose_color": {
        "ru": "Выбрать цвет",
        "en": "Choose color",
        "uz": "Rangni tanlash",
    },
    "picker.color_title": {
        "ru": "Выбор цвета",
        "en": "Choose color",
        "uz": "Rang tanlash",
    },
    "picker.choose_icon": {
        "ru": "Выбрать иконку",
        "en": "Choose icon",
        "uz": "Belgini tanlash",
    },
    "picker.icon_catalog": {
        "ru": "Каталог иконок",
        "en": "Icon catalog",
        "uz": "Belgilar katalogi",
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
    "settings.budget_alerts": {
        "ru": "Уведомления о бюджетах",
        "en": "Budget alerts",
        "uz": "Byudjet bildirishnomalari",
    },
    "settings.debt_reminders": {
        "ru": "Напоминания о долгах",
        "en": "Debt reminders",
        "uz": "Qarz eslatmalari",
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
    "settings.subscription_reminders": {
        "ru": "Напоминания о подписках",
        "en": "Subscription reminders",
        "uz": "Obuna eslatmalari",
    },
    "settings.reminder_days": {
        "ru": "Напоминать о подписках за N дней",
        "en": "Remind about subscriptions N days ahead",
        "uz": "Obunalar haqida N kun oldin eslatish",
    },
    "settings.check_balance_before_subscription": {
        "ru": "Проверять баланс перед списанием подписки",
        "en": "Check balance before subscription charge",
        "uz": "Obunani yechishdan oldin balansni tekshirish",
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
    "subscription.daily": {
        "ru": "Ежедневно",
        "en": "Daily",
        "uz": "Har kuni",
    },
    "subscription.weekly": {
        "ru": "Еженедельно",
        "en": "Weekly",
        "uz": "Har hafta",
    },
    "subscription.biweekly": {
        "ru": "Раз в 2 недели",
        "en": "Biweekly",
        "uz": "2 haftada bir",
    },
    "subscription.quarterly": {
        "ru": "Ежеквартально",
        "en": "Quarterly",
        "uz": "Har chorak",
    },
    "subscription.semi_annual": {
        "ru": "Раз в полгода",
        "en": "Semi-annual",
        "uz": "Yarim yilda bir",
    },
    "subscription.custom": {
        "ru": "Свой интервал",
        "en": "Custom interval",
        "uz": "Maxsus interval",
    },
    "subscription.custom_interval": {
        "ru": "Интервал (дней)",
        "en": "Interval (days)",
        "uz": "Interval (kun)",
    },
    "subscription.start_date": {
        "ru": "Дата начала",
        "en": "Start date",
        "uz": "Boshlanish sanasi",
    },
    "subscription.end_date": {
        "ru": "Дата окончания",
        "en": "End date",
        "uz": "Tugash sanasi",
    },
    "subscription.max_payments": {
        "ru": "Макс. платежей",
        "en": "Max payments",
        "uz": "Maks. to‘lovlar",
    },
    "subscription.status.active": {
        "ru": "Активна",
        "en": "Active",
        "uz": "Faol",
    },
    "subscription.status.paused": {
        "ru": "На паузе",
        "en": "Paused",
        "uz": "Pauzada",
    },
    "subscription.status.expired": {
        "ru": "Истекла",
        "en": "Expired",
        "uz": "Tugagan",
    },
    "subscription.status.cancelled": {
        "ru": "Отменена",
        "en": "Cancelled",
        "uz": "Bekor qilingan",
    },
    "subscription.pause": {
        "ru": "Приостановить",
        "en": "Pause",
        "uz": "Pauza",
    },
    "subscription.resume": {
        "ru": "Возобновить",
        "en": "Resume",
        "uz": "Davom ettirish",
    },
    "subscription.charge_now": {
        "ru": "Списать сейчас",
        "en": "Charge now",
        "uz": "Hozir yechib olish",
    },
    "subscription.auto_charge": {
        "ru": "Автосписание",
        "en": "Auto-charge",
        "uz": "Avto-yechib olish",
    },
    "subscription.auto_charge_off": {
        "ru": "без автосписания",
        "en": "manual only",
        "uz": "qo‘lda",
    },
    "subscription.charge_history": {
        "ru": "История списаний",
        "en": "Charge history",
        "uz": "Yechib olish tarixi",
    },
    "subscription.delete_charge_hint": {
        "ru": "Списание будет удалено без пересчёта следующей даты.",
        "en": "The charge will be deleted without recalculating the next billing date.",
        "uz": "To‘lov keyingi sana qayta hisoblanmasdan o‘chiriladi.",
    },
    "subscription.insufficient_funds": {
        "ru": "Недостаточно средств на счёте",
        "en": "Insufficient account balance",
        "uz": "Hisobda mablag‘ yetarli emas",
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
    "analytics.tab.spend": {
        "ru": "Расходы",
        "en": "Spending",
        "uz": "Xarajat",
    },
    "analytics.tab.trend": {
        "ru": "График",
        "en": "Trend",
        "uz": "Grafik",
    },
    "analytics.tab.more": {
        "ru": "Ещё",
        "en": "More",
        "uz": "Yana",
    },
    "analytics.income": {
        "ru": "Доход",
        "en": "Income",
        "uz": "Daromad",
    },
    "analytics.expense": {
        "ru": "Расход",
        "en": "Expense",
        "uz": "Xarajat",
    },
    "analytics.net": {
        "ru": "Чистое",
        "en": "Net",
        "uz": "Sof",
    },
    "analytics.balance": {
        "ru": "Все счета",
        "en": "All accounts",
        "uz": "Barcha hisoblar",
    },
    "analytics.savings": {
        "ru": "Сбережения",
        "en": "Saved",
        "uz": "Jamg‘arma",
    },
    "analytics.avg_day": {
        "ru": "В день",
        "en": "Per day",
        "uz": "Kuniga",
    },
    "analytics.ops": {
        "ru": "Операций",
        "en": "Operations",
        "uz": "Operatsiyalar",
    },
    "analytics.no_subs": {
        "ru": "Нет данных по подпискам",
        "en": "No subscription data",
        "uz": "Obunalar bo‘yicha ma’lumot yo‘q",
    },
    "analytics.subscriptions": {
        "ru": "Подписки",
        "en": "Subscriptions",
        "uz": "Obunalar",
    },
    "analytics.subscriptions_spent": {
        "ru": "Потрачено на подписки",
        "en": "Spent on subscriptions",
        "uz": "Obunalarga sarflangan",
    },
    "analytics.subscriptions_monthly_cost": {
        "ru": "Стоимость в месяц",
        "en": "Monthly cost",
        "uz": "Oyiga narx",
    },
    "analytics.subscriptions_active": {
        "ru": "Активных подписок",
        "en": "Active subscriptions",
        "uz": "Faol obunalar",
    },
    "analytics.subscriptions_top": {
        "ru": "Топ подписок",
        "en": "Top subscriptions",
        "uz": "Eng ko‘p obunalar",
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
    "transaction.transfer": {
        "ru": "Перевод",
        "en": "Transfer",
        "uz": "O‘tkazma",
    },
    "transfers.title": {
        "ru": "Перевод между счетами",
        "en": "Transfer between accounts",
        "uz": "Hisoblar o‘rtasida o‘tkazma",
    },
    "transfer.from": {
        "ru": "Откуда",
        "en": "From",
        "uz": "Qayerdan",
    },
    "transfer.to": {
        "ru": "Куда",
        "en": "To",
        "uz": "Qayerga",
    },
    "transfer.same_account": {
        "ru": "Выберите разные счета",
        "en": "Choose two different accounts",
        "uz": "Ikkita turli hisob tanlang",
    },
    "transfer.need_two_accounts": {
        "ru": "Нужны минимум два активных счёта",
        "en": "You need at least two active accounts",
        "uz": "Kamida ikkita faol hisob kerak",
    },
    "transfer.insufficient": {
        "ru": "Недостаточно средств на счёте списания",
        "en": "Insufficient funds on the source account",
        "uz": "Manba hisobida mablag‘ yetarli emas",
    },
    "transfer.no_rate": {
        "ru": "Нет курса для этой пары валют",
        "en": "No exchange rate for this currency pair",
        "uz": "Bu valyuta juftligi uchun kurs yo‘q",
    },
    "transfer.will_credit": {
        "ru": "Зачислится {amount} на «{account}»",
        "en": "{amount} will be credited to “{account}”",
        "uz": "«{account}» hisobiga {amount} tushadi",
    },
    "transfer.edit_hint": {
        "ru": "Сумму и счета перевода менять нельзя — только комментарий. Удаление снимает обе стороны.",
        "en": "Transfer amount and accounts cannot be changed — only the comment. Deleting removes both legs.",
        "uz": "O‘tkazma summasini va hisoblarni o‘zgartirib bo‘lmaydi — faqat izoh. O‘chirish ikkala tomonni ham olib tashlaydi.",
    },
    "transfer.delete_pair": {
        "ru": "Будут удалены обе стороны перевода",
        "en": "Both sides of the transfer will be deleted",
        "uz": "O‘tkazmaning ikkala tomoni o‘chiriladi",
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
    "Долг": {"en": "Debt", "uz": "Qarz"},
    "Перевод": {"en": "Transfer", "uz": "O‘tkazma"},
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
