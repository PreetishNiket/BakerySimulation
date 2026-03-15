import json
import numpy as np
import pandas as pd


# numpy  : random numbers and math (Poisson arrivals, random choices)
# pandas : tables (DataFrames) and aggregations


# Default business parameters (used when user presses Enter at prompts)
DEFAULT_OPENING_HOUR = 8
DEFAULT_CLOSING_HOUR = 20
DEFAULT_AVG_CUSTOMERS_PER_HOUR = 15
DEFAULT_BASE_PROBS = {"Pretzel": 0.50, "Bread": 0.30, "Cake": 0.20}
DEFAULT_PROMO_PROBS = {"Pretzel": 0.70, "Bread": 0.20, "Cake": 0.10}
DEFAULT_PRICES = {"Pretzel": 60, "Bread": 180, "Cake": 220}
DEFAULT_PEAK_START_HOUR = 12   # 12 PM (clock time)
DEFAULT_PEAK_END_HOUR = 14     # 2 PM (clock time; peak applies to 12 and 13)
DEFAULT_PEAK_MULTIPLIER = 1.40


def _parse_float(prompt: str, default: float) -> float:
    """Read a float from user input; use default if empty."""
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _parse_int(prompt: str, default: int) -> int:
    """Read an int from user input; use default if empty."""
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_simulation_params() -> dict:
    """
    Collect simulation parameters from user input.
    Press Enter to keep the default value for each parameter.
    Returns a dict with all parameters needed for simulate_day and run_monte_carlo.
    """
    print("\n--- BrotHaus Simulation – Input Parameters ---")
    print("(Press Enter to use the default value shown in brackets)\n")

    opening_hour = _parse_int(f"Opening hour (0–23) [{DEFAULT_OPENING_HOUR}]: ", DEFAULT_OPENING_HOUR)
    closing_hour = _parse_int(f"Closing hour (0–23, must be > opening) [{DEFAULT_CLOSING_HOUR}]: ", DEFAULT_CLOSING_HOUR)
    if closing_hour <= opening_hour:
        closing_hour = opening_hour + 12
        print(f"  Using closing_hour = {closing_hour} (invalid range corrected).")

    avg_customers = _parse_float(f"Average customers per hour [{DEFAULT_AVG_CUSTOMERS_PER_HOUR}]: ", DEFAULT_AVG_CUSTOMERS_PER_HOUR)
    peak_start = _parse_int(f"Peak period start (clock hour, e.g. 12 for noon) [{DEFAULT_PEAK_START_HOUR}]: ", DEFAULT_PEAK_START_HOUR)
    peak_end = _parse_int(f"Peak period end (clock hour, e.g. 14 for 2 PM) [{DEFAULT_PEAK_END_HOUR}]: ", DEFAULT_PEAK_END_HOUR)
    peak_mult = _parse_float(f"Peak hour customer multiplier (e.g. 1.4 = +40%) [{DEFAULT_PEAK_MULTIPLIER}]: ", DEFAULT_PEAK_MULTIPLIER)

    print("\nProduct prices (INR). Press Enter for default.")
    prices = {}
    for product, default_val in DEFAULT_PRICES.items():
        prices[product] = int(_parse_float(f"  Price for {product} [{default_val}]: ", default_val))

    print("\nBase purchase probabilities (fractions, must sum to 1). Press Enter for defaults.")
    base_probs = {}
    for product, default_val in DEFAULT_BASE_PROBS.items():
        base_probs[product] = _parse_float(f"  {product} [{default_val}]: ", default_val)
    promo_probs = {}
    for product, default_val in DEFAULT_PROMO_PROBS.items():
        promo_probs[product] = _parse_float(f"  Promo – {product} [{default_val}]: ", default_val)

    hours_open = closing_hour - opening_hour
    # Peak hour indices: hours (0..hours_open-1) whose clock time is in [peak_start, peak_end)
    peak_hour_indices = [
        h for h in range(hours_open)
        if peak_start <= (opening_hour + h) < peak_end
    ]

    params = {
        "opening_hour": opening_hour,
        "closing_hour": closing_hour,
        "hours_open": hours_open,
        "avg_customers_per_hour": avg_customers,
        "base_probs": base_probs,
        "promo_probs": promo_probs,
        "prices": prices,
        "peak_hour_indices": peak_hour_indices,
        "peak_start_hour": peak_start,
        "peak_end_hour": peak_end,
        "peak_multiplier": peak_mult,
    }
    print("\n--- Using parameters ---")
    print(f"  Hours: {opening_hour}:00 – {closing_hour}:00 ({hours_open} hours)")
    print(f"  Peak hours (clock): {peak_start}–{peak_end}, multiplier: {peak_mult}x")
    print()
    return params


