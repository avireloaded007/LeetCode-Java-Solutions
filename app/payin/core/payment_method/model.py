from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel
from typing_extensions import final

from app.payin.core.exceptions import PayinErrorCode, PaymentMethodReadError
from app.payin.core.payment_method.types import WalletType
from app.payin.repository.payment_method_repo import (
    PgpPaymentMethodDbEntity,
    StripeCardDbEntity,
)


@final
class Wallet(BaseModel):
    type: WalletType
    dynamic_last4: str


@final
class Card(BaseModel):
    last4: str
    exp_year: str
    exp_month: str
    fingerprint: str
    active: bool
    legacy_dd_stripe_card_id: int  # primary key of maindb_stripe_card
    country: Optional[str]
    brand: Optional[str]
    payment_provider_card_id: Optional[str] = None
    wallet: Optional[Wallet] = None


@final
class PaymentMethod(BaseModel):
    payment_provider: str
    card: Card
    id: Optional[UUID] = None  # make it optional for existing DSJ stripe_card
    payer_id: Optional[UUID] = None
    type: Optional[str]
    dd_consumer_id: Optional[str] = None
    payment_provider_customer_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


@final
class PaymentMethodList(BaseModel):
    count: int
    has_more: bool  # Currently default to False. Returning all the disputes for a query
    data: List[PaymentMethod]


class RawPaymentMethod:
    def __init__(
        self,
        pgp_payment_method_entity: Optional[PgpPaymentMethodDbEntity] = None,
        stripe_card_entity: Optional[StripeCardDbEntity] = None,
    ):
        self.pgp_payment_method_entity = pgp_payment_method_entity
        self.stripe_card_entity = stripe_card_entity

    def to_payment_method(self) -> PaymentMethod:
        """
        Build PaymentMethod object.

        :param pgp_payment_method_entity: pgp_payment_method_entity returned from pgp_payment_method. It could
               be None if the payment_method was not created through payin APIs.
        :param stripe_card_entity:
        :return: PaymentMethod object
        """
        if not self.stripe_card_entity:
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND, retryable=False
            )

        wallet: Optional[Wallet] = None
        if self.stripe_card_entity.tokenization_method:
            wallet = Wallet(
                type=self.stripe_card_entity.tokenization_method,
                dynamic_last4=self.stripe_card_entity.dynamic_last4,
            )

        card: Card = Card(
            country=self.stripe_card_entity.country_of_origin,
            last4=self.stripe_card_entity.last4,
            exp_year=self.stripe_card_entity.exp_year,
            exp_month=self.stripe_card_entity.exp_month,
            fingerprint=self.stripe_card_entity.fingerprint,
            active=self.stripe_card_entity.active,
            legacy_dd_stripe_card_id=self.stripe_card_entity.id,
            brand=self.stripe_card_entity.type,
            payment_provider_card_id=self.stripe_card_entity.stripe_id,
            wallet=wallet,
        )

        return (
            PaymentMethod(
                id=self.pgp_payment_method_entity.id,
                payer_id=self.pgp_payment_method_entity.payer_id,
                dd_consumer_id=self.pgp_payment_method_entity.legacy_consumer_id,
                payment_provider=self.pgp_payment_method_entity.pgp_code,
                type=self.pgp_payment_method_entity.type,
                card=card,
                created_at=self.pgp_payment_method_entity.created_at,
                updated_at=self.pgp_payment_method_entity.updated_at,
                deleted_at=self.pgp_payment_method_entity.deleted_at,
            )
            if self.pgp_payment_method_entity
            else PaymentMethod(
                dd_consumer_id=str(self.stripe_card_entity.consumer_id),
                payment_provider="stripe",
                type="card",
                card=card,
                created_at=self.stripe_card_entity.created_at,
                deleted_at=self.stripe_card_entity.removed_at,
                payer_id=None,
                payment_provider_customer_id=None,
                updated_at=None,
            )
        )

    def pgp_payment_method_id(self) -> str:
        pgp_payment_method_id: str
        if self.pgp_payment_method_entity:
            pgp_payment_method_id = self.pgp_payment_method_entity.pgp_resource_id
        elif self.stripe_card_entity:
            pgp_payment_method_id = self.stripe_card_entity.stripe_id

        return pgp_payment_method_id

    def legacy_dd_stripe_card_id(self) -> Optional[str]:
        return str(self.stripe_card_entity.id) if self.stripe_card_entity else None

    def payer_id(self) -> Optional[UUID]:
        return (
            self.pgp_payment_method_entity.payer_id
            if self.pgp_payment_method_entity
            else None
        )