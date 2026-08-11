"""SQLAlchemy currency and exchange-rate repository."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional, Sequence
from uuid import uuid4

from sqlalchemy import select

from lib.domain.entities.currency import Currency, ExchangeRate
from lib.domain.repositories.currency_repository import CurrencyRepository
from lib.infrastructure.db_models import CurrencyModel, ExchangeRateModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.currency")


def _currency_to_entity(model: CurrencyModel, *, lang: str = "en") -> Currency:
    code = (lang or "en").lower()
    if code.startswith("ru") and model.name_ru:
        name = model.name_ru
    elif model.name_en:
        name = model.name_en
    else:
        name = model.name_ru or model.name or model.code
    return Currency(
        code=model.code,
        name=name,
        symbol=model.symbol,
        is_crypto=model.is_crypto,
    )


def _apply_currency(model: CurrencyModel, entity: Currency) -> None:
    model.code = entity.code.upper()
    model.name = entity.name
    if not model.name_en:
        model.name_en = entity.name
    if not model.name_ru:
        model.name_ru = entity.name
    # Prefer keeping bilingual columns in sync when only `name` is provided.
    if model.name_en == "" or model.name_en == model.code:
        model.name_en = entity.name
    model.symbol = entity.symbol
    model.is_crypto = entity.is_crypto


def _rate_to_entity(model: ExchangeRateModel) -> ExchangeRate:
    return ExchangeRate(
        id=model.id,
        base=model.base,
        quote=model.quote,
        rate=Decimal(str(model.rate)),
        updated_at=ensure_utc(model.updated_at) or datetime.now(timezone.utc),
    )


def _apply_rate(model: ExchangeRateModel, entity: ExchangeRate, *, is_new: bool) -> None:
    # Never rewrite PK of an existing row — a fresh entity.id would make
    # SQLAlchemy UPDATE by a non-existent id → StaleDataError.
    if is_new or not model.id:
        model.id = entity.id or str(uuid4())
    model.base = entity.base.upper()
    model.quote = entity.quote.upper()
    model.rate = entity.rate
    model.updated_at = ensure_utc(entity.updated_at) or datetime.now(timezone.utc)


class SqlAlchemyCurrencyRepository(CurrencyRepository):
    """Currency / rate persistence via SQLAlchemy sync session + ``asyncio.to_thread``."""

    def __init__(self, session_factory: SessionFactory, *, default_lang: str = "en") -> None:
        self._session_factory = session_factory
        self._default_lang = default_lang

    async def upsert_currency(self, currency: Currency) -> Currency:
        return await asyncio.to_thread(self._upsert_currency_sync, currency)

    async def get_currency(self, code: str) -> Optional[Currency]:
        return await asyncio.to_thread(self._get_currency_sync, code)

    async def list_currencies(self, *, include_crypto: bool = True) -> list[Currency]:
        return await asyncio.to_thread(self._list_currencies_sync, include_crypto)

    async def upsert_rate(self, rate: ExchangeRate) -> ExchangeRate:
        return await asyncio.to_thread(self._upsert_rate_sync, rate)

    async def get_rate(self, base: str, quote: str) -> Optional[ExchangeRate]:
        return await asyncio.to_thread(self._get_rate_sync, base, quote)

    async def list_rates(self, *, base: Optional[str] = None) -> list[ExchangeRate]:
        return await asyncio.to_thread(self._list_rates_sync, base)

    async def upsert_rates(self, rates: Sequence[ExchangeRate]) -> list[ExchangeRate]:
        return await asyncio.to_thread(self._upsert_rates_sync, list(rates))

    async def seed_from_json(self, path: Path | str) -> int:
        """Load currency definitions from a JSON file. Returns upserted count."""
        return await asyncio.to_thread(self._seed_from_json_sync, Path(path))

    def _upsert_currency_sync(self, entity: Currency) -> Currency:
        with session_scope(self._session_factory) as session:
            model = session.get(CurrencyModel, entity.code.upper())
            if model is None:
                model = CurrencyModel(code=entity.code.upper())
                session.add(model)
            _apply_currency(model, entity)
            session.flush()
            logger.debug("Upserted currency %s", model.code)
            return _currency_to_entity(model, lang=self._default_lang)

    def _get_currency_sync(self, code: str) -> Optional[Currency]:
        with session_scope(self._session_factory) as session:
            model = session.get(CurrencyModel, code.upper())
            return _currency_to_entity(model, lang=self._default_lang) if model else None

    def _list_currencies_sync(self, include_crypto: bool) -> list[Currency]:
        with session_scope(self._session_factory) as session:
            stmt = select(CurrencyModel).order_by(CurrencyModel.code)
            if not include_crypto:
                stmt = stmt.where(CurrencyModel.is_crypto.is_(False))
            return [
                _currency_to_entity(r, lang=self._default_lang)
                for r in session.scalars(stmt).all()
            ]

    def _upsert_rate_sync(self, rate: ExchangeRate) -> ExchangeRate:
        with session_scope(self._session_factory) as session:
            stmt = select(ExchangeRateModel).where(
                ExchangeRateModel.base == rate.base.upper(),
                ExchangeRateModel.quote == rate.quote.upper(),
            )
            model = session.scalars(stmt).first()
            is_new = model is None
            if is_new:
                model = ExchangeRateModel(id=rate.id or str(uuid4()))
                session.add(model)
            _apply_rate(model, rate, is_new=is_new)
            session.flush()
            logger.debug("Upserted rate %s/%s = %s", model.base, model.quote, model.rate)
            return _rate_to_entity(model)

    def _upsert_rates_sync(self, rates: list[ExchangeRate]) -> list[ExchangeRate]:
        results: list[ExchangeRate] = []
        with session_scope(self._session_factory) as session:
            # Prefetch existing rows for this batch to avoid PK churn / races.
            pairs = {(r.base.upper(), r.quote.upper()) for r in rates}
            existing: dict[tuple[str, str], ExchangeRateModel] = {}
            if pairs:
                bases = {b for b, _ in pairs}
                stmt = select(ExchangeRateModel).where(
                    ExchangeRateModel.base.in_(bases)
                )
                for row in session.scalars(stmt).all():
                    key = (row.base.upper(), row.quote.upper())
                    if key in pairs:
                        existing[key] = row

            for rate in rates:
                key = (rate.base.upper(), rate.quote.upper())
                model = existing.get(key)
                is_new = model is None
                if is_new:
                    model = ExchangeRateModel(id=rate.id or str(uuid4()))
                    session.add(model)
                    existing[key] = model
                _apply_rate(model, rate, is_new=is_new)
                results.append(_rate_to_entity(model))
            session.flush()
        logger.info("Upserted %s exchange rates", len(results))
        return results

    def _get_rate_sync(self, base: str, quote: str) -> Optional[ExchangeRate]:
        with session_scope(self._session_factory) as session:
            stmt = select(ExchangeRateModel).where(
                ExchangeRateModel.base == base.upper(),
                ExchangeRateModel.quote == quote.upper(),
            )
            model = session.scalars(stmt).first()
            return _rate_to_entity(model) if model else None

    def _list_rates_sync(self, base: Optional[str]) -> list[ExchangeRate]:
        with session_scope(self._session_factory) as session:
            stmt = select(ExchangeRateModel)
            if base is not None:
                stmt = stmt.where(ExchangeRateModel.base == base.upper())
            stmt = stmt.order_by(ExchangeRateModel.base, ExchangeRateModel.quote)
            return [_rate_to_entity(r) for r in session.scalars(stmt).all()]

    def _seed_from_json_sync(self, path: Path) -> int:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to read currencies JSON from %s", path)
            raise

        items = payload if isinstance(payload, list) else payload.get("currencies", [])
        count = 0
        with session_scope(self._session_factory) as session:
            for item in items:
                code = str(item["code"]).upper()
                model = session.get(CurrencyModel, code)
                if model is None:
                    model = CurrencyModel(code=code)
                    session.add(model)
                model.name_ru = item.get("name_ru", item.get("name", code))
                model.name_en = item.get("name_en", item.get("name", code))
                model.name = model.name_en or model.name_ru or code
                model.symbol = item.get("symbol", code)
                model.is_crypto = bool(item.get("is_crypto", False))
                count += 1
            session.flush()
        logger.info("Seeded %s currencies from %s", count, path)
        return count
