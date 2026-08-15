"""Abstract repository interfaces."""

from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.base import Repository
from lib.domain.repositories.budget_repository import BudgetRepository
from lib.domain.repositories.currency_repository import CurrencyRepository
from lib.domain.repositories.debt_repository import DebtRepository
from lib.domain.repositories.goal_repository import GoalRepository
from lib.domain.repositories.settings_repository import SettingsRepository
from lib.domain.repositories.subscription_repository import SubscriptionRepository
from lib.domain.repositories.transaction_repository import TransactionRepository

__all__ = [
    "Repository",
    "AccountRepository",
    "BudgetRepository",
    "CurrencyRepository",
    "DebtRepository",
    "GoalRepository",
    "SettingsRepository",
    "SubscriptionRepository",
    "TransactionRepository",
]
