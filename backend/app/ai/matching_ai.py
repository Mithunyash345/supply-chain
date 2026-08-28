from typing import List, Dict, Any

def evaluate_and_rank_offers(
    invoice_amount: float, 
    risk_level: str, 
    offers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Ranks submitted financier offers based on a deterministic multi-factor scoring model.
    Does not rank solely on interest rate.
    
    Factors considered:
    1. Financing Amount Fit (Weight 30%): How close the offered financing is to the invoice amount.
    2. Interest Rate (Weight 30%): Lower interest rate is preferred.
    3. Fees (Weight 15%): Lower fee is preferred.
    4. Settlement Speed (Weight 15%): Faster settlement (lower hours) is preferred.
    5. Tenure Match (Weight 10%): Match between tenure and risk expectations.
    """
    if not offers:
        return []

    scored_offers = []
    
    # 1. Determine min and max limits for normalization
    rates = [o["interest_rate"] for o in offers]
    fees = [o["fee"] for o in offers]
    speeds = [o["settlement_speed_hours"] for o in offers]
    amounts = [o["financing_amount"] for o in offers]
    
    min_rate, max_rate = min(rates), max(rates)
    min_fee, max_fee = min(fees), max(fees)
    min_speed, max_speed = min(speeds), max(speeds)
    min_amount, max_amount = min(amounts), max(amounts)

    for offer in offers:
        # Avoid division by zero in normalization
        
        # Amount Fit Score: higher is better (normalized 0 to 100)
        # We want to reward offers that match or are close to the requested invoice_amount
        amount_ratio = offer["financing_amount"] / invoice_amount
        # Cap ratio at 1.0 (if they offer more than invoice_amount, which shouldn't happen, it's 100%)
        amount_fit_score = min(amount_ratio * 100, 100.0)

        # Rate Score: lower is better (normalized 0 to 100)
        if max_rate == min_rate:
            rate_score = 100.0
        else:
            # Scale from 0 (worst rate) to 100 (best rate)
            rate_score = ((max_rate - offer["interest_rate"]) / (max_rate - min_rate)) * 100.0

        # Fee Score: lower is better (normalized 0 to 100)
        if max_fee == min_fee:
            fee_score = 100.0
        else:
            fee_score = ((max_fee - offer["fee"]) / (max_fee - min_fee)) * 100.0

        # Settlement Speed Score: lower is better (normalized 0 to 100)
        if max_speed == min_speed:
            speed_score = 100.0
        else:
            speed_score = ((max_speed - offer["settlement_speed_hours"]) / (max_speed - min_speed)) * 100.0

        # Tenure match score (basic logic: reward standard 30-90 days, penalize outliers)
        tenure = offer["tenure_days"]
        if 30 <= tenure <= 90:
            tenure_score = 100.0
        elif tenure < 30:
            tenure_score = 60.0
        else:
            tenure_score = max(0.0, 100.0 - (tenure - 90) * 1.5)

        # Calculate final weighted score
        final_score = (
            (amount_fit_score * 0.30) +
            (rate_score * 0.30) +
            (fee_score * 0.15) +
            (speed_score * 0.15) +
            (tenure_score * 0.10)
        )
        
        final_score = round(final_score, 2)
        
        # Build explanation
        reasons = []
        if rate_score >= 80:
            reasons.append("highly competitive interest rate")
        if amount_fit_score >= 95:
            reasons.append("excellent financing amount coverage")
        if speed_score >= 80:
            reasons.append("rapid settlement speed")
        if fee_score >= 80:
            reasons.append("low admin/processing fees")
            
        if not reasons:
            reasons.append("balanced terms across rate, fee, and amount")
            
        explanation = f"Offer scored {final_score}/100. Strengths include: {', '.join(reasons)}."
        
        scored_offers.append({
            **offer,
            "offer_score": final_score,
            "explanation": explanation
        })

    # Sort offers by score in descending order
    scored_offers.sort(key=lambda x: x["offer_score"], reverse=True)
    
    # Add rank
    for rank, offer in enumerate(scored_offers, start=1):
        offer["rank"] = rank

    return scored_offers
