from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import get_redis

from app.schemas.api import (
    NegotiationRequest,
    NegotiationResponse,
    NegotiationSessionRequest,
    NegotiationSessionResponse,
    PaymentOrderRequest,
    PaymentOrderResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
)

from app.schemas.negotiation import (
    NegotiationStatus,
    TransactionStatus,
)
from app.services.buyer_service import BuyerService
from app.services.decision_controller import NegotiationDecisionController
from app.services.merchant_service import MerchantPolicyService
from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService
from app.services.payment_service import PaymentService

from app.agents.buyer_agent import BuyerAgent
from app.agents.session import NegotiationSession
from app.agents.seller_agent import SellerGrowthAgent
from app.services.llm_service import LLMService


router = APIRouter()


@router.post(
    "/api/v1/negotiation/decide",
    response_model=NegotiationResponse,
    tags=["negotiation"],
)
def decide(
    request: NegotiationRequest,
    db: Session = Depends(get_db),
):
    buyer = BuyerService(db).get_by_buyer_id(
        request.buyer_id
    )

    if buyer is None:
        raise HTTPException(
            status_code=404,
            detail="Buyer not found",
        )

    if not buyer.is_active:
        raise HTTPException(
            status_code=403,
            detail="Buyer is inactive",
        )

    product = ProductService(db).get_by_id(
        product_id=request.product_id,
        merchant_id=request.merchant_id,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found for merchant",
        )

    merchant_policy = MerchantPolicyService(
        db
    ).get_by_merchant_id(
        request.merchant_id
    )

    if merchant_policy is None:
        raise HTTPException(
            status_code=404,
            detail="Merchant policy not found",
        )

    controller = NegotiationDecisionController(
        get_redis()
    )

    result = controller.decide(
        merchant_id=request.merchant_id,
        period=request.period,
        buyer_signals=request.buyer_signals,
        product_price=product.price,
        product_cost=product.cost,
        requested_discount_pct=request.requested_discount_pct,
        max_discount_pct=merchant_policy.max_discount_pct,
        allocated_budget=merchant_policy.daily_budget,
    )

    transaction = TransactionService(
        db
    ).create_from_decision(
        buyer_id=buyer.id,
        merchant_id=request.merchant_id,
        product_id=product.id,
        proposed_offer={
            "requested_discount_pct": (
                request.requested_discount_pct
            ),
            "product_price": product.price,
            "product_cost": product.cost,
        },
        result=result,
    )

    return NegotiationResponse(
        transaction_id=transaction.transaction_id,
        decision=result.decision.value,
        authority=result.authority.value,
        trust_score=result.trust_score,
        discount_pct=result.discount_pct,
        discount_value=result.discount_value,
        final_price=result.final_price,
        budget_remaining=result.budget_remaining,
        reason=result.reason,
    )

@router.post(
    "/api/v1/negotiation/session",
    response_model=NegotiationSessionResponse,
    tags=["negotiation"],
)
def start_session(
    request: NegotiationSessionRequest,
    db: Session = Depends(get_db),
):
    llm_service = LLMService()

    buyer = BuyerService(db).get_by_buyer_id(
        request.buyer_id
    )

    if buyer is None:
        raise HTTPException(
            status_code=404,
            detail="Buyer not found",
        )

    if not buyer.is_active:
        raise HTTPException(
            status_code=403,
            detail="Buyer is inactive",
        )

    product = ProductService(db).get_by_id(
        product_id=request.product_id,
        merchant_id=request.merchant_id,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found for merchant",
        )

    merchant_policy = MerchantPolicyService(
        db
    ).get_by_merchant_id(
        request.merchant_id
    )

    if merchant_policy is None:
        raise HTTPException(
            status_code=404,
            detail="Merchant policy not found",
        )

    controller = NegotiationDecisionController(
        get_redis()
    )

    session_id = (
        f"session_{request.buyer_id}_"
        f"{request.merchant_id}_"
        f"{request.product_id}"
    )

    buyer_agent = BuyerAgent(
        buyer_id=request.buyer_id,
        merchant_id=request.merchant_id,
        product_id=str(request.product_id),
        session_id=session_id,
        target_discount_pct=(
            request.requested_discount_pct
        ),
        llm_service=llm_service,
    )

    seller_agent = SellerGrowthAgent(
        controller=controller,
        merchant_id=request.merchant_id,
        period=request.period,
        buyer_signals=request.buyer_signals,
        max_discount_pct=(
            merchant_policy.max_discount_pct
        ),
        allocated_budget=(
            merchant_policy.daily_budget
        ),
        llm_service=llm_service,
    )

    session = NegotiationSession(
        buyer=buyer_agent,
        seller=seller_agent,
        product_price=product.price,
        product_cost=product.cost,
        max_rounds=request.max_rounds,
    )

    result = session.start()

    transaction_id = None

    if result.status == NegotiationStatus.ACCEPTED:
        decision_result = seller_agent.last_decision_result

        if decision_result is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Negotiation was accepted but "
                    "authorization result was unavailable."
                ),
            )

        transaction = TransactionService(
            db
        ).create_from_decision(
            buyer_id=buyer.id,
            merchant_id=request.merchant_id,
            product_id=product.id,
            proposed_offer={
                "session_id": result.session_id,
                "requested_discount_pct": (
                    request.requested_discount_pct
                ),
                "product_price": product.price,
                "product_cost": product.cost,
                "allocated_budget": (
                    merchant_policy.daily_budget
                ),
            },
            result=decision_result,
            session_id=result.session_id,
        )

        transaction_id = transaction.transaction_id

    return NegotiationSessionResponse(
        session_id=result.session_id,
        transaction_id=transaction_id,
        status=result.status,
        rounds=result.rounds,
        final_price=result.final_price,
        final_discount_pct=result.final_discount_pct,
        message=result.message,
        messages=result.messages,
    )


