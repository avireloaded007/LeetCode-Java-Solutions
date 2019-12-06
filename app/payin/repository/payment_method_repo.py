from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import and_
from typing_extensions import final

from app.commons import tracing
from app.commons.context.logger import get_logger
from app.commons.database.model import DBEntity, DBRequestModel

###########################################################
# PgpPaymentMethod DBEntity and CRUD operations           #
###########################################################
from app.commons.types import PgpCode
from app.payin.core.payer.types import PayerType
from app.payin.models.maindb import stripe_cards
from app.payin.models.paymentdb import pgp_payment_methods, payment_methods
from app.payin.repository.base import PayinDBRepository

log = get_logger(__name__)


class PgpPaymentMethodDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID
    pgp_code: PgpCode
    pgp_resource_id: str
    payer_id: Optional[UUID] = None
    pgp_card_id: Optional[str] = None
    legacy_consumer_id: Optional[str] = None
    object: Optional[str] = None
    type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    attached_at: Optional[datetime] = None
    detached_at: Optional[datetime] = None
    payment_method_id: Optional[UUID] = None


class PaymentMethodDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID
    payer_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class InsertPgpPaymentMethodInput(PgpPaymentMethodDbEntity):
    pass


class InsertPaymentMethodInput(PaymentMethodDbEntity):
    pass


class GetPgpPaymentMethodByPgpResourceIdInput(DBRequestModel):
    pgp_resource_id: str


class GetPgpPaymentMethodByIdInput(DBRequestModel):
    id: UUID


class DeletePgpPaymentMethodByIdSetInput(DBRequestModel):
    detached_at: datetime
    deleted_at: datetime
    updated_at: datetime


class DeletePgpPaymentMethodByIdWhereInput(DBRequestModel):
    id: UUID


class GetPgpPaymentMethodByPaymentMethodId(DBRequestModel):
    id: UUID


class ListPgpPaymentMethodByStripeCustomerIdInput(DBRequestModel):
    stripe_customer_id: str


class ListStripeCardDbEntitiesByConsumerId(DBRequestModel):
    dd_consumer_id: str


###########################################################
# StripeCard DBEntity and CRUD operations                 #
###########################################################
class InsertStripeCardDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    stripe_id: str
    fingerprint: str
    last4: str
    dynamic_last4: str
    exp_month: str
    exp_year: str
    type: str
    country_of_origin: Optional[str] = None
    zip_code: Optional[str] = None
    created_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    is_scanned: Optional[bool] = None
    dd_fingerprint: Optional[str] = None
    active: bool
    consumer_id: Optional[int] = None
    stripe_customer_id: Optional[int] = None
    external_stripe_customer_id: Optional[str] = None
    tokenization_method: Optional[str] = None
    address_line1_check: Optional[str] = None
    address_zip_check: Optional[str] = None
    validation_card_id: Optional[int] = None