def simulate_day(params: dict, use_promotion: bool = False, rng=None):
    """
    Simulate one full day of bakery operations using the given parameters.

    Parameters
    ----------
    params : dict
        From get_simulation_params(): opening_hour, hours_open, avg_customers_per_hour,
        base_probs, promo_probs, prices, peak_hour_indices, peak_multiplier.
    use_promotion : bool
        If True, use promo_probs; else base_probs.
    rng : np.random.Generator, optional
        Random number generator for reproducibility.

    Returns
    -------
    hourly_df : pd.DataFrame
        Hour-by-hour sales and revenue.
    totals : dict
        Aggregated totals for the day (revenue and units).
    """
    if rng is None:
        rng = np.random.default_rng()

    probs = params["promo_probs"] if use_promotion else params["base_probs"]
    opening_hour = params["opening_hour"]
    hours_open = params["hours_open"]
    prices = params["prices"]
    peak_indices = set(params["peak_hour_indices"])
    peak_mult = params["peak_multiplier"]

    hours = list(range(hours_open))
    hour_labels = [f"{opening_hour + h}:00" for h in hours]

    extra_cust_mult = params.get("extra_cust_mult", 1.0)
    extra_rev_mult = params.get("extra_rev_mult", 1.0)

    records = []
    for h, label in zip(hours, hour_labels):
        lam = params["avg_customers_per_hour"] * extra_cust_mult
        if h in peak_indices:
            lam *= peak_mult

        customers = rng.poisson(lam=lam)

        if customers > 0:
            choices = rng.choice(
                ["Pretzel", "Bread", "Cake"],
                size=customers,
                p=[probs["Pretzel"], probs["Bread"], probs["Cake"]],
            )
            pretzels = int(np.sum(choices == "Pretzel"))
            breads = int(np.sum(choices == "Bread"))
            cakes = int(np.sum(choices == "Cake"))
        else:
            pretzels = breads = cakes = 0

        pretzel_rev = pretzels * prices["Pretzel"] * extra_rev_mult
        bread_rev = breads * prices["Bread"] * extra_rev_mult
        cake_rev = cakes * prices["Cake"] * extra_rev_mult
        total_rev = pretzel_rev + bread_rev + cake_rev

        records.append(
            {
                "Hour_Index": h,
                "Hour": label,
                "Customers": customers,
                "Pretzel_Sales": pretzels,
                "Bread_Sales": breads,
                "Cake_Sales": cakes,
                "Pretzel_Revenue": pretzel_rev,
                "Bread_Revenue": bread_rev,
                "Cake_Revenue": cake_rev,
                "Total_Revenue": total_rev,
            }
        )

    hourly_df = pd.DataFrame(records)
    totals = {
        "Total_Revenue": int(hourly_df["Total_Revenue"].sum()),
        "Pretzel_Sales": int(hourly_df["Pretzel_Sales"].sum()),
        "Bread_Sales": int(hourly_df["Bread_Sales"].sum()),
        "Cake_Sales": int(hourly_df["Cake_Sales"].sum()),
        "Customers": int(hourly_df["Customers"].sum()),
    }
    return hourly_df, totals


