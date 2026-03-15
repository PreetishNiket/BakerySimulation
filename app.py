from flask import Flask, render_template, request, jsonify
import numpy as np

from brothaus_simulation import (
    get_default_params,
    simulate_day,
    run_monte_carlo,
    summarize_revenue,
)


app = Flask(__name__)


def _coerce_int(data: dict, key: str, default: int) -> int:
    raw = data.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _coerce_float(data: dict, key: str, default: float) -> float:
    raw = data.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _parse_probs(payload: dict, key: str, default: dict) -> dict:
    """Parse base_probs or promo_probs from payload. Expects {Pretzel: 50, Bread: 30, Cake: 20}."""
    raw = payload.get(key)
    if not raw or not isinstance(raw, dict):
        return dict(default)
    p = float(raw.get("Pretzel", 50)) / 100.0
    b = float(raw.get("Bread", 30)) / 100.0
    c = float(raw.get("Cake", 20)) / 100.0
    total = p + b + c
    if total <= 0:
        return dict(default)
    return {"Pretzel": p / total, "Bread": b / total, "Cake": c / total}


def _parse_prices(payload: dict, key: str, default: dict) -> dict:
    """Parse optional custom prices, fallback to defaults."""
    raw = payload.get(key)
    if not raw or not isinstance(raw, dict):
        return dict(default)
    prices = {}
    for product in ("Pretzel", "Bread", "Cake"):
        try:
            prices[product] = float(raw.get(product, default[product]))
        except (TypeError, ValueError, KeyError):
            prices[product] = float(default.get(product, 0.0))
    return prices


def build_params_from_payload(payload: dict) -> dict:
    """
    Build a simulation parameter dict from JSON payload.
    Falls back to get_default_params() for any missing/invalid fields.
    Supports: weather_cust_mult, holiday_cust_mult, holiday_rev_mult, base_probs, promo_probs.
    """
    base = get_default_params()

    opening = _coerce_int(payload, "opening_hour", base["opening_hour"])
    closing = _coerce_int(payload, "closing_hour", base["closing_hour"])
    if closing <= opening:
        closing = opening + 12

    avg_customers = _coerce_float(
        payload, "avg_customers_per_hour", base["avg_customers_per_hour"]
    )
    peak_start = _coerce_int(payload, "peak_start_hour", base["peak_start_hour"])
    peak_end = _coerce_int(payload, "peak_end_hour", base["peak_end_hour"])
    peak_mult = _coerce_float(payload, "peak_multiplier", base["peak_multiplier"])

    weather_cust = _coerce_float(payload, "weather_cust_mult", 1.0)
    holiday_cust = _coerce_float(payload, "holiday_cust_mult", 1.0)
    holiday_rev = _coerce_float(payload, "holiday_rev_mult", 1.0)
    extra_cust_mult = weather_cust * holiday_cust
    extra_rev_mult = holiday_rev

    base_probs = _parse_probs(payload, "base_probs", base["base_probs"])
    promo_probs = _parse_probs(payload, "promo_probs", base["promo_probs"])
    prices = _parse_prices(payload, "prices", base["prices"])

    hours_open = closing - opening
    peak_hour_indices = [
        h for h in range(hours_open)
        if peak_start <= (opening + h) < peak_end
    ]

    params = dict(base)
    params.update(
        opening_hour=opening,
        closing_hour=closing,
        hours_open=hours_open,
        avg_customers_per_hour=avg_customers,
        peak_hour_indices=peak_hour_indices,
        peak_start_hour=peak_start,
        peak_end_hour=peak_end,
        peak_multiplier=peak_mult,
        extra_cust_mult=extra_cust_mult,
        extra_rev_mult=extra_rev_mult,
        base_probs=base_probs,
        promo_probs=promo_probs,
        prices=prices,
    )
    return params


def _summary_to_json(summary: dict) -> dict:
    """
    Convert summarize_revenue() output into a JSON-serializable dict.
    """
    total_units_series = summary.get("total_units")
    total_units = (
        total_units_series.to_dict() if hasattr(total_units_series, "to_dict") else {}
    )
    return {
        "avg": float(summary.get("avg", 0.0)),
        "min": int(summary.get("min", 0)),
        "max": int(summary.get("max", 0)),
        "std": float(summary.get("std", 0.0)),
        "most_popular": str(summary.get("most_popular", "")),
        "total_units": total_units,
    }


@app.route("/")
def dashboard():
    """
    Render the BrotHaus interactive simulation dashboard.
    All heavy lifting is done via the /api/simulate endpoint.
    """
    defaults = get_default_params()
    return render_template("dashboard.html", defaults=defaults)


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """
    JSON API used by the dashboard to run simulations.

    Request JSON (all optional, defaults applied if missing):
    - opening_hour: int
    - closing_hour: int
    - avg_customers_per_hour: float
    - peak_start_hour: int
    - peak_end_hour: int
    - peak_multiplier: float
    """
    payload = request.get_json(silent=True) or {}

    # Base scenario: uses weather/holiday multipliers as given.
    base_params = build_params_from_payload(payload)

    # Promotion scenario assumptions:
    # - More customers because of the promotion (e.g. +25% traffic)
    # - Slightly higher average ticket size (e.g. +10% revenue per customer)
    promo_params = dict(base_params)
    base_extra_cust = base_params.get("extra_cust_mult", 1.0)
    base_extra_rev = base_params.get("extra_rev_mult", 1.0)
    promo_params["extra_cust_mult"] = base_extra_cust * 1.25
    promo_params["extra_rev_mult"] = base_extra_rev * 1.10

    # Single-day hourly view (no promotion vs promotion)
    hourly_base, _ = simulate_day(
        base_params, use_promotion=False, rng=np.random.default_rng(123)
    )
    hourly_promo, _ = simulate_day(
        promo_params, use_promotion=True, rng=np.random.default_rng(456)
    )

    # 100-day Monte Carlo
    daily_base = run_monte_carlo(
        base_params, n_days=100, use_promotion=False, seed=42
    )
    base_summary = summarize_revenue(daily_base)

    daily_promo = run_monte_carlo(
        promo_params, n_days=100, use_promotion=True, seed=42
    )
    promo_summary = summarize_revenue(daily_promo)

    response = {
        "config": {
            "opening_hour": base_params["opening_hour"],
            "closing_hour": base_params["closing_hour"],
            "hours_open": base_params["hours_open"],
            "avg_customers_per_hour": base_params["avg_customers_per_hour"],
            "peak_start_hour": base_params["peak_start_hour"],
            "peak_end_hour": base_params["peak_end_hour"],
            "peak_multiplier": base_params["peak_multiplier"],
            "extra_cust_mult_base": base_params.get("extra_cust_mult", 1.0),
            "extra_rev_mult_base": base_params.get("extra_rev_mult", 1.0),
            "extra_cust_mult_promo": promo_params.get("extra_cust_mult", 1.0),
            "extra_rev_mult_promo": promo_params.get("extra_rev_mult", 1.0),
        },
        "base": {
            "summary": _summary_to_json(base_summary),
            "daily": daily_base.to_dict(orient="records"),
            "hourly": hourly_base.to_dict(orient="records"),
        },
        "promo": {
            "summary": _summary_to_json(promo_summary),
            "daily": daily_promo.to_dict(orient="records"),
            "hourly": hourly_promo.to_dict(orient="records"),
        },
    }
    return jsonify(response)


if __name__ == "__main__":
    import os
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug)

