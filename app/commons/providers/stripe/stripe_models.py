from datetime import datetime
from enum import Enum
from typing import Dict, List, NewType, Optional, Any

import pydantic

from app.commons.types import CountryCode

# global stripe settings
# hard code this because we'll need code changes anyway to support newer versions
STRIPE_API_VERSION = "2019-08-14"


IdempotencyKey = Optional[str]
SettingsByCountryCode = Dict[CountryCode, "StripeClientSettings"]
SettingsList = List["StripeClientSettings"]
TokenId = NewType("TokenId", str)
CustomerId = NewType("CustomerId", str)
ConnectedAccountId = NewType("ConnectedAccountId", str)
PaymentMethodId = NewType("PaymentMethodId", str)
PaymentIntentId = NewType("PaymentIntentId", str)
PaymentIntentStatus = NewType("PaymentIntentStatus", str)
StripeDisputeId = NewType("StripeDisputeId", str)
Currency = NewType("Currency", str)
Amount = NewType("Amount", int)
Destination = NewType("Destination", str)
StatementDescriptor = NewType("StatementDescriptor", str)
StripeAccountId = NewType("StripeAccountId", str)
Metadata = NewType("Metadata", dict)


class StripeBaseModel(pydantic.BaseModel):
    # object String that comes from a typical stripe response. Denotes the object 'type'
    # Reference: https://stripe.com/docs/api/events/object#event_object-object
    _STRIPE_OBJECT_NAME: Optional[str] = None

    def dict(self, *, include=None, exclude=None, by_alias=False, skip_defaults=True):
        """
        Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        By default, we skip serializing any default (or unset) values
        """
        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
        )


class StripeClientSettings(StripeBaseModel):
    # informational
    country: CountryCode

    # stripe settings
    api_key: str
    api_version: Optional[str] = STRIPE_API_VERSION

    @property
    def client_settings(self) -> dict:
        return {"api_key": self.api_key, "stripe_version": self.api_version}


# --------------- REQUEST MODELS ---------------------------------------------------------------------------------------
class CreateConnectedAccountToken(StripeBaseModel):
    card: str
    stripe_account: str
    customer: str


class CreateBankAccountToken(StripeBaseModel):
    ...


class CreateCreditCardToken(StripeBaseModel):
    number: str
    exp_month: int
    exp_year: int
    cvc: str


class CreateCustomer(StripeBaseModel):
    email: str
    description: str


class UpdateCustomer(StripeBaseModel):
    class InvoiceSettings(StripeBaseModel):
        default_payment_method: str

    sid: str
    invoice_settings: InvoiceSettings


class TransferData(StripeBaseModel):
    destination: ConnectedAccountId
    amount: Optional[int]


