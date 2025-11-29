"""
Betting Models Configuration

Defines different betting model strategies and their rules.
Each model can have different:
- Bet sizing rules
- Filtering rules (what plays to take)
- Display settings

Model IDs:
- pulsar_v1: Original model - flat $10 bets, z-score > 0.5 threshold
- sentinel_v1: Conservative model - variable sizing, UNDER restrictions
"""


# Model definitions
MODELS = {
    'pulsar_v1': {
        'id': 'pulsar_v1',
        'display_name': 'Pulsar 1.0',
        'short_name': 'Pulsar',
        'description': 'Original model: 50% season avg + 50% L5, bet toward Vegas line movement',
        'color': '#00ff88',  # Green
        'icon': '⚡',
        'default_bet': 10.0,
        'active': True,
    },
    'sentinel_v1': {
        'id': 'sentinel_v1',
        'display_name': 'Sentinel 1.0',
        'short_name': 'Sentinel',
        'description': 'Conservative model: Variable bet sizing, UNDER restrictions',
        'color': '#a78bfa',  # Purple
        'icon': '🛡️',
        'default_bet': 10.0,  # Base bet, varies by confidence
        'active': True,
    },
}

# Default model
DEFAULT_MODEL = 'pulsar_v1'


def get_model_config(model_id):
    """Get configuration for a specific model"""
    return MODELS.get(model_id, MODELS[DEFAULT_MODEL])


def get_all_models():
    """Get all active models"""
    return {k: v for k, v in MODELS.items() if v.get('active', True)}


def get_model_display_name(model_id):
    """Get display name for a model"""
    config = get_model_config(model_id)
    return config.get('display_name', model_id)


def z_score_to_confidence_pct(z_score):
    """
    Convert z-score to confidence percentage (0-100)

    |z| = 0.5 → 60%
    |z| = 1.0 → 70%
    |z| = 1.5 → 80%
    |z| = 2.0 → 90%
    |z| = 2.5+ → 95%+
    """
    if z_score is None:
        return 50

    abs_z = abs(z_score)
    # Linear mapping: 50% base + 20% per z-score unit
    confidence = 50 + (abs_z * 20)
    # Cap at 99%
    return min(confidence, 99)


class PulsarV1Model:
    """
    Pulsar 1.0 - Original betting model

    Rules:
    - Flat $10 bets
    - Takes all plays with z-score > 0.5 (Medium confidence)
    - Takes all plays with z-score > 1.0 (High confidence)
    - No special filtering
    """

    MODEL_ID = 'pulsar_v1'

    @staticmethod
    def should_take_play(analysis):
        """
        Determine if this model should take the play

        Args:
            analysis: dict with z_score, recommendation, stat_type, confidence

        Returns:
            (should_take: bool, bet_amount: float, reason: str)
        """
        z_score = analysis.get('z_score', 0)
        recommendation = analysis.get('recommendation', 'NO PLAY')

        # No play threshold
        if abs(z_score) < 0.5:
            return False, 0, "Z-score below threshold (< 0.5)"

        if recommendation == 'NO PLAY':
            return False, 0, "No recommendation"

        # Flat $10 bet for all plays
        return True, 10.0, "Standard play"

    @staticmethod
    def get_confidence_label(z_score):
        """Get confidence label (High/Medium) based on z-score"""
        abs_z = abs(z_score) if z_score else 0
        if abs_z >= 1.0:
            return "High"
        elif abs_z >= 0.5:
            return "Medium"
        return "N/A"


class SentinelV1Model:
    """
    Sentinel 1.0 - Conservative betting model

    Changes from Pulsar:
    1. Variable bet sizing by confidence:
       - 80%+ confidence → $20
       - 75-80% confidence → $15
       - 60-74% confidence → $10

    2. UNDER restrictions:
       - No UNDER bets below 75% confidence

    3. Stat-type restrictions:
       - No PTS UNDER below 70% confidence
       - No REB UNDER below 70% confidence
    """

    MODEL_ID = 'sentinel_v1'

    @staticmethod
    def should_take_play(analysis):
        """
        Determine if this model should take the play

        Args:
            analysis: dict with z_score, recommendation, stat_type, confidence

        Returns:
            (should_take: bool, bet_amount: float, reason: str)
        """
        z_score = analysis.get('z_score', 0)
        recommendation = analysis.get('recommendation', 'NO PLAY')
        stat_type = analysis.get('stat_type', '')

        if recommendation == 'NO PLAY':
            return False, 0, "No recommendation"

        # Calculate confidence percentage
        confidence_pct = z_score_to_confidence_pct(z_score)

        # Base threshold - still need z-score > 0.5 (which is ~60% confidence)
        if abs(z_score) < 0.5:
            return False, 0, "Z-score below threshold (< 0.5)"

        # === UNDER RESTRICTIONS ===
        if recommendation == 'UNDER':
            # Rule 2: No UNDER bets below 75% confidence
            if confidence_pct < 75:
                return False, 0, f"UNDER below 75% confidence ({confidence_pct:.0f}%)"

            # Rule 3a: No PTS UNDER below 70% confidence
            if stat_type == 'PTS' and confidence_pct < 70:
                return False, 0, f"PTS UNDER below 70% confidence ({confidence_pct:.0f}%)"

            # Rule 3b: No REB UNDER below 70% confidence
            if stat_type == 'REB' and confidence_pct < 70:
                return False, 0, f"REB UNDER below 70% confidence ({confidence_pct:.0f}%)"

        # === BET SIZING BY CONFIDENCE ===
        # Rule 1: Variable bet sizing
        if confidence_pct >= 80:
            bet_amount = 20.0
            reason = f"High confidence ({confidence_pct:.0f}%) - $20 bet"
        elif confidence_pct >= 75:
            bet_amount = 15.0
            reason = f"Medium-high confidence ({confidence_pct:.0f}%) - $15 bet"
        else:
            bet_amount = 10.0
            reason = f"Standard confidence ({confidence_pct:.0f}%) - $10 bet"

        return True, bet_amount, reason

    @staticmethod
    def get_confidence_label(z_score):
        """Get confidence label based on z-score"""
        abs_z = abs(z_score) if z_score else 0
        if abs_z >= 1.0:
            return "High"
        elif abs_z >= 0.5:
            return "Medium"
        return "N/A"


# Model class registry
MODEL_CLASSES = {
    'pulsar_v1': PulsarV1Model,
    'sentinel_v1': SentinelV1Model,
}


def get_model_class(model_id):
    """Get the model class for a given model ID"""
    return MODEL_CLASSES.get(model_id, PulsarV1Model)


def apply_model_rules(model_id, analysis):
    """
    Apply a model's rules to an analysis

    Args:
        model_id: str - the model identifier
        analysis: dict - the prop analysis data

    Returns:
        (should_take: bool, bet_amount: float, reason: str, confidence: str)
    """
    model_class = get_model_class(model_id)
    should_take, bet_amount, reason = model_class.should_take_play(analysis)
    confidence = model_class.get_confidence_label(analysis.get('z_score', 0))

    return should_take, bet_amount, reason, confidence