@router.post(
    "/api/v1/payment/order",
    response_model=PaymentOrderResponse,
    tags=["payment"],
)
def create_payment_order(
    request: PaymentOrderRequest,
    db: Session = Depends(get_db),
):
    transaction_service = TransactionService(db)

    transaction = transaction_service.get_by_transaction_id(
        request.transaction_id
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    if transaction.status != TransactionStatus.PAYMENT_PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=(
                "Payment order can only be created for "
                "transactions in payment_pending state"
            ),
        )

    final_price = transaction.final_offer.get(
        "final_price"
    )

    if final_price is None or final_price <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Transaction does not contain a valid "
                "final price"
            ),
        )

    try:
        payment_service = PaymentService()

        order = payment_service.create_order(
            amount=final_price,
            currency="INR",
            receipt=transaction.transaction_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Unable to create payment order: {exc}"
            ),
        ) from exc

    transaction_service.update_status(
        transaction=transaction,
        status=TransactionStatus.PAYMENT_CREATED,
        razorpay_ref=order["id"],
    )

    return PaymentOrderResponse(
        transaction_id=transaction.transaction_id,
        razorpay_order_id=order["id"],
        amount=final_price,
        currency=order.get("currency", "INR"),
        status=TransactionStatus.PAYMENT_CREATED,
    )


@router.post(
    "/api/v1/payment/verify",
    response_model=PaymentVerifyResponse,
    tags=["payment"],
)
def verify_payment(
    request: PaymentVerifyRequest,
    db: Session = Depends(get_db),
):
    transaction_service = TransactionService(db)

    transaction = transaction_service.get_by_transaction_id(
        request.transaction_id
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    if transaction.status != TransactionStatus.PAYMENT_CREATED.value:
        raise HTTPException(
            status_code=400,
            detail=(
                "Payment verification can only be performed "
                "for transactions in payment_created state"
            ),
        )

    if transaction.razorpay_ref != request.razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail="Razorpay order does not match transaction",
        )

    payment_service = PaymentService()

    try:
        payment_service.verify_payment(
            order_id=request.razorpay_order_id,
            payment_id=request.razorpay_payment_id,
            signature=request.razorpay_signature,
        )
    except Exception as exc:
        transaction_service.update_status(
            transaction=transaction,
            status=TransactionStatus.PAYMENT_FAILED,
        )

        raise HTTPException(
            status_code=400,
            detail=f"Payment verification failed: {exc}",
        ) from exc

    transaction_service.update_status(
        transaction=transaction,
        status=TransactionStatus.PAYMENT_AUTHORIZED,
        razorpay_ref=request.razorpay_payment_id,
    )

    return PaymentVerifyResponse(
        transaction_id=transaction.transaction_id,
        razorpay_payment_id=request.razorpay_payment_id,
        status=TransactionStatus.PAYMENT_AUTHORIZED,
        message="Payment verified successfully.",
    )
