"""Align the sole cash account with the app display currency when needed."""

from __future__ import annotations

import logging
from typing import Any

from lib.domain.entities.currency_codes import normalize_currency_code

logger = logging.getLogger("finanse.domain.use_cases.align_currencies")


async def align_sole_account_currency(container: Any) -> bool:
    """If there is exactly one account and it differs from settings base, retarget it.

    Returns True when a migration ran.
    """
    if (
        container.get_settings is None
        or container.list_accounts is None
        or container.update_account is None
    ):
        return False

    settings = await container.get_settings.execute()
    base = normalize_currency_code(settings.default_currency)
    accounts = await container.list_accounts.execute(active_only=False)
    if len(accounts) != 1:
        return False

    account = accounts[0]
    current = normalize_currency_code(account.currency)
    if current == base:
        return False

    updated = account.model_copy(update={"currency": base})
    await container.update_account.execute(updated)
    logger.info(
        "Aligned sole account %s currency %s → %s",
        account.name,
        current,
        base,
    )

    if container.list_transactions is None or container.update_transaction is None:
        return True

    txs = await container.list_transactions.execute(account_id=account.id)
    for tx in txs:
        if normalize_currency_code(tx.currency) == base:
            continue
        await container.update_transaction.execute(
            tx.model_copy(update={"currency": base})
        )
    return True
