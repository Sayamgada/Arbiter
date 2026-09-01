from pydantic import BaseModel, Field

from app.agents.buyer_agent import BuyerAgent
from app.agents.protocol import (
    AgentResponse,
    MessageType,
    NegotiationMessage,
)
from app.agents.seller_agent import SellerGrowthAgent
from app.schemas.negotiation import (
    NegotiationSessionResult,
    NegotiationStatus,
)

class NegotiationSessionResult(BaseModel):
    session_id: str
    status: NegotiationStatus
    rounds: int = Field(ge=0)
    final_price: float | None = None
    final_discount_pct: float | None = None
    message: str
    messages: list[
        NegotiationMessage | AgentResponse
    ] = Field(default_factory=list)


class NegotiationSession:
    """
    Coordinates a multi-round buyer/seller negotiation.

    The session manages conversation state, but it does not
    make authorization decisions. Seller offers are always
    evaluated by the Negotiation Decision Controller through
    SellerGrowthAgent.
    """

    def __init__(
        self,
        *,
        buyer: BuyerAgent,
        seller: SellerGrowthAgent,
        product_price: float,
        product_cost: float,
        max_rounds: int = 5,
    ):
        if product_price <= 0:
            raise ValueError(
                "Product price must be positive"
            )

        if product_cost < 0:
            raise ValueError(
                "Product cost cannot be negative"
            )

        if product_cost > product_price:
            raise ValueError(
                "Product cost cannot exceed product price"
            )

        if max_rounds < 1:
            raise ValueError(
                "Maximum rounds must be at least 1"
            )

        self.buyer = buyer
        self.seller = seller
        self.product_price = product_price
        self.product_cost = product_cost
        self.max_rounds = max_rounds

        self.round_number = 0
        self.status = NegotiationStatus.ACTIVE

        self.messages: list[
            NegotiationMessage | AgentResponse
        ] = []

        self.authorized_discount_value: float | None = None
        self.authorized_price: float | None = None
        self.authorized_discount_pct: float | None = None

    def start(self) -> NegotiationSessionResult:
        """
        Start the negotiation with the buyer's initial request.
        """
        if self.status != NegotiationStatus.ACTIVE:
            raise RuntimeError(
                "Negotiation session is no longer active"
            )

        request = self.buyer.create_purchase_request(
            product_price=self.product_price,
        )

        self.round_number = 1
        self.messages.append(request)

        return self._process_buyer_request(request)

    def _process_buyer_request(
        self,
        request: NegotiationMessage,
    ) -> NegotiationSessionResult:
        seller_response = self.seller.evaluate_offer(
            request,
            product_price=self.product_price,
            product_cost=self.product_cost,
        )

        self.messages.append(seller_response)

        if seller_response.message_type == MessageType.REJECT:
            self.status = NegotiationStatus.BLOCKED

            return NegotiationSessionResult(
                session_id=request.session_id,
                status=self.status,
                rounds=self.round_number,
                final_price=None,
                final_discount_pct=None,
                message=seller_response.message,
                messages=self.messages,
            )

        self.authorized_price = seller_response.price
        self.authorized_discount_pct = (
            seller_response.discount_pct
        )

        return self._process_seller_offer(
            seller_response
        )

    def _process_seller_offer(
        self,
        seller_response: AgentResponse,
    ) -> NegotiationSessionResult:
        buyer_response = self.buyer.respond_to_offer(
            price=seller_response.price,
            discount_pct=seller_response.discount_pct,
            round_number=self.round_number + 1,
        )

        self.messages.append(buyer_response)

        if buyer_response.message_type == MessageType.ACCEPT:
            return self._complete_transaction(
                seller_response
            )

        if (
            buyer_response.message_type
            == MessageType.COUNTER_OFFER
        ):
            return self._continue_negotiation(
                buyer_response
            )

        self.status = NegotiationStatus.REJECTED

        return NegotiationSessionResult(
            session_id=seller_response.session_id,
            status=self.status,
            rounds=self.round_number,
            final_price=None,
            final_discount_pct=None,
            message=buyer_response.message,
            messages=self.messages,
        )

    def _continue_negotiation(
        self,
        buyer_response: AgentResponse,
    ) -> NegotiationSessionResult:
        if self.round_number >= self.max_rounds:
            self.status = NegotiationStatus.EXPIRED

            return NegotiationSessionResult(
                session_id=self.buyer.session_id,
                status=self.status,
                rounds=self.round_number,
                final_price=None,
                final_discount_pct=None,
                message=(
                    "Negotiation ended because the "
                    "maximum number of rounds was reached."
                ),
                messages=self.messages,
            )

        self.round_number += 1

        request = NegotiationMessage(
            session_id=self.buyer.session_id,
            buyer_id=self.buyer.buyer_id,
            merchant_id=self.buyer.merchant_id,
            product_id=self.buyer.product_id,
            message_type=MessageType.COUNTER_OFFER,
            round_number=self.round_number,
            proposed_price=buyer_response.price,
            requested_discount_pct=(
                buyer_response.discount_pct
            ),
            message=buyer_response.message,
        )

        self.messages.append(request)

        return self._process_buyer_request(request)

    def _complete_transaction(
        self,
        seller_response: AgentResponse,
    ) -> NegotiationSessionResult:
        discount_value = round(
            self.product_price
            * seller_response.discount_pct
            / 100,
            2,
        )

        reservation = self.seller.commit_accepted_offer(
            discount_value=discount_value,
        )

        if not reservation.allowed:
            self.status = NegotiationStatus.REJECTED

            return NegotiationSessionResult(
                session_id=seller_response.session_id,
                status=self.status,
                rounds=self.round_number,
                final_price=None,
                final_discount_pct=None,
                message=(
                    "The offer was authorized, but the "
                    "autonomy budget could not be committed."
                ),
                messages=self.messages,
            )

        self.status = NegotiationStatus.ACCEPTED

        self.authorized_discount_value = (
            discount_value
        )

        return NegotiationSessionResult(
            session_id=seller_response.session_id,
            status=self.status,
            rounds=self.round_number,
            final_price=seller_response.price,
            final_discount_pct=seller_response.discount_pct,
            message=(
                "Negotiation accepted and budget committed."
            ),
            messages=self.messages,
        )