class CreatePaymentIntent(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_intents/create
    """

    class CaptureMethod(str, Enum):
        AUTOMATIC = "automatic"
        MANUAL = "manual"

    class ConfirmationMethod(str, Enum):
        AUTOMATIC = "automatic"
        MANUAL = "manual"

    class SetupFutureUsage(str, Enum):
        ON_SESSION = "on_session"
        OFF_SESSION = "off_session"

    # TODO Determine how we can use types where Enums are defined.  For example capture_method: Optional[CaptureMethod].
    # If used directly stripe will error out.
    amount: int
    currency: str
    application_fee_amount: Optional[int]
    capture_method: Optional[str]
    confirm: Optional[bool]
    confirmation_method: Optional[str]
    customer: Optional[CustomerId]
    description: Optional[str]
    metadata: Optional[Dict[str, Any]]
    off_session: Optional[bool]  # only when confirm=True
    on_behalf_of: Optional[ConnectedAccountId]
    payment_method: Optional[PaymentMethodId]
    payment_method_options: Optional[dict]
    payment_method_types: Optional[str]
    receipt_email: Optional[str]
    return_url: Optional[str]  # only when confirm=True
    save_payment_method: Optional[bool]
    setup_future_usage: Optional[str]
    shipping: Optional[dict]
    statement_descriptor: Optional[str]
    transfer_data: Optional[TransferData]
    transfer_group: Optional[str]


class CapturePaymentIntent(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_intents/capture
    """

    sid: PaymentIntentId
    amount_to_capture: Optional[int]
    application_fee_amount: Optional[int]
    statement_descriptor: Optional[str]
    transfer_data: Optional[TransferData]


class CancelPaymentIntent(StripeBaseModel):
    class CancellationReason(str, Enum):
        ABANDONED = "abandoned"
        DUPLICATE = "duplicate"
        FRAUDULENT = "fraudulent"
        REQUESTED_BY_CONSUMER = "requested_by_customer"

    sid: PaymentIntentId
    cancellation_reason: str


class RefundCharge(StripeBaseModel):
    class RefundReason(str, Enum):
        DUPLICATE = "duplicate"
        FRAUDULENT = "fraudulent"
        REQUESTED_BY_CONSUMER = "requested_by_customer"

    charge: str
    amount: Optional[int]
    metadata: Optional[Dict]
    reason: Optional[str]
    refund_application_fee: Optional[bool]
    reverse_transfer: Optional[bool]


class CreatePaymentMethod(StripeBaseModel):
    class Card(StripeBaseModel):
        token: str

    type: str
    card: Card


class AttachPaymentMethod(StripeBaseModel):
    sid: str
    customer: str


class DetachPaymentMethod(StripeBaseModel):
    sid: str


class RetrievePaymentMethod(StripeBaseModel):
    id: str


class RetrievePayout(StripeBaseModel):
    id: str
    stripe_account: str


class CancelPayout(StripeBaseModel):
    sid: str
    stripe_account: str


class UpdateDispute(StripeBaseModel):
    class Evidence(StripeBaseModel):
        access_activity_log: Optional[str] = None
        billing_address: Optional[str] = None
        cancellation_policy: Optional[str] = None
        cancellation_policy_disclosure: Optional[str] = None
        cancellation_rebuttal: Optional[str] = None
        customer_communication: Optional[str] = None
        customer_email_address: Optional[str] = None
        customer_name: Optional[str] = None
        customer_purchase_ip: Optional[str] = None
        customer_signature: Optional[str] = None
        duplicate_charge_documentation: Optional[str] = None
        duplicate_charge_explanation: Optional[str] = None
        duplicate_charge_id: Optional[str] = None
        product_description: Optional[str] = None
        receipt: Optional[str] = None
        refund_policy: Optional[str] = None
        refund_policy_disclosure: Optional[str] = None
        refund_refusal_explanation: Optional[str] = None
        service_date: Optional[str] = None
        service_documentation: Optional[str] = None
        shipping_address: Optional[str] = None
        shipping_carrier: Optional[str] = None
        shipping_date: Optional[str] = None
        shipping_documentation: Optional[str] = None
        shipping_tracking_number: Optional[str] = None
        uncategorized_file: Optional[str] = None
        uncategorized_text: Optional[str] = None

    sid: str
    evidence: Evidence


class CreateTransfer(StripeBaseModel):
    description: Optional[str]
    metadata: Optional[Dict]
    source_transaction: Optional[str]
    source_type: Optional[str]
    transfer_group: Optional[str]


class CreatePayout(StripeBaseModel):
    description: Optional[str]
    destination: Optional[str]
    metadata: Optional[Dict]
    method: Optional[str]
    source_type: Optional[str]
    statement_descriptor: Optional[str]


# --------------- RESPONSE MODELS --------------------------------------------------------------------------------------
class Address(StripeBaseModel):
    city: Optional[str]
    country: Optional[str]
    line1: Optional[str]
    line2: Optional[str]
    postal_code: Optional[str]
    state: Optional[str]


class BillingDetails(StripeBaseModel):
    address: Optional[Address]
    email: Optional[str]
    name: Optional[str]
    phone: Optional[str]


class Shipping(StripeBaseModel):
    address: Optional[Address]
    carrier: Optional[str]
    name: Optional[str]
    phone: Optional[str]
    tracking_nubmer: Optional[str]


class PaymentMethodOptions(StripeBaseModel):
    class CardOptions(StripeBaseModel):
        class RequestThreeDSecure(str, Enum):
            automatic = "automatic"
            any = "any"

        request_three_d_secure: Optional[RequestThreeDSecure]

    card: Optional[CardOptions]


class Outcome(StripeBaseModel):
    network_status: str
    reason: str
    risk_level: str
    risk_score: int
    rule: str
    seller_message: str
    type: str


class PaymentMethod(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_methods/object
    """

    _STRIPE_OBJECT_NAME: str = "payment_method"

    class Card(StripeBaseModel):
        class Wallet(StripeBaseModel):
            type: str
            dynamic_last4: str

        exp_month: int
        exp_year: int
        fingerprint: str
        last4: str
        funding: Optional[str]
        brand: Optional[str]
        country: Optional[str]
        description: Optional[str]
        wallet: Optional[Wallet]

    id: str
    type: str
    object: Optional[str]
    customer: Optional[str]
    card: Card
    billing_details: BillingDetails


class Event(StripeBaseModel):
    """
    https://stripe.com/docs/api/events
    """

    _STRIPE_OBJECT_NAME: str = "event"

    id: str
    object: str
    account: Optional[str]
    api_version: str
    created: datetime

    class Data(StripeBaseModel):
        object: Dict[str, Any]
        previous_attributes: Optional[Dict[str, Any]]

    data: Data
    livemode: bool
    pending_webhooks: int

    class Request(StripeBaseModel):
        id: Optional[str]
        idempotency_key: Optional[str]

    request: Optional[Request]
    type: str

    @property
    def resource_type(self):
        """
        Reference: https://stripe.com/docs/api/events/object#event_object-type
        :return: str represeting the api resource type in Stripe's API
        """
        return self.data.object.get("object")

    @property
    def event_type(self):
        """
        Reference: https://stripe.com/docs/api/events/object#event_object-type
        :return: str represeting the api resource type in Stripe's API
        """
        split_type = self.type.rsplit(".", 1)
        return split_type[1]

    @property
    def data_object(self):
        return self.data.object


class Refund(StripeBaseModel):
    """
    https://stripe.com/docs/api/refunds
    """

    _STRIPE_OBJECT_NAME: str = "refund"

    id: str
    object: str
    amount: int
    balance_transaction: Optional[str]
    charge: str
    created: int
    currency: str
    metadata: Optional[Dict]
    reason: Optional[str]
    receipt_number: Optional[str]
    source_transfer_reversal: Optional[str]
    status: str
    transfer_reversal: Optional[str]


class Charge(StripeBaseModel):
    """
    https://stripe.com/docs/api/charges
    """

    _STRIPE_OBJECT_NAME: str = "charge"

    id: str
    object: str
    amount: int
    amount_refunded: int
    # amount_updates - preview feature
    application: str
    application_fee: str
    application_fee_amount: int
    balance_transaction: str
    billing_details: Optional[BillingDetails]
    captured: bool
    created: datetime
    currency: str
    customer: str
    description: Optional[str]
    dispute: Optional[str]
    failure_code: Optional[str]
    failure_message: Optional[str]
    invoice: Optional[str]
    livemode: bool
    metadata: Optional[Dict]
    on_behalf_of: Optional[str]
    order: Optional[str]
    outcome: Optional[Outcome]
    paid: bool
    payment_intent: Optional[str]
    payment_method: Optional[str]
    # TODO payment_method_details
    receipt_email: Optional[str]
    receipt_number: Optional[str]
    receipt_url: Optional[str]
    refunded: bool
    # TODO refunds
    review: Optional[str]
    shipping: Optional[Shipping]
    source_transfer: Optional[str]
    statement_descriptor: Optional[str]
    statement_descriptor_suffix: Optional[str]
    status: str
    transfer: Optional[str]
    transfer_data: Optional[TransferData]
    transfer_group: Optional[str]


class PaymentIntent(StripeBaseModel):
    """
    https://stripe.com/docs/api/payment_intents
    """

    _STRIPE_OBJECT_NAME: str = "payment_intent"

    class NextAction(StripeBaseModel):
        class RedirectToUrl(StripeBaseModel):
            return_url: str
            url: str

        redirect_to_url: RedirectToUrl
        type: str
        use_stripe_sdk: str

    class LastPaymentError(StripeBaseModel):
        charge: Optional[str]
        code: Optional[str]
        decline_code: Optional[str]
        doc_url: Optional[str]
        message: Optional[str]
        param: Optional[str]
        payment_method: Optional[PaymentMethod]
        type: Optional[str]

    class Charges(StripeBaseModel):
        data: List[Charge]
        has_more: bool
        object: str
        url: Optional[str]

    id: str
    object: str
    amount: int
    amount_capturable: Optional[int]
    amount_received: Optional[int]
    application: Optional[str]
    application_fee_amount: Optional[int]
    canceled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    capture_method: str
    charges: Charges
    confirmation_method: str
    created: datetime
    currency: str
    customer: str
    description: Optional[str]
    invoice: Optional[str]
    last_payment_error: Optional[LastPaymentError]
    livemode: bool
    metadata: Optional[dict]
    next_action: Optional[NextAction]
    on_behalf_of: str
    payment_method: str
    payment_method_options: Optional[PaymentMethodOptions]
    payment_method_types: List[str]
    receipt_email: str
    review: str
    setup_future_usage: str
    shipping: Optional[Shipping]
    statement_descriptor: Optional[str]
    status: str
    transfer_data: Optional[TransferData]
    transfer_group: Optional[str]


class TransferReversal(StripeBaseModel):
    id: str
    object: str
    amount: int
    balanced_transaction: str
    created: datetime
    currency: str
    destination_payment_refund: str
    metadata: dict
    source_refund: str
    transfer: str


class Transfer(StripeBaseModel):
    class Reversals(StripeBaseModel):
        data: List[TransferReversal]
        has_more: bool
        object: str
        url: Optional[str]

    id: str
    object: str
    amount: int
    amount_reversed: int
    balance_transaction: str
    created: datetime
    currency: str
    description: str
    destination: str
    destination_payment: str
    livemode: bool
    metadata: dict
    reversals: Reversals
    reversed: bool
    source_transaction: str
    source_type: str
    transfer_group: str


class Payout(StripeBaseModel):
    id: str
    object: str
    amount: int
    arrival_date: datetime
    automatic: bool
    balance_transaction: str
    created: datetime
    currency: str
    description: str
    destination: str
    failure_balance_transaction: str
    failure_code: str
    failure_message: str
    livemode: bool
    metadata: dict
    method: str
    source_type: str
    statement_descriptor: str
    status: str
    type: str


class SourceTypes(StripeBaseModel):
    bank_account: int
    card: int


class Balance(StripeBaseModel):
    class Available(StripeBaseModel):
        amount: int
        currency: str
        source_types: SourceTypes

    class ConnectReserved(StripeBaseModel):
        amount: int
        currency: str
        source_types: SourceTypes

    class Pending(StripeBaseModel):
        amount: int
        currency: str
        source_types: SourceTypes

    object: str
    available: List[Available]
    connect_reserved: List[ConnectReserved]
    livemode: bool
    pending: List[Pending]