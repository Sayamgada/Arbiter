from app.schemas.negotiation import (
    AuthorityTier,
    BuyerSignals,
    TrustScoreResult,
)


class TrustScoreEngine:
    """
    Transparent weighted trust scoring.

    Weights follow the system design:
        identity  = 30%
        intent    = 25%
        history   = 20%
        violations = 15%
        behavior  = 10%
    """

    IDENTITY_WEIGHT = 0.30
    INTENT_WEIGHT = 0.25
    HISTORY_WEIGHT = 0.20
    VIOLATION_WEIGHT = 0.15
    BEHAVIOR_WEIGHT = 0.10

    FULL_THRESHOLD = 80.0
    RESTRICTED_THRESHOLD = 40.0
    MAX_VIOLATIONS = 5

    def score(self, signals: BuyerSignals) -> TrustScoreResult:
        violation_rate = min(
            signals.violation_count / self.MAX_VIOLATIONS,
            1.0,
        )

        violation_score = (1.0 - violation_rate) * 100

        identity_component = (
            signals.identity_confidence * self.IDENTITY_WEIGHT
        )
        intent_component = (
            signals.intent_confidence * self.INTENT_WEIGHT
        )
        history_component = (
            signals.history_score * self.HISTORY_WEIGHT
        )
        violation_component = (
            violation_score * self.VIOLATION_WEIGHT
        )
        behavior_component = (
            signals.behavior_score * self.BEHAVIOR_WEIGHT
        )

        total = (
            identity_component
            + intent_component
            + history_component
            + violation_component
            + behavior_component
        )

        score = round(max(0.0, min(total, 100.0)), 2)

        if score >= self.FULL_THRESHOLD:
            authority = AuthorityTier.FULL
        elif score >= self.RESTRICTED_THRESHOLD:
            authority = AuthorityTier.RESTRICTED
        else:
            authority = AuthorityTier.BLOCK

        return TrustScoreResult(
            score=score,
            authority=authority,
            sub_scores={
                "identity": round(signals.identity_confidence, 2),
                "intent": round(signals.intent_confidence, 2),
                "history": round(signals.history_score, 2),
                "violation_score": round(violation_score, 2),
                "behavior": round(signals.behavior_score, 2),
            },
        )
