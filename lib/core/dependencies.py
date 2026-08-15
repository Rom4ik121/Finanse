"""Simple dependency-injection container and factory.

``build_container`` wires infrastructure repositories (when available) to
domain use cases. Missing modules are recorded so a partial build remains
usable during incremental development.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from lib.core.config import AppConfig, get_default_config
from lib.core.database import get_session_factory, init_db

logger = logging.getLogger("finanse.dependencies")


@dataclass
class Container:
    """Holds config, repositories, services, and use-case instances.

    Attributes that could not be constructed during a partial build remain
    ``None``. Check :attr:`missing` / :attr:`errors` for diagnostics.
    """

    config: AppConfig

    # Repositories
    transaction_repository: Any = None
    account_repository: Any = None
    goal_repository: Any = None
    debt_repository: Any = None
    subscription_repository: Any = None
    currency_repository: Any = None
    category_repository: Any = None
    settings_repository: Any = None

    # Optional infrastructure services
    exchange_rate_provider: Any = None
    notification_service: Any = None
    backup_service: Any = None
    export_service: Any = None
    encryption_service: Any = None

    # Use cases — transactions
    add_transaction: Any = None
    update_transaction: Any = None
    delete_transaction: Any = None
    list_transactions: Any = None
    get_transaction_stats: Any = None

    # Use cases — accounts
    create_account: Any = None
    update_account: Any = None
    delete_account: Any = None
    list_accounts: Any = None
    recalculate_account_balance: Any = None

    # Use cases — goals
    create_goal: Any = None
    update_goal: Any = None
    delete_goal: Any = None
    list_goals: Any = None
    contribute_to_goal: Any = None
    get_goal_projection: Any = None
    archive_goal: Any = None
    duplicate_goal: Any = None
    delete_goal_contribution: Any = None

    # Use cases — debts
    create_debt: Any = None
    update_debt: Any = None
    delete_debt: Any = None
    list_debts: Any = None
    repay_debt: Any = None
    calculate_debt_interest: Any = None
    get_debt_projection: Any = None
    archive_debt: Any = None
    delete_debt_payment: Any = None
    mark_overdue_debts: Any = None

    # Use cases — subscriptions
    create_subscription: Any = None
    update_subscription: Any = None
    delete_subscription: Any = None
    list_subscriptions: Any = None
    process_due_subscriptions: Any = None
    pause_subscription: Any = None
    resume_subscription: Any = None
    charge_subscription_now: Any = None
    delete_subscription_charge: Any = None
    get_subscription_analytics: Any = None

    # Use cases — currencies / settings / export / categories
    update_exchange_rates: Any = None
    convert_currency: Any = None
    list_currencies: Any = None
    get_settings: Any = None
    update_settings: Any = None
    export_data: Any = None
    list_categories: Any = None
    create_category: Any = None
    update_category: Any = None
    delete_category: Any = None
    find_or_create_category: Any = None

    missing: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    def require(self, name: str) -> Any:
        """Return a wired dependency or raise if it was not built."""
        value = getattr(self, name, None)
        if value is None:
            detail = self.errors.get(name, "not constructed")
            raise RuntimeError(f"Dependency '{name}' is unavailable: {detail}")
        return value

    def rebind_session_factory(self, session_factory: Any) -> None:
        """Point every SQLAlchemy repository at a fresh session factory.

        Used after ``reset_engine()`` + DB restore so open repos do not keep
        a disposed engine.
        """
        for attr in (
            "transaction_repository",
            "account_repository",
            "goal_repository",
            "debt_repository",
            "subscription_repository",
            "currency_repository",
            "category_repository",
            "settings_repository",
        ):
            repo = getattr(self, attr, None)
            if repo is not None and hasattr(repo, "_session_factory"):
                repo._session_factory = session_factory


def _try_import(module_path: str, attr: str) -> tuple[Optional[type], Optional[str]]:
    """Import ``attr`` from ``module_path``.

    Returns:
        ``(class_or_none, error_message_or_none)``.
    """
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        return None, f"import failed: {exc}"
    try:
        return getattr(module, attr), None
    except AttributeError as exc:
        return None, f"attribute missing: {exc}"


def _construct(
    container: Container,
    attr_name: str,
    module_path: str,
    class_name: str,
    *ctor_args: Any,
    **ctor_kwargs: Any,
) -> None:
    """Instantiate a class into ``container`` or record why it failed."""
    cls, err = _try_import(module_path, class_name)
    if cls is None:
        container.missing.append(attr_name)
        container.errors[attr_name] = err or "unknown import error"
        logger.debug("Skip %s: %s", attr_name, container.errors[attr_name])
        return
    try:
        setattr(container, attr_name, cls(*ctor_args, **ctor_kwargs))
    except Exception as exc:  # pragma: no cover - defensive
        container.missing.append(attr_name)
        container.errors[attr_name] = f"construct failed: {exc}"
        logger.warning("Failed to construct %s: %s", attr_name, exc)


def build_container(
    config: Optional[AppConfig] = None,
    *,
    init_database: bool = True,
) -> Container:
    """Build a :class:`Container` with repositories and use cases.

    Infrastructure repository implementations are expected at:

    * ``lib.infrastructure.repositories.transaction_repository.SqlAlchemyTransactionRepository``
    * ``lib.infrastructure.repositories.account_repository.SqlAlchemyAccountRepository``
    * ``lib.infrastructure.repositories.goal_repository.SqlAlchemyGoalRepository``
    * ``lib.infrastructure.repositories.debt_repository.SqlAlchemyDebtRepository``
    * ``lib.infrastructure.repositories.subscription_repository.SqlAlchemySubscriptionRepository``
    * ``lib.infrastructure.repositories.currency_repository.SqlAlchemyCurrencyRepository``
    * ``lib.infrastructure.repositories.settings_repository.SqlAlchemySettingsRepository``

    Optional service:

    * ``lib.infrastructure.services.exchange_rate_provider.HttpExchangeRateProvider``

    When a module is missing, the corresponding slot stays ``None`` and the
    name is listed in :attr:`Container.missing`.
    """
    cfg = config or get_default_config()
    cfg.ensure_directories()
    container = Container(config=cfg)

    if init_database:
        try:
            init_db(cfg)
        except Exception as exc:
            container.errors["database"] = str(exc)
            logger.warning("init_db failed: %s", exc)

    session_factory = get_session_factory(cfg)

    # --- Repositories (infrastructure) ---------------------------------
    repo_specs = [
        (
            "transaction_repository",
            "lib.infrastructure.repositories.transaction_repository",
            "SqlAlchemyTransactionRepository",
        ),
        (
            "account_repository",
            "lib.infrastructure.repositories.account_repository",
            "SqlAlchemyAccountRepository",
        ),
        (
            "goal_repository",
            "lib.infrastructure.repositories.goal_repository",
            "SqlAlchemyGoalRepository",
        ),
        (
            "debt_repository",
            "lib.infrastructure.repositories.debt_repository",
            "SqlAlchemyDebtRepository",
        ),
        (
            "subscription_repository",
            "lib.infrastructure.repositories.subscription_repository",
            "SqlAlchemySubscriptionRepository",
        ),
        (
            "currency_repository",
            "lib.infrastructure.repositories.currency_repository",
            "SqlAlchemyCurrencyRepository",
        ),
        (
            "settings_repository",
            "lib.infrastructure.repositories.settings_repository",
            "SqlAlchemySettingsRepository",
        ),
        (
            "category_repository",
            "lib.infrastructure.repositories.category_repository",
            "SqlAlchemyCategoryRepository",
        ),
    ]
    for attr, module_path, class_name in repo_specs:
        _construct(container, attr, module_path, class_name, session_factory)

    _construct(
        container,
        "exchange_rate_provider",
        "lib.infrastructure.services.exchange_rate_provider",
        "HttpExchangeRateProvider",
        api_key=cfg.exchange_rate_api_key,
    )
    _construct(
        container,
        "notification_service",
        "lib.infrastructure.services.notification_service",
        "NotificationService",
    )
    _construct(
        container,
        "backup_service",
        "lib.infrastructure.services.backup_service",
        "BackupService",
        cfg,
    )
    _construct(
        container,
        "export_service",
        "lib.infrastructure.services.export_service",
        "ExportService",
        cfg,
    )
    _construct(
        container,
        "encryption_service",
        "lib.infrastructure.services.encryption_service",
        "EncryptionService",
    )

    # --- Use cases (domain) --------------------------------------------
    from lib.domain.use_cases.accounts import (
        CreateAccountUseCase,
        DeleteAccountUseCase,
        ListAccountsUseCase,
        RecalculateAccountBalanceUseCase,
        UpdateAccountUseCase,
    )
    from lib.domain.use_cases.currencies import (
        ConvertCurrencyUseCase,
        ListCurrenciesUseCase,
        UpdateExchangeRatesUseCase,
    )
    from lib.domain.use_cases.debts import (
        ArchiveDebtUseCase,
        CalculateDebtInterestUseCase,
        CreateDebtUseCase,
        DeleteDebtPaymentUseCase,
        DeleteDebtUseCase,
        GetDebtProjectionUseCase,
        ListDebtsUseCase,
        MarkOverdueDebtsUseCase,
        RepayDebtUseCase,
        UpdateDebtUseCase,
    )
    from lib.domain.use_cases.export_data import ExportDataUseCase
    from lib.domain.use_cases.goals import (
        ArchiveGoalUseCase,
        ContributeToGoalUseCase,
        CreateGoalUseCase,
        DeleteGoalContributionUseCase,
        DeleteGoalUseCase,
        DuplicateGoalUseCase,
        GetGoalProjectionUseCase,
        ListGoalsUseCase,
        UpdateGoalUseCase,
    )
    from lib.domain.use_cases.categories import (
        CreateCategoryUseCase,
        DeleteCategoryUseCase,
        FindOrCreateCategoryUseCase,
        ListCategoriesUseCase,
        UpdateCategoryUseCase,
    )
    from lib.domain.use_cases.settings import GetSettingsUseCase, UpdateSettingsUseCase
    from lib.domain.use_cases.subscriptions import (
        ChargeSubscriptionNowUseCase,
        CreateSubscriptionUseCase,
        DeleteSubscriptionChargeUseCase,
        DeleteSubscriptionUseCase,
        GetSubscriptionAnalyticsUseCase,
        ListSubscriptionsUseCase,
        PauseSubscriptionUseCase,
        ProcessDueSubscriptionsUseCase,
        ResumeSubscriptionUseCase,
        UpdateSubscriptionUseCase,
    )
    from lib.domain.use_cases.transactions import (
        AddTransactionUseCase,
        DeleteTransactionUseCase,
        GetTransactionStatsUseCase,
        ListTransactionsUseCase,
        UpdateTransactionUseCase,
    )

    def _wire(attr: str, factory: Any, *deps: str) -> None:
        values = []
        for dep in deps:
            value = getattr(container, dep)
            if value is None:
                container.missing.append(attr)
                container.errors[attr] = f"missing dependency: {dep}"
                return
            values.append(value)
        try:
            setattr(container, attr, factory(*values))
        except Exception as exc:  # pragma: no cover
            container.missing.append(attr)
            container.errors[attr] = f"construct failed: {exc}"

    _wire(
        "add_transaction",
        AddTransactionUseCase,
        "transaction_repository",
        "account_repository",
        "goal_repository",
        "debt_repository",
    )
    _wire(
        "update_transaction",
        UpdateTransactionUseCase,
        "transaction_repository",
        "account_repository",
        "goal_repository",
        "debt_repository",
    )
    _wire(
        "delete_transaction",
        DeleteTransactionUseCase,
        "transaction_repository",
        "account_repository",
        "goal_repository",
        "debt_repository",
    )
    _wire("list_transactions", ListTransactionsUseCase, "transaction_repository")
    _wire(
        "get_transaction_stats",
        GetTransactionStatsUseCase,
        "transaction_repository",
    )

    _wire("create_account", CreateAccountUseCase, "account_repository")
    _wire("update_account", UpdateAccountUseCase, "account_repository")
    _wire("delete_account", DeleteAccountUseCase, "account_repository")
    _wire("list_accounts", ListAccountsUseCase, "account_repository")
    _wire(
        "recalculate_account_balance",
        RecalculateAccountBalanceUseCase,
        "account_repository",
        "transaction_repository",
    )

    _wire("create_goal", CreateGoalUseCase, "goal_repository")
    _wire("update_goal", UpdateGoalUseCase, "goal_repository")
    _wire("delete_goal", DeleteGoalUseCase, "goal_repository")
    _wire("list_goals", ListGoalsUseCase, "goal_repository")
    _wire("archive_goal", ArchiveGoalUseCase, "goal_repository")
    _wire("duplicate_goal", DuplicateGoalUseCase, "goal_repository")
    _wire(
        "get_goal_projection",
        GetGoalProjectionUseCase,
        "goal_repository",
        "transaction_repository",
    )
    _wire(
        "delete_goal_contribution",
        DeleteGoalContributionUseCase,
        "transaction_repository",
        "delete_transaction",
    )
    _wire(
        "contribute_to_goal",
        ContributeToGoalUseCase,
        "goal_repository",
        "account_repository",
        "add_transaction",
        "currency_repository",
        "transaction_repository",
    )

    _wire(
        "create_debt",
        CreateDebtUseCase,
        "debt_repository",
        "account_repository",
        "add_transaction",
    )
    _wire("update_debt", UpdateDebtUseCase, "debt_repository")
    _wire("delete_debt", DeleteDebtUseCase, "debt_repository")
    _wire("list_debts", ListDebtsUseCase, "debt_repository")
    _wire("archive_debt", ArchiveDebtUseCase, "debt_repository")
    _wire("mark_overdue_debts", MarkOverdueDebtsUseCase, "debt_repository")
    _wire(
        "get_debt_projection",
        GetDebtProjectionUseCase,
        "debt_repository",
        "transaction_repository",
    )
    _wire(
        "delete_debt_payment",
        DeleteDebtPaymentUseCase,
        "transaction_repository",
        "delete_transaction",
    )
    _wire(
        "repay_debt",
        RepayDebtUseCase,
        "debt_repository",
        "account_repository",
        "add_transaction",
        "currency_repository",
    )
    _wire(
        "calculate_debt_interest",
        CalculateDebtInterestUseCase,
        "debt_repository",
    )

    _wire("create_subscription", CreateSubscriptionUseCase, "subscription_repository")
    _wire("update_subscription", UpdateSubscriptionUseCase, "subscription_repository")
    _wire("delete_subscription", DeleteSubscriptionUseCase, "subscription_repository")
    _wire("list_subscriptions", ListSubscriptionsUseCase, "subscription_repository")
    _wire("pause_subscription", PauseSubscriptionUseCase, "subscription_repository")
    _wire("resume_subscription", ResumeSubscriptionUseCase, "subscription_repository")
    _wire(
        "process_due_subscriptions",
        ProcessDueSubscriptionsUseCase,
        "subscription_repository",
        "transaction_repository",
        "account_repository",
        "settings_repository",
    )
    _wire(
        "charge_subscription_now",
        ChargeSubscriptionNowUseCase,
        "subscription_repository",
        "transaction_repository",
        "account_repository",
        "settings_repository",
    )
    _wire(
        "delete_subscription_charge",
        DeleteSubscriptionChargeUseCase,
        "transaction_repository",
        "subscription_repository",
        "delete_transaction",
    )
    _wire(
        "get_subscription_analytics",
        GetSubscriptionAnalyticsUseCase,
        "subscription_repository",
        "transaction_repository",
        "currency_repository",
    )

    # Currencies: provider is optional for UpdateExchangeRatesUseCase
    if container.currency_repository is not None:
        container.update_exchange_rates = UpdateExchangeRatesUseCase(
            container.currency_repository,
            provider=container.exchange_rate_provider,
        )
        container.convert_currency = ConvertCurrencyUseCase(
            container.currency_repository
        )
        container.list_currencies = ListCurrenciesUseCase(
            container.currency_repository
        )
    else:
        for name in ("update_exchange_rates", "convert_currency", "list_currencies"):
            container.missing.append(name)
            container.errors[name] = "missing dependency: currency_repository"

    _wire("get_settings", GetSettingsUseCase, "settings_repository")
    _wire("update_settings", UpdateSettingsUseCase, "settings_repository")

    _wire("list_categories", ListCategoriesUseCase, "category_repository")
    _wire("create_category", CreateCategoryUseCase, "category_repository")
    _wire("update_category", UpdateCategoryUseCase, "category_repository")
    _wire("delete_category", DeleteCategoryUseCase, "category_repository")
    _wire(
        "find_or_create_category",
        FindOrCreateCategoryUseCase,
        "category_repository",
    )

    _wire(
        "export_data",
        ExportDataUseCase,
        "account_repository",
        "transaction_repository",
        "goal_repository",
        "debt_repository",
        "subscription_repository",
        "currency_repository",
        "settings_repository",
    )

    if container.missing:
        logger.info(
            "Container built with %d missing dependencies: %s",
            len(container.missing),
            ", ".join(container.missing),
        )
    else:
        logger.info("Container built successfully (all dependencies wired)")

    return container