def run_monte_carlo(
    params: dict,
    n_days: int = 100,
    use_promotion: bool = False,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Run Monte Carlo simulation of many days using the given parameters.
    """
    base_rng = np.random.default_rng(seed)
    results = []

    for day in range(1, n_days + 1):
        day_rng = np.random.default_rng(base_rng.integers(0, 10_000_000))
        _, totals = simulate_day(params, use_promotion=use_promotion, rng=day_rng)
        results.append(
            {
                "Day": day,
                "Total_Revenue": totals["Total_Revenue"],
                "Pretzel_Sales": totals["Pretzel_Sales"],
                "Bread_Sales": totals["Bread_Sales"],
                "Cake_Sales": totals["Cake_Sales"],
                "Customers": totals["Customers"],
            }
        )

    return pd.DataFrame(results)


def save_html_report(
    daily_base: pd.DataFrame,
    base_summary: dict,
    daily_promo: pd.DataFrame,
    promo_summary: dict,
    html_path: str = "brothaus_report.html",
    params: dict = None,
) -> None:
    """
    Generate a styled HTML report with key metrics and sample tables.
    If params is provided, report shows actual opening/closing hours from config.
    """
    if params is None:
        params = {}
    opening = params.get("opening_hour", DEFAULT_OPENING_HOUR)
    closing = params.get("closing_hour", DEFAULT_CLOSING_HOUR)
    hours_open = params.get("hours_open", closing - opening)
    peak_mult = params.get("peak_multiplier", DEFAULT_PEAK_MULTIPLIER)
    peak_start = params.get("peak_start_hour", DEFAULT_PEAK_START_HOUR)
    peak_end = params.get("peak_end_hour", DEFAULT_PEAK_END_HOUR)
    peak_str = f"{peak_start}–{peak_end}"
    # Compute pretzel share numbers for display
    base_units = base_summary["total_units"].sum()
    promo_units = promo_summary["total_units"].sum()
    base_pretzel_share = (
        base_summary["total_units"]["Pretzel_Sales"] / base_units if base_units > 0 else 0.0
    )
    promo_pretzel_share = (
        promo_summary["total_units"]["Pretzel_Sales"] / promo_units if promo_units > 0 else 0.0
    )

    # Build a 60-day combined revenue log:
    # - Days 1–60
    # - Normal days from daily_base
    # - Festival window (days 8–14) from daily_promo
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekend_mult = {"Sat": 1.4, "Sun": 1.5}

    rows = []
    for day in range(1, 61):
        idx = day - 1
        dow = dow_names[idx % 7]
        is_festival = 8 <= day <= 14
        mode = "Festival" if is_festival else ("Weekend" if dow in ("Sat", "Sun") else "Normal")
        lam_mult = weekend_mult.get(dow, 1.0)
        source = daily_promo if is_festival else daily_base
        # Guard in case there are fewer simulated days
        if idx >= len(source):
            break
        r = source.iloc[idx]
        rows.append(
            {
                "Day": day,
                "Weekday": dow,
                "Mode": mode,
                "Lambda_Mult": f"x{lam_mult:.1f}",
                "Customers": int(r.get("Customers", 0)),
                "Pretzel_Sales": int(r["Pretzel_Sales"]),
                "Bread_Sales": int(r["Bread_Sales"]),
                "Cake_Sales": int(r["Cake_Sales"]),
                "Revenue": int(r["Total_Revenue"]),
            }
        )

    log_df = pd.DataFrame(rows)
    # Nicely formatted revenue column
    log_df["Revenue_INR"] = log_df["Revenue"].apply(
        lambda v: f"₹{int(v):,}".replace(",", ",")
    )
    log_table = log_df[
        [
            "Day",
            "Weekday",
            "Mode",
            "Lambda_Mult",
            "Customers",
            "Pretzel_Sales",
            "Bread_Sales",
            "Cake_Sales",
            "Revenue_INR",
        ]
    ].to_html(index=False, classes="tbl full-log", border=0)

    # Data for interactive charts (converted to JSON)
    days = daily_base["Day"].tolist()
    base_revenue = daily_base["Total_Revenue"].tolist()
    promo_revenue = daily_promo["Total_Revenue"].tolist()

    base_unit_totals = {
        "Pretzel": int(base_summary["total_units"]["Pretzel_Sales"]),
        "Bread": int(base_summary["total_units"]["Bread_Sales"]),
        "Cake": int(base_summary["total_units"]["Cake_Sales"]),
    }
    promo_unit_totals = {
        "Pretzel": int(promo_summary["total_units"]["Pretzel_Sales"]),
        "Bread": int(promo_summary["total_units"]["Bread_Sales"]),
        "Cake": int(promo_summary["total_units"]["Cake_Sales"]),
    }

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BrotHaus Sales Simulation Report</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <style>
    *,*::before,*::after {{ box-sizing:border-box;margin:0;padding:0; }}
    :root {{
      --p1:#4da3ff; --p2:#2b6cb0; --p3:#1a4f80;
      --soft:#e3f2ff; --mid:#b3d4ff; --light:#f4f9ff;
      --white:#ffffff; --text:#12324b; --muted:#6a8bad; --faint:#d4e6ff;
    }}
    body {{
      background:var(--light);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      color:var(--text);
      min-height:100vh;
      padding-bottom:80px;
    }}
    header {{
      background:linear-gradient(135deg,#a0c4ff 0%,#4da3ff 45%,#e3f2ff 100%);
      padding:40px 24px 32px;
      text-align:center;
      position:relative;
      overflow:hidden;
    }}
    .blob {{ position:absolute;border-radius:50%;pointer-events:none; }}
    .hinner {{ position:relative;z-index:1; }}
    .hemoji {{ font-size:3.2rem;display:block;margin-bottom:8px; }}
    header h1 {{
      font-size:clamp(2rem,5vw,3rem);
      color:#fff;
      line-height:1.05;
      text-shadow:0 3px 14px rgba(18,50,75,0.35);
    }}
    header p {{ color:rgba(255,255,255,0.9);font-weight:600;font-size:14px;margin-top:8px; }}
    .chip {{
      display:inline-block;
      margin-top:10px;
      padding:6px 14px;
      border-radius:999px;
      background:rgba(0,0,0,0.18);
      color:#fff;
      font-size:11px;
      font-weight:700;
      letter-spacing:.08em;
      text-transform:uppercase;
    }}
    .wrap {{ max-width:1120px;margin:0 auto;padding:32px 18px 40px; }}
    .sec-title {{
      font-size:1.3rem;
      font-weight:800;
      color:var(--p2);
      margin-bottom:18px;
      display:flex;
      align-items:center;
      gap:10px;
    }}
    .sec-title span {{ font-size:1.5rem; }}
    .cards3 {{
      display:grid;
      grid-template-columns:repeat(3,1fr);
      gap:16px;
      margin-bottom:26px;
    }}
    .card {{
      background:var(--white);
      border-radius:18px;
      padding:18px 18px 16px;
      border:2px solid var(--faint);
      box-shadow:0 6px 22px rgba(77,163,255,0.18);
    }}
    .pill-label {{
      font-size:11px;
      font-weight:800;
      letter-spacing:.12em;
      text-transform:uppercase;
      color:var(--muted);
      margin-bottom:6px;
    }}
    .pill-val {{
      font-size:1.7rem;
      font-weight:800;
      color:var(--p3);
      line-height:1.1;
    }}
    .pill-sub {{ font-size:12px;font-weight:600;color:var(--muted);margin-top:4px; }}
    .cmp-wrap {{
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:16px;
      margin-bottom:28px;
    }}
    .cmp-box {{
      border-radius:18px;
      padding:18px 18px 14px;
      border:2px solid var(--faint);
      background:linear-gradient(135deg,#f4f9ff,#fff);
    }}
    .cmp-box.promo {{ background:linear-gradient(135deg,rgba(77,163,255,.12),rgba(179,212,255,.3)); }}
    .cmp-head {{ font-weight:800;color:var(--p2);margin-bottom:10px;font-size:1.05rem; }}
    .cmp-row {{
      display:flex;
      justify-content:space-between;
      align-items:center;
      margin-bottom:6px;
      font-size:13px;
    }}
    .cmp-key {{ font-weight:600;color:var(--muted); }}
    .cmp-v {{ font-weight:800;color:var(--text); }}
    .tbl-wrap {{ overflow-x:auto;margin-bottom:26px; }}
    table.tbl {{ width:100%;border-collapse:collapse;font-size:12px; }}
    table.tbl thead tr {{ background:linear-gradient(90deg,var(--p1),var(--mid));color:#fff; }}
    table.tbl th,table.tbl td {{ padding:8px 10px;border-bottom:1px solid var(--faint);text-align:left;white-space:nowrap; }}
    table.tbl tbody tr:nth-child(even) {{ background:#fff9fb; }}
    table.tbl tbody tr:nth-child(odd) {{ background:var(--white); }}
    .insight {{
      background:linear-gradient(135deg,var(--p1),var(--p2));
      color:#fff;
      border-radius:18px;
      padding:20px 22px;
      margin-bottom:26px;
    }}
    .insight-title {{ font-weight:800;font-size:1.1rem;margin-bottom:10px; }}
    .insight ul {{ margin-left:18px;font-size:13px;line-height:1.7; }}
    footer {{
      text-align:center;
      margin-top:36px;
      font-size:11px;
      font-weight:700;
      letter-spacing:.1em;
      text-transform:uppercase;
      color:#9abff0;
    }}
    @media(max-width:720px) {{
      .cards3,.cmp-wrap {{ grid-template-columns:1fr; }}
    }}
  </style>
</head>
</html>
<body>
  <header>
    <div class="blob" style="top:-20px;left:-20px;width:130px;height:130px;background:rgba(255,255,255,0.18)"></div>
    <div class="blob" style="top:8px;right:-30px;width:170px;height:170px;background:rgba(255,255,255,0.12)"></div>
    <div class="blob" style="bottom:-26px;left:32%;width:110px;height:110px;background:rgba(255,255,255,0.15)"></div>
    <div class="hinner">
      <span class="hemoji">🥐</span>
      <h1>BrotHaus Bakery · Sales Simulation</h1>
      <p>Poisson arrivals · 100-day Monte Carlo · Pretzel Festival Promotion</p>
      <div class="chip">Open {opening}:00 – {closing}:00 ({hours_open} h) · Peak {peak_str} · INR</div>
    </div>
  </header>

  <div class="wrap">
    <div class="sec-title"><span>📌</span>Executive Snapshot</div>
    <div class="cards3">
      <div class="card">
        <div class="pill-label">Avg Daily Revenue (No Promo)</div>
        <div class="pill-val">₹{base_summary['avg']:,.0f}</div>
        <div class="pill-sub">Range ₹{base_summary['min']:,.0f} – ₹{base_summary['max']:,.0f}</div>
      </div>
      <div class="card">
        <div class="pill-label">Avg Daily Revenue (Promotion)</div>
        <div class="pill-val">₹{promo_summary['avg']:,.0f}</div>
        <div class="pill-sub">Range ₹{promo_summary['min']:,.0f} – ₹{promo_summary['max']:,.0f}</div>
      </div>
      <div class="card">
        <div class="pill-label">Pretzel Share of Units</div>
        <div class="pill-val">{base_pretzel_share:.1%} → {promo_pretzel_share:.1%}</div>
        <div class="pill-sub">No promo → with Pretzel Festival</div>
      </div>
    </div>

    <div class="sec-title"><span>📊</span>Revenue & Mix Comparison</div>
    <div class="cmp-wrap">
      <div class="cmp-box">
        <div class="cmp-head">Normal Operations</div>
        <div class="cmp-row">
          <div class="cmp-key">Expected daily revenue</div>
          <div class="cmp-v">₹{base_summary['avg']:,.0f}</div>
        </div>
        <div class="cmp-row">
          <div class="cmp-key">Revenue standard deviation</div>
          <div class="cmp-v">₹{base_summary['std']:,.0f}</div>
        </div>
        <div class="cmp-row">
          <div class="cmp-key">Most popular product</div>
          <div class="cmp-v">{base_summary['most_popular']}</div>
        </div>
      </div>
      <div class="cmp-box promo">
        <div class="cmp-head">Pretzel Festival Promotion</div>
        <div class="cmp-row">
          <div class="cmp-key">Expected daily revenue</div>
          <div class="cmp-v">₹{promo_summary['avg']:,.0f}</div>
        </div>
        <div class="cmp-row">
          <div class="cmp-key">Revenue standard deviation</div>
          <div class="cmp-v">₹{promo_summary['std']:,.0f}</div>
        </div>
        <div class="cmp-row">
          <div class="cmp-key">Most popular product</div>
          <div class="cmp-v">{promo_summary['most_popular']}</div>
        </div>
      </div>
    </div>

    <div class="sec-title"><span>🕒</span>Simulation Setup</div>
    <div class="card" style="margin-bottom:26px;">
      <div class="pill-label" style="margin-bottom:6px;">Run Configuration</div>
      <div style="font-size:13px;font-weight:600;color:var(--muted);line-height:1.7;">
        1. <strong>Bakery Operating Hours:</strong> {opening}:00 – {closing}:00 ({hours_open} hours of trading)<br/>
        2. <strong>Pretzel Festival:</strong> days 8 to 14 in the 60-day horizon<br/>
        3. <strong>Weekend Effect:</strong> every Saturday (+40% λ) and Sunday (+50% λ)<br/>
        4. <strong>60-Day Revenue Simulation:</strong> Monte Carlo engine with Poisson arrivals and product choice probabilities
      </div>
    </div>

    <div class="sec-title"><span>📈</span>60-Day Revenue Simulation</div>
    <div class="card" style="margin-bottom:26px;">
      <div class="pill-label" style="margin-bottom:10px;">Daily Revenue – No Promotion vs Promotion</div>
      <canvas id="revenueTrendChart" height="120"></canvas>
    </div>

    <div class="card" style="margin-bottom:26px;">
      <div class="pill-label" style="margin-bottom:10px;">Product Mix – Units Sold</div>
      <div style="display:flex;flex-wrap:wrap;gap:20px;justify-content:space-between;">
        <div style="flex:1;min-width:240px;">
          <div style="font-size:12px;font-weight:700;color:var(--muted);margin-bottom:6px;">No Promotion</div>
          <canvas id="mixBaseChart" height="160"></canvas>
        </div>
        <div style="flex:1;min-width:240px;">
          <div style="font-size:12px;font-weight:700;color:var(--muted);margin-bottom:6px;">With Pretzel Festival</div>
          <canvas id="mixPromoChart" height="160"></canvas>
        </div>
      </div>
    </div>

    <div class="sec-title"><span>📋</span>Revenue Breakdown by Day Type</div>
    <div class="tbl-wrap">
      {log_table}
    </div>
  </div>

  <footer>🥐 BrotHaus Bakery · Monte Carlo Sales Simulation · Poisson Arrivals · Peak Hours · Promotions</footer>

  <script>
    const DAYS = {json.dumps(days)};
    const BASE_REV = {json.dumps(base_revenue)};
    const PROMO_REV = {json.dumps(promo_revenue)};
    const BASE_UNITS = {json.dumps(base_unit_totals)};
    const PROMO_UNITS = {json.dumps(promo_unit_totals)};

    function makeRevenueTrendChart() {{
      const ctx = document.getElementById('revenueTrendChart');
      if (!ctx) return;
      new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: DAYS,
          datasets: [
            {{
              label: 'No Promotion',
              data: BASE_REV,
              borderColor: '#2b6cb0',
              backgroundColor: 'rgba(43,108,176,0.1)',
              tension: 0.25,
              pointRadius: 2,
            }},
            {{
              label: 'Pretzel Festival',
              data: PROMO_REV,
              borderColor: '#63b3ed',
              backgroundColor: 'rgba(99,179,237,0.1)',
              tension: 0.25,
              pointRadius: 2,
            }}
          ]
        }},
        options: {{
          responsive: true,
          interaction: {{ mode: 'index', intersect: false }},
          plugins: {{
            legend: {{ display: true }},
            tooltip: {{
              callbacks: {{
                label: (ctx) => ' ' + ctx.dataset.label + ': ₹' + Math.round(ctx.parsed.y).toLocaleString('en-IN')
              }}
            }}
          }},
          scales: {{
            y: {{
              ticks: {{
                callback: (v) => '₹' + v.toLocaleString('en-IN')
              }}
            }}
          }}
        }}
      }});
    }}

    function makeMixChart(canvasId, units) {{
      const ctx = document.getElementById(canvasId);
      if (!ctx) return;
      const labels = Object.keys(units);
      const data = labels.map(k => units[k]);
      new Chart(ctx, {{
        type: 'doughnut',
        data: {{
          labels,
          datasets: [{{
            data,
            backgroundColor: ['#3182ce','#63b3ed','#90cdf4'],
            borderColor: '#ffffff',
            borderWidth: 2,
          }}]
        }},
        options: {{
          plugins: {{
            legend: {{ position: 'bottom' }},
            tooltip: {{
              callbacks: {{
                label: (ctx) => ' ' + ctx.label + ': ' + ctx.parsed + ' units'
              }}
            }}
          }},
          cutout: '60%'
        }}
      }});
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      makeRevenueTrendChart();
      makeMixChart('mixBaseChart', BASE_UNITS);
      makeMixChart('mixPromoChart', PROMO_UNITS);
    }});
  </script>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


def summarize_revenue(daily_df: pd.DataFrame) -> dict:
    avg = float(daily_df["Total_Revenue"].mean())
    min_rev = int(daily_df["Total_Revenue"].min())
    max_rev = int(daily_df["Total_Revenue"].max())
    std_rev = float(daily_df["Total_Revenue"].std())

    total_units = daily_df[["Pretzel_Sales", "Bread_Sales", "Cake_Sales"]].sum()
    most_popular = total_units.idxmax()

    return {
        "avg": avg,
        "min": min_rev,
        "max": max_rev,
        "std": std_rev,
        "most_popular": most_popular,
        "total_units": total_units,
    }


def print_insights(label: str, summary: dict) -> None:
    print(f"\n=== Business Insights – {label} ===")
    print(f"Expected (Average) Daily Revenue: ₹{summary['avg']:,.0f}")
    print(f"Most Popular Product: {summary['most_popular']}")
    print(f"Revenue Range: ₹{summary['min']:,.0f} – ₹{summary['max']:,.0f}")
    print(f"Revenue Standard Deviation: ₹{summary['std']:,.0f}")
    print("\nUnits sold over all simulated days:")
    for product, units in summary["total_units"].items():
        print(f"  {product}: {units:,} units")


def main():
    # Get all simulation parameters from user (Enter = use defaults)
    params = get_simulation_params()

    print("Simulating a single day without promotion...")
    hourly_df, totals = simulate_day(params, use_promotion=False, rng=np.random.default_rng(123))

    print("\nSample of hourly data:")
    print(
        hourly_df[
            [
                "Hour",
                "Customers",
                "Pretzel_Sales",
                "Bread_Sales",
                "Cake_Sales",
                "Total_Revenue",
            ]
        ].head()
    )

    print("\nTotal daily revenue (no promotion): "
          f"₹{totals['Total_Revenue']:,.0f}")

    daily_base = run_monte_carlo(params, n_days=100, use_promotion=False, seed=42)
    base_summary = summarize_revenue(daily_base)

    daily_promo = run_monte_carlo(params, n_days=100, use_promotion=True, seed=42)
    promo_summary = summarize_revenue(daily_promo)

    print_insights("No Promotion", base_summary)
    print_insights("With Pretzel Promotion", promo_summary)

    delta_avg = promo_summary["avg"] - base_summary["avg"]
    pretzel_share_base = (
        base_summary["total_units"]["Pretzel_Sales"] /
        base_summary["total_units"].sum()
    )
    pretzel_share_promo = (
        promo_summary["total_units"]["Pretzel_Sales"] /
        promo_summary["total_units"].sum()
    )

    print("\n=== Promotion Impact Summary ===")
    print(f"Change in Average Daily Revenue with Promotion: "
          f"₹{delta_avg:,.0f} per day")
    print(f"Pretzel Share of Units (No Promotion): {pretzel_share_base:.1%}")
    print(f"Pretzel Share of Units (With Promotion): {pretzel_share_promo:.1%}")

    # Save HTML report with current config (hours, etc.)
    save_html_report(daily_base, base_summary, daily_promo, promo_summary, params=params)
    print("\nHTML report saved as 'brothaus_report.html' in the current folder.")


def get_default_params() -> dict:
    """Return default simulation parameters (no user input). Use for scripting or --defaults."""
    opening_hour = DEFAULT_OPENING_HOUR
    closing_hour = DEFAULT_CLOSING_HOUR
    hours_open = closing_hour - opening_hour
    peak_start = DEFAULT_PEAK_START_HOUR
    peak_end = DEFAULT_PEAK_END_HOUR
    peak_hour_indices = [
        h for h in range(hours_open)
        if peak_start <= (opening_hour + h) < peak_end
    ]
    return {
        "opening_hour": opening_hour,
        "closing_hour": closing_hour,
        "hours_open": hours_open,
        "avg_customers_per_hour": DEFAULT_AVG_CUSTOMERS_PER_HOUR,
        "base_probs": dict(DEFAULT_BASE_PROBS),
        "promo_probs": dict(DEFAULT_PROMO_PROBS),
        "prices": dict(DEFAULT_PRICES),
        "peak_hour_indices": peak_hour_indices,
        "peak_start_hour": peak_start,
        "peak_end_hour": peak_end,
        "peak_multiplier": DEFAULT_PEAK_MULTIPLIER,
        "extra_cust_mult": 1.0,
        "extra_rev_mult": 1.0,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1].strip().lower() in ("--defaults", "-d"):
        # Non-interactive: use defaults without prompting
        _params = get_default_params()
        print("Using default parameters (no input).")
        print(f"  Hours: {_params['opening_hour']}:00 – {_params['closing_hour']}:00 ({_params['hours_open']} h)")
        print()

        def _main_with_params():
            params = _params
            print("Simulating a single day without promotion...")
            hourly_df, totals = simulate_day(params, use_promotion=False, rng=np.random.default_rng(123))
            print("\nSample of hourly data:")
            print(hourly_df[["Hour", "Customers", "Pretzel_Sales", "Bread_Sales", "Cake_Sales", "Total_Revenue"]].head())
            print("\nTotal daily revenue (no promotion):", f"₹{totals['Total_Revenue']:,.0f}")
            daily_base = run_monte_carlo(params, n_days=100, use_promotion=False, seed=42)
            base_summary = summarize_revenue(daily_base)
            daily_promo = run_monte_carlo(params, n_days=100, use_promotion=True, seed=42)
            promo_summary = summarize_revenue(daily_promo)
            print_insights("No Promotion", base_summary)
            print_insights("With Pretzel Promotion", promo_summary)
            delta_avg = promo_summary["avg"] - base_summary["avg"]
            pretzel_share_base = base_summary["total_units"]["Pretzel_Sales"] / base_summary["total_units"].sum()
            pretzel_share_promo = promo_summary["total_units"]["Pretzel_Sales"] / promo_summary["total_units"].sum()
            print("\n=== Promotion Impact Summary ===")
            print(f"Change in Average Daily Revenue with Promotion: ₹{delta_avg:,.0f} per day")
            print(f"Pretzel Share of Units (No Promotion): {pretzel_share_base:.1%}")
            print(f"Pretzel Share of Units (With Promotion): {pretzel_share_promo:.1%}")
            save_html_report(daily_base, base_summary, daily_promo, promo_summary, params=params)
            print("\nHTML report saved as 'brothaus_report.html' in the current folder.")

        _main_with_params()
    else:
        main()


