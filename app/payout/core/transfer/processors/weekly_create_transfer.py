from datetime import datetime, timedelta

from aioredlock import Aioredlock

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional, List

from app.commons.cache.cache import PaymentCache
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.async_kafka_producer import KafkaMessageProducer
from app.commons.lock.lockable import Lockable
from app.commons.providers.dsj_client import DSJClient
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.constants import ENABLE_QUEUEING_MECHANISM_FOR_PAYOUT
from app.payout.core.transfer.processors.create_transfer import (
    CreateTransferRequest,
    CreateTransfer,
)
from app.payout.core.transfer.tasks.create_transfer_task import CreateTransferTask
from app.payout.models import PayoutDay, TransferType
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.commons.runtime import runtime
from random import shuffle

from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepositoryInterface,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


class WeeklyCreateTransferResponse(OperationResponse):
    pass


class WeeklyCreateTransferRequest(OperationRequest):
    payout_day: PayoutDay
    payout_countries: List[str]
    end_time: datetime
    unpaid_txn_start_time: datetime
    whitelist_payment_account_ids: List[int]
    exclude_recently_updated_accounts: Optional[bool] = False


class WeeklyCreateTransfer(
    AsyncOperation[WeeklyCreateTransferRequest, WeeklyCreateTransferResponse]
):
    """
    Processor to create a transfer when triggered by cron job.
    """

    transfer_repo: TransferRepositoryInterface
    transaction_repo: TransactionRepositoryInterface
    payment_account_repo: PaymentAccountRepositoryInterface
    payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface
    stripe_transfer_repo: StripeTransferRepositoryInterface
    managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface
    payment_lock_manager: Aioredlock
    stripe: StripeAsyncClient
    kafka_producer: KafkaMessageProducer
    cache: PaymentCache
    dsj_client: DSJClient
    payout_lock_repo: Lockable

    def __init__(
        self,
        request: WeeklyCreateTransferRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface,
        payment_lock_manager: Aioredlock,
        stripe: StripeAsyncClient,
        kafka_producer: KafkaMessageProducer,
        cache: PaymentCache,
        dsj_client: DSJClient,
        logger: BoundLogger = None,
        payout_lock_repo: Lockable,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.transaction_repo = transaction_repo
        self.payment_account_repo = payment_account_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.payment_lock_manager = payment_lock_manager
        self.stripe = stripe
        self.kafka_producer = kafka_producer
        self.cache = cache
        self.dsj_client = dsj_client
        self.payout_lock_repo = payout_lock_repo

    async def _execute(self) -> WeeklyCreateTransferResponse:
        payout_day = self.request.payout_day
        end_time = self.request.end_time
        unpaid_txn_start_time = self.request.unpaid_txn_start_time
        exclude_recently_updated_accounts = (
            self.request.exclude_recently_updated_accounts
        )
        self.logger.info(
            "Executing weekly_create_transfers",
            payout_day=payout_day,
            end_time=end_time,
            unpaid_txn_start_time=unpaid_txn_start_time,
            exclude_recently_updated_accounts=exclude_recently_updated_accounts,
        )
        if self.request.whitelist_payment_account_ids:
            payment_account_ids = self.request.whitelist_payment_account_ids
        else:
            payment_account_ids = []
            unpaid_payment_account_ids = await self.transaction_repo.get_payout_account_ids_for_unpaid_transactions_without_limit(
                start_time=unpaid_txn_start_time, end_time=end_time
            )
            for unpaid_account_id in unpaid_payment_account_ids:
                if self._is_enabled_for_payment_service_traffic(unpaid_account_id):
                    payment_account_ids.append(unpaid_account_id)
            self.logger.info(
                "[Weekly Create Transfers] total unpaid_payment_account_ids count",
                total_number=len(payment_account_ids),
            )

            # ATO prevention: exclude payment account ids that should be blocked because of ATO and only apply this to dx
            if exclude_recently_updated_accounts:
                ids_blocked_by_ato = await self.get_payment_account_ids_blocked_by_ato()
                payment_account_ids = list(
                    set(unpaid_payment_account_ids) - set(ids_blocked_by_ato)
                )
                self.logger.info(
                    "Executing weekly_create_transfers with accounts blocked by ATO excluded",
                    total_ato_accounts=len(unpaid_payment_account_ids)
                    - len(payment_account_ids),
                    total_unpaid_accounts=len(unpaid_payment_account_ids),
                )

        # randomize the account ids so they're not processed in any specific order and spread out
        # the accounts that may have more transactions or slower task execution
        shuffle(payment_account_ids)

        transfer_count = 0
        for account_id in payment_account_ids:
            try:
                if runtime.get_bool(ENABLE_QUEUEING_MECHANISM_FOR_PAYOUT, False):
                    # put create_transfer into queue
                    self.logger.info(
                        "Enqueuing transfer creation for account",
                        payout_account_id=account_id,
                    )
                    create_transfer_task = CreateTransferTask(
                        payout_day=payout_day,
                        payout_account_id=account_id,
                        transfer_type=TransferType.SCHEDULED,
                        end_time=end_time.isoformat(),
                        payout_countries=self.request.payout_countries,
                        start_time=None,
                        submit_after_creation=True,
                        created_by_id=None,
                    )
                    await create_transfer_task.send(kafka_producer=self.kafka_producer)
                else:
                    create_transfer_request = CreateTransferRequest(
                        payout_account_id=account_id,
                        transfer_type=TransferType.SCHEDULED,
                        end_time=end_time,
                        payout_countries=self.request.payout_countries,
                        payout_day=payout_day,
                        start_time=None,
                        submit_after_creation=True,
                        created_by_id=None,
                    )
                    create_transfer_op = CreateTransfer(
                        logger=self.logger,
                        request=create_transfer_request,
                        transfer_repo=self.transfer_repo,
                        payment_account_repo=self.payment_account_repo,
                        payment_account_edit_history_repo=self.payment_account_edit_history_repo,
                        managed_account_transfer_repo=self.managed_account_transfer_repo,
                        transaction_repo=self.transaction_repo,
                        stripe_transfer_repo=self.stripe_transfer_repo,
                        payment_lock_manager=self.payment_lock_manager,
                        stripe=self.stripe,
                        kafka_producer=self.kafka_producer,
                        cache=self.cache,
                        dsj_client=self.dsj_client,
                        payout_lock_repo=self.payout_lock_repo,
                    )
                    await create_transfer_op.execute()
            except Exception as e:
                self.logger.warn(
                    "[weekly_create_transfer] Failed to create_transfer for payment account. ",
                    payment_account_id=account_id,
                    error=e,
                )
                continue
            transfer_count += 1
        self.logger.info(
            "Finished executing weekly_create_transfers.",
            payout_day=payout_day,
            end_time=end_time,
            unpaid_txn_start_time=unpaid_txn_start_time,
            transfer_count=transfer_count,
        )
        return WeeklyCreateTransferResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, WeeklyCreateTransferResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def get_payment_account_ids_blocked_by_ato(self) -> List[int]:
        """
        ATO prevention hack
        Get a list of payment account ids that should be blocked by Account Takeover
        :rtype: list
        """
        payout_blocks_in_hours = runtime.get_int(
            "payout/feature-flags/DASHER_ATO_PREVENTION_THRESHOLD_IN_HOURS.int",
            default=0,
        )
        if payout_blocks_in_hours == 0:
            return []
        last_bank_account_update_allowed_at = datetime.utcnow() - timedelta(
            hours=payout_blocks_in_hours
        )
        recently_updated_payment_account_ids = await self.payment_account_edit_history_repo.get_recent_bank_update_payment_account_ids(
            last_bank_account_update_allowed_at=last_bank_account_update_allowed_at
        )
        return recently_updated_payment_account_ids

    def _is_enabled_for_payment_service_traffic(self, account_id: int) -> bool:
        """
        Check whether the given account is enabled for payment service or not
        """
        data = runtime.get_json(
            "payout/feature-flags/enable_list_transfers_v1.json", {}
        )

        # Check if feature flag is turned on for all
        if data.get("enable_all", False):
            return True

        if account_id is None:
            return False

        # Check if account id is in whitelist
        if account_id in data.get("white_list", []):
            return True
        # Check if account id is in enabled bucket
        if account_id % 100 < data.get("bucket", 0):
            return True
        return False