class StripeCardDbEntity(InsertStripeCardDbEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: int


class InsertStripeCardInput(InsertStripeCardDbEntity):
    pass


class GetStripeCardByStripeIdInput(DBRequestModel):
    stripe_id: str


class GetStripeCardByIdInput(DBRequestModel):
    id: int


class DeleteStripeCardByIdSetInput(DBRequestModel):
    removed_at: datetime
    active: bool


class DeleteStripeCardByIdWhereInput(DBRequestModel):
    id: int


class GetStripeCardsByStripeCustomerIdInput(DBRequestModel):
    stripe_customer_id: str


class GetStripeCardsByConsumerIdInput(DBRequestModel):
    consumer_id: int


class GetDuplicateStripeCardInput(DBRequestModel):
    fingerprint: str
    dynamic_last4: str
    exp_year: str
    exp_month: str
    active: bool
    external_stripe_customer_id: Optional[
        str
    ]  # FIXME: need to fix foreign key contraint issue in Integration Test then change to consumer_id, or add new index and consolidate the deduplication code in DSJ cx/drive
    consumer_id: Optional[int]
    stripe_customer_id: Optional[int]


class ListStripeCardDbEntitiesByStripeCustomerId(DBRequestModel):
    stripe_customer_id: str


class ListPgpPaymentMethodByStripeCardId(DBRequestModel):
    stripe_id_list: List[str]


class PaymentMethodRepositoryInterface:
    """
    PaymentMethod repository interface class that exposes complicated CRUD operations APIs for business layer.
    """

    @abstractmethod
    async def insert_pgp_payment_method(
        self, pm_input: InsertPgpPaymentMethodInput
    ) -> PgpPaymentMethodDbEntity:
        ...

    async def insert_payment_method(
        self, pm_input: InsertPaymentMethodInput
    ) -> PaymentMethodDbEntity:
        ...

    @abstractmethod
    async def insert_stripe_card(
        self, sc_input: InsertStripeCardInput
    ) -> StripeCardDbEntity:
        ...

    @abstractmethod
    async def get_pgp_payment_method_by_pgp_resource_id(
        self, input: GetPgpPaymentMethodByPgpResourceIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        ...

    @abstractmethod
    async def get_pgp_payment_method_by_id(
        self, input: GetPgpPaymentMethodByIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        ...

    @abstractmethod
    async def get_pgp_payment_method_by_payment_method_id(
        self, input: GetPgpPaymentMethodByPaymentMethodId
    ) -> Optional[PgpPaymentMethodDbEntity]:
        ...

    @abstractmethod
    async def get_stripe_card_by_stripe_id(
        self, input: GetStripeCardByStripeIdInput
    ) -> Optional[StripeCardDbEntity]:
        ...

    @abstractmethod
    async def get_stripe_card_by_id(
        self, input: GetStripeCardByIdInput
    ) -> Optional[StripeCardDbEntity]:
        ...

    @abstractmethod
    async def get_duplicate_stripe_card(
        self, payer_type: PayerType, input: GetDuplicateStripeCardInput
    ) -> Optional[StripeCardDbEntity]:
        ...

    @abstractmethod
    async def list_stripe_card_db_entities_by_stripe_customer_id(
        self, input: ListStripeCardDbEntitiesByStripeCustomerId
    ) -> List[StripeCardDbEntity]:
        ...

    @abstractmethod
    async def list_pgp_payment_method_entities_by_stripe_card_ids(
        self, input: ListPgpPaymentMethodByStripeCardId
    ) -> List[PgpPaymentMethodDbEntity]:
        ...

    @abstractmethod
    async def list_stripe_card_db_entities_by_consumer_id(
        self, input: ListStripeCardDbEntitiesByConsumerId
    ) -> List[StripeCardDbEntity]:
        ...


@tracing.track_breadcrumb(repository_name="payment_method")
@final
@dataclass
class PaymentMethodRepository(PaymentMethodRepositoryInterface, PayinDBRepository):
    """
    PaymentMethod repository class that exposes complicated CRUD operations APIs for business layer.
    """

    async def insert_pgp_payment_method(
        self, pm_input: InsertPgpPaymentMethodInput
    ) -> PgpPaymentMethodDbEntity:
        paymentdb_conn = self.payment_database.master()
        async with paymentdb_conn.transaction():
            # insert object into pgp_payment_methods table
            stmt = (
                pgp_payment_methods.table.insert()
                .values(pm_input.dict(skip_defaults=True))
                .returning(*pgp_payment_methods.table.columns.values())
            )
            row = await self.payment_database.master().fetch_one(stmt)
            return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def insert_payment_method(
        self, pm_input: InsertPaymentMethodInput
    ) -> PaymentMethodDbEntity:
        stmt = (
            payment_methods.table.insert()
            .values(pm_input.dict(skip_defaults=True))
            .returning(*payment_methods.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return PaymentMethodDbEntity.from_row(row)  # type: ignore

    async def insert_stripe_card(
        self, sc_input: InsertStripeCardInput
    ) -> StripeCardDbEntity:
        maindb_conn = self.main_database.master()
        async with maindb_conn.transaction():
            # insert object into stripe_card table
            stmt = (
                stripe_cards.table.insert()
                .values(sc_input.dict(skip_defaults=True))
                .returning(*stripe_cards.table.columns.values())
            )
            row = await maindb_conn.fetch_one(stmt)
            return StripeCardDbEntity.from_row(row) if row else None

    async def get_pgp_payment_method_by_pgp_resource_id(
        self, input: GetPgpPaymentMethodByPgpResourceIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        stmt = pgp_payment_methods.table.select().where(
            pgp_payment_methods.pgp_resource_id == input.pgp_resource_id
        )
        row = await self.payment_database.replica().fetch_one(stmt)
        return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def get_pgp_payment_method_by_id(
        self, input: GetPgpPaymentMethodByIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        stmt = pgp_payment_methods.table.select().where(
            pgp_payment_methods.id == input.id
        )
        row = await self.payment_database.replica().fetch_one(stmt)
        return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def get_pgp_payment_method_by_payment_method_id(
        self, input: GetPgpPaymentMethodByPaymentMethodId
    ) -> Optional[PgpPaymentMethodDbEntity]:
        stmt = pgp_payment_methods.table.select().where(
            pgp_payment_methods.payment_method_id == input.id
        )
        row = await self.payment_database.replica().fetch_one(stmt)
        return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def delete_pgp_payment_method_by_id(
        self,
        input_set: DeletePgpPaymentMethodByIdSetInput,
        input_where: DeletePgpPaymentMethodByIdWhereInput,
    ) -> Optional[PgpPaymentMethodDbEntity]:
        stmt = (
            pgp_payment_methods.table.update()
            .where(pgp_payment_methods.id == input_where.id)
            .values(input_set.dict(skip_defaults=True))
            .returning(*pgp_payment_methods.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def get_stripe_card_by_stripe_id(
        self, input: GetStripeCardByStripeIdInput
    ) -> Optional[StripeCardDbEntity]:
        stmt = stripe_cards.table.select().where(
            stripe_cards.stripe_id == input.stripe_id
        )
        row = await self.main_database.replica().fetch_one(stmt)
        return StripeCardDbEntity.from_row(row) if row else None

    async def get_stripe_card_by_id(
        self, input: GetStripeCardByIdInput
    ) -> Optional[StripeCardDbEntity]:
        stmt = stripe_cards.table.select().where(stripe_cards.id == input.id)
        row = await self.main_database.replica().fetch_one(stmt)
        return StripeCardDbEntity.from_row(row) if row else None

    async def delete_stripe_card_by_id(
        self,
        input_set: DeleteStripeCardByIdSetInput,
        input_where: DeleteStripeCardByIdWhereInput,
    ):
        stmt = (
            stripe_cards.table.update()
            .where(stripe_cards.id == input_where.id)
            .values(input_set.dict(skip_defaults=True))
            .returning(*stripe_cards.table.columns.values())
        )
        row = await self.main_database.master().fetch_one(stmt)
        return StripeCardDbEntity.from_row(row) if row else None

    async def get_dd_stripe_card_ids_by_stripe_customer_id(
        self, input: GetStripeCardsByStripeCustomerIdInput
    ):
        stmt = stripe_cards.table.select().where(
            stripe_cards.external_stripe_customer_id == input.stripe_customer_id
        )
        stripe_card_rows = await self.main_database.replica().fetch_all(stmt)
        stripe_card_db_entities = [
            StripeCardDbEntity.from_row(row) for row in stripe_card_rows
        ]
        return stripe_card_db_entities

    async def get_stripe_cards_by_consumer_id(
        self, input: GetStripeCardsByConsumerIdInput
    ) -> List[StripeCardDbEntity]:
        stmt = stripe_cards.table.select().where(
            stripe_cards.consumer_id == input.consumer_id
        )
        rows = await self.main_database.replica().fetch_all(stmt)
        return [StripeCardDbEntity.from_row(row) for row in rows]

    async def get_duplicate_stripe_card(
        self, payer_type: PayerType, input: GetDuplicateStripeCardInput
    ) -> Optional[StripeCardDbEntity]:
        if payer_type == PayerType.MARKETPLACE:
            stmt = stripe_cards.table.select().where(
                and_(
                    stripe_cards.fingerprint == input.fingerprint,
                    stripe_cards.dynamic_last4 == input.dynamic_last4,
                    stripe_cards.exp_year == input.exp_year,
                    stripe_cards.exp_month == input.exp_month,
                    # stripe_cards.external_stripe_customer_id == input.external_stripe_customer_id,
                    stripe_cards.consumer_id == input.consumer_id,
                    stripe_cards.active == input.active,
                )
            )
        else:
            stmt = stripe_cards.table.select().where(
                and_(
                    stripe_cards.fingerprint == input.fingerprint,
                    stripe_cards.dynamic_last4 == input.dynamic_last4,
                    stripe_cards.exp_year == input.exp_year,
                    stripe_cards.exp_month == input.exp_month,
                    stripe_cards.stripe_customer_id == input.stripe_customer_id,
                    stripe_cards.active == input.active,
                )
            )
        row = await self.main_database.replica().fetch_one(stmt)
        return StripeCardDbEntity.from_row(row) if row else None

    async def list_stripe_card_db_entities_by_stripe_customer_id(
        self, input: ListStripeCardDbEntitiesByStripeCustomerId
    ) -> List[StripeCardDbEntity]:
        stmt = stripe_cards.table.select().where(
            stripe_cards.external_stripe_customer_id == input.stripe_customer_id
        )
        rows = await self.main_database.replica().fetch_all(stmt)
        stripe_card_db_entities: List[StripeCardDbEntity] = []
        for row in rows:
            stripe_card_db_entities.append(StripeCardDbEntity.from_row(row))
        return stripe_card_db_entities

    async def list_stripe_card_db_entities_by_consumer_id(
        self, input: ListStripeCardDbEntitiesByConsumerId
    ) -> List[StripeCardDbEntity]:
        stmt = stripe_cards.table.select().where(
            stripe_cards.consumer_id == input.dd_consumer_id
        )
        rows = await self.main_database.replica().fetch_all(stmt)
        stripe_card_db_entities: List[StripeCardDbEntity] = []
        for row in rows:
            stripe_card_db_entities.append(StripeCardDbEntity.from_row(row))
        return stripe_card_db_entities

    async def list_pgp_payment_method_entities_by_stripe_card_ids(
        self, input: ListPgpPaymentMethodByStripeCardId
    ) -> List[PgpPaymentMethodDbEntity]:
        stmt = pgp_payment_methods.table.select().where(
            pgp_payment_methods.pgp_resource_id.in_(input.stripe_id_list)
        )
        rows = await self.payment_database.replica().fetch_all(stmt)
        pgp_payment_method_db_entities: List[PgpPaymentMethodDbEntity] = []
        for row in rows:
            pgp_payment_method_db_entities.append(
                PgpPaymentMethodDbEntity.from_row(row)
            )
        return pgp_payment_method_db_entities
