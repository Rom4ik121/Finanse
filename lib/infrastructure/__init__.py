"""Infrastructure layer: ORM models, repositories, API clients, and services."""

from __future__ import annotations

__all__ = [
    "AccountModel",
    "CurrencyModel",
    "DebtModel",
    "ExchangeRateModel",
    "GoalModel",
    "SettingsModel",
    "SubscriptionModel",
    "TransactionModel",
    "SqlAlchemyAccountRepository",
    "SqlAlchemyCurrencyRepository",
    "SqlAlchemyDebtRepository",
    "SqlAlchemyGoalRepository",
    "SqlAlchemySettingsRepository",
    "SqlAlchemySubscriptionRepository",
    "SqlAlchemyTransactionRepository",
    "CryptoRateClient",
    "ExchangeRateClient",
    "BackupService",
    "EncryptionService",
    "ExportService",
    "NotificationService",
    "t",
]


def __getattr__(name: str):
    """Lazy attribute access to avoid circular imports at package load time."""
    if name.endswith("Model") or name in {
        "AccountModel",
        "CurrencyModel",
        "DebtModel",
        "ExchangeRateModel",
        "GoalModel",
        "SettingsModel",
        "SubscriptionModel",
        "TransactionModel",
    }:
        from lib.infrastructure import db_models

        return getattr(db_models, name)

    if name.startswith("SqlAlchemy"):
        from lib.infrastructure import repositories

        return getattr(repositories, name)

    if name in {"CryptoRateClient", "ExchangeRateClient"}:
        from lib.infrastructure import api

        return getattr(api, name)

    if name in {
        "BackupService",
        "EncryptionService",
        "ExportService",
        "NotificationService",
        "t",
    }:
        from lib.infrastructure import services

        return getattr(services, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
