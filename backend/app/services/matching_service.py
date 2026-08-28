import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.database import models
from app.services.risk_service import calculate_invoice_risk

logger = logging.getLogger("app.services.matching_service")

def run_matching_engine(db: Session, invoice_id: int):
    """
    Two-stage matching engine:
    Stage 1: Eligibility Filter
    Stage 2: Suitability Scoring
    
    Saves and returns the ranked matches for an invoice.
    """
    # 1. Fetch invoice
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # 2. Check if verified
    if invoice.verification_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Invoice verification is blocked or pending. Matching requires verified invoices.",
                "error_code": "INVOICE_NOT_VERIFIED"
            }
        )

    # 3. Ensure risk has been calculated
    if invoice.risk_score is None:
        calculate_invoice_risk(db, invoice.id)
        db.refresh(invoice)

    # 4. Load all financier profiles
    financiers = db.query(models.Financier).all()
    if not financiers:
        return []

    # Clear previous matches
    db.query(models.Match).filter(models.Match.invoice_id == invoice.id).delete()
    db.commit()

    matches = []
    invoice_amount = invoice.total_amount
    tenure_days = (invoice.due_date - invoice.invoice_date).days if invoice.due_date and invoice.invoice_date else 60
    if tenure_days <= 0:
        tenure_days = 60

    # Fetch buyer and supplier for industry check
    buyer = db.query(models.Buyer).filter(models.Buyer.id == invoice.buyer_id).first()
    industry = buyer.industry.lower() if buyer and buyer.industry else ""

    for f in financiers:
        reasons = []
        is_eligible = True

        # --- STAGE 1: ELIGIBILITY FILTER ---
        
        # A. Available capital check
        if f.available_capital < invoice_amount * 0.8:
            is_eligible = False
            reasons.append(f"Invoice amount ({invoice_amount}) exceeds available capital ({f.available_capital}).")
            
        # B. Max financing check
        if f.maximum_financing < invoice_amount * 0.8:
            is_eligible = False
            reasons.append(f"Invoice amount exceeds financier maximum financing limit ({f.maximum_financing}).")
            
        # C. Tenure compatibility
        if tenure_days < f.preferred_min_tenure or tenure_days > f.preferred_max_tenure:
            is_eligible = False
            reasons.append(f"Invoice tenure ({tenure_days} days) outside preferred range ({f.preferred_min_tenure}-{f.preferred_max_tenure} days).")
            
        # D. Risk Appetite Compatibility
        # low appetite only accepts LOW risk
        # medium appetite accepts LOW/MEDIUM
        # high appetite accepts LOW/MEDIUM/HIGH
        inv_risk = invoice.risk_level.lower()
        f_risk = f.risk_appetite.lower()
        
        if f_risk == "low" and inv_risk != "low":
            is_eligible = False
            reasons.append(f"Invoice risk ({invoice.risk_level}) exceeds low risk appetite.")
        elif f_risk == "medium" and inv_risk == "high":
            is_eligible = False
            reasons.append("Invoice risk (HIGH) exceeds medium risk appetite.")

        # --- STAGE 2: SUITABILITY SCORING ---
        suitability_score = 0.0
        
        if is_eligible:
            # 1. Financing amount fit (20%): reward financiers with max limits closer to this amount
            amount_ratio = min(f.maximum_financing / (invoice_amount * 0.8), 1.5)
            if amount_ratio >= 1.0:
                amount_fit = 20.0
            else:
                amount_fit = amount_ratio * 20.0
            suitability_score += amount_fit
            reasons.append("Optimal available capital fit.")

            # 2. Risk compatibility (20%): perfect fit gets full points
            if f_risk == inv_risk:
                risk_fit = 20.0
            else:
                risk_fit = 12.0 # acceptable but not exact
            suitability_score += risk_fit

            # 3. Rate fit (20%): Lower minimum rate gets higher score
            # Minimum rate range usually between 4% and 18%
            rate_fit = max(0.0, 20.0 - (f.minimum_rate - 4.0) * 1.1)
            suitability_score += rate_fit
            reasons.append(f"Competitive rate starting at {f.minimum_rate}%.")

            # 4. Tenure fit (15%):
            mid_tenure = (f.preferred_min_tenure + f.preferred_max_tenure) / 2
            tenure_diff = abs(tenure_days - mid_tenure)
            tenure_range = max(1, f.preferred_max_tenure - f.preferred_min_tenure)
            tenure_fit = max(0.0, 15.0 - (tenure_diff / tenure_range) * 15.0)
            suitability_score += tenure_fit

            # 5. Settlement speed (10%): Faster is better
            speed_fit = max(0.0, 10.0 - (f.settlement_speed_hours / 24) * 2.0)
            suitability_score += speed_fit
            if f.settlement_speed_hours <= 12:
                reasons.append(f"Fast settlement ({f.settlement_speed_hours} hours).")

            # 6. Fees (5%): Baseline score
            suitability_score += 5.0

            # 7. Industry preference (10%): Match
            industry_fit = 5.0 # default
            if f.preferred_industries:
                prefs = [p.strip().lower() for p in f.preferred_industries.split(",")]
                if industry in prefs:
                    industry_fit = 10.0
                    reasons.append(f"Matches preferred industry ({industry}).")
                else:
                    industry_fit = 0.0
            else:
                reasons.append("Financier is industry agnostic.")
            suitability_score += industry_fit

        suitability_score = round(suitability_score, 2)
        
        # Save Match record
        match_record = models.Match(
            invoice_id=invoice.id,
            financier_id=f.id,
            eligibility_status=is_eligible,
            suitability_score=suitability_score if is_eligible else 0.0,
            match_reasons=", ".join(reasons)
        )
        db.add(match_record)
        matches.append(match_record)

    db.commit()
    
    # Return matches sorted by suitability score (only eligible matches first, then non-eligible)
    # Actually, let's filter out non-eligible or place them at bottom
    db.expire_all()
    results = db.query(models.Match).filter(
        models.Match.invoice_id == invoice_id
    ).order_by(models.Match.eligibility_status.desc(), models.Match.suitability_score.desc()).all()
    
    return results
