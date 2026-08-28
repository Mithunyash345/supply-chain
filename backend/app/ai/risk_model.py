import os
import joblib
import numpy as np
import logging
from sklearn.ensemble import RandomForestClassifier
from app.core.config import settings

logger = logging.getLogger("app.ai.risk_model")
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ml_models", "risk_model.joblib")

def generate_synthetic_data(num_samples: int = 200) -> tuple:
    """
    Generates synthetic training data for demo/testing purposes.
    Features:
    0. invoice_amount
    1. days_to_due
    2. supplier_transaction_count
    3. supplier_delay_count
    4. buyer_transaction_count
    5. buyer_average_delay
    6. previous_default_count
    7. financing_amount
    8. tenure_days
    
    Output:
    0 = likely normal/on-time
    1 = likely delayed/default
    """
    np.random.seed(42)
    
    # Random feature generation
    invoice_amount = np.random.uniform(5000, 2000000, num_samples)
    days_to_due = np.random.randint(15, 120, num_samples)
    supplier_transaction_count = np.random.randint(0, 100, num_samples)
    supplier_delay_count = np.random.randint(0, 20, num_samples)
    buyer_transaction_count = np.random.randint(0, 150, num_samples)
    buyer_average_delay = np.random.uniform(0, 30, num_samples)
    previous_default_count = np.random.randint(0, 5, num_samples)
    
    # Financing amount is typically 80% to 90% of invoice amount
    financing_amount = invoice_amount * np.random.uniform(0.8, 0.95, num_samples)
    tenure_days = days_to_due + np.random.randint(-5, 15, num_samples)
    
    X = np.column_stack([
        invoice_amount,
        days_to_due,
        supplier_transaction_count,
        supplier_delay_count,
        buyer_transaction_count,
        buyer_average_delay,
        previous_default_count,
        financing_amount,
        tenure_days
    ])
    
    # Calculate a probability-like score to assign labels deterministically with some noise
    # Higher risk factors should increase probability of default (label=1)
    risk_score = (
        (previous_default_count * 0.25) +
        (buyer_average_delay / 30.0 * 0.2) +
        (supplier_delay_count / (supplier_transaction_count + 1) * 0.2) +
        (invoice_amount / 2000000.0 * 0.15) +
        (tenure_days / 120.0 * 0.1) +
        (np.random.uniform(0, 0.2, num_samples))
    )
    
    y = (risk_score > 0.45).astype(int)
    
    return X, y

def train_model() -> str:
    """Trains the RandomForest risk model and saves it to disk"""
    try:
        X, y = generate_synthetic_data(300)
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X, y)
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        logger.info(f"ML Risk model trained and saved to {MODEL_PATH}")
        return "Model trained successfully."
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return f"Error training model: {str(e)}"

def load_model() -> RandomForestClassifier:
    """Loads the trained ML model from disk, or returns None if not found"""
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            return model
        except Exception as e:
            logger.error(f"Error loading model from {MODEL_PATH}: {e}")
            return None
    return None

def predict_risk(
    invoice_amount: float,
    days_to_due: int,
    supplier_transaction_count: int,
    supplier_delay_count: int,
    buyer_transaction_count: int,
    buyer_average_delay: float,
    previous_default_count: int,
    financing_amount: float,
    tenure_days: int
) -> dict:
    """
    Predicts transaction risk using the ML model if available.
    If the model does not exist, falls back to a deterministic calculation.
    Returns:
        dict: containing risk_score, risk_level, risk_factors, and model_used
    """
    model = load_model()
    
    # Feature vector matching training structure
    features = [
        invoice_amount,
        days_to_due,
        supplier_transaction_count,
        supplier_delay_count,
        buyer_transaction_count,
        buyer_average_delay,
        previous_default_count,
        financing_amount,
        tenure_days
    ]
    
    model_used = "RandomForestClassifier (ML)"
    
    if model is not None:
        try:
            # Predict probability of class 1 (delayed/default)
            features_arr = np.array([features])
            prob_default = model.predict_proba(features_arr)[0][1]
            
            # Map 0.0 - 1.0 probability to a 0 - 100 risk score
            risk_score = round(prob_default * 100, 2)
        except Exception as e:
            logger.warning(f"Error executing ML model prediction: {e}. Using fallback.")
            risk_score = None
    else:
        risk_score = None
        
    # Deterministic fallback score calculation
    if risk_score is None:
        model_used = "Deterministic Prototype Fallback (Rule-Based)"
        
        # Base score starts at 15 (neutral)
        score = 15.0
        
        # 1. Defaults count - high impact
        score += previous_default_count * 20.0
        
        # 2. Buyer performance - medium impact
        if buyer_transaction_count > 0:
            delay_ratio = buyer_average_delay / 30.0  # Normalized up to 30 days
            score += min(delay_ratio * 15.0, 15.0)
        else:
            score += 5.0  # Cold start buyer
            
        # 3. Supplier performance - medium impact
        if supplier_transaction_count > 0:
            supplier_ratio = supplier_delay_count / supplier_transaction_count
            score += min(supplier_ratio * 15.0, 15.0)
        else:
            score += 5.0  # Cold start supplier
            
        # 4. Invoice details - lower impact
        # Large amounts slightly increase transaction size risk
        score += min((invoice_amount / 1000000.0) * 10.0, 10.0)
        
        # Shorter time to due date increases stress
        if days_to_due < 15:
            score += 15.0
        elif days_to_due < 30:
            score += 8.0
        elif days_to_due > 90:
            score += 3.0
            
        # Cap score between 0 and 100
        risk_score = float(round(max(0.0, min(100.0, score)), 2))

    # Risk level determination based on thresholds
    low_thresh = settings.RISK_THRESHOLD_LOW
    med_thresh = settings.RISK_THRESHOLD_MEDIUM
    
    if risk_score <= low_thresh:
        risk_level = "LOW"
    elif risk_score <= med_thresh:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    # Identify individual risk factors
    risk_factors = []
    if previous_default_count > 0:
        risk_factors.append(f"Supplier has {previous_default_count} historical default(s).")
    if buyer_average_delay > 10:
        risk_factors.append(f"Buyer has high average payment delay of {buyer_average_delay:.1f} days.")
    if supplier_transaction_count > 0 and (supplier_delay_count / supplier_transaction_count) > 0.2:
        risk_factors.append("Supplier has high payment delay frequency.")
    if invoice_amount > 500000:
        risk_factors.append("Large transaction amount increases concentration risk.")
    if days_to_due < 20:
        risk_factors.append("Short tenure (less than 20 days) leaves limited time for invoice processing.")

    if not risk_factors:
        risk_factors.append("No critical risk factors identified.")

    explanation = f"Risk score is {risk_score}% ({risk_level} Risk). Calculated using {model_used}."

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "explanation": explanation,
        "model_used": model_used
    }
