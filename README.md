# BrotHaus Sales Simulation (MBA Business Analytics Assignment)

This project simulates daily sales for a fictional German bakery, **BrotHaus**, to teach MBA-level Business Analytics concepts:

- demand simulation
- customer arrival modeling (Poisson process)
- stochastic processes
- revenue forecasting
- promotional effects
- Monte Carlo simulation
- simple data visualization for decision-making

## How to run

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies (with venv activated use `pip`, otherwise `pip3`):

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you get `BackendUnavailable` or build errors, upgrade pip first as above; the requirements use versions that have pre-built wheels.

3. Run the simulation script (console mode, optional):

```bash
python brothaus_simulation.py
```

**Input parameters:** When you run the script, it will prompt for key business parameters. You can customize:

- **Opening hour** and **closing hour** (e.g. 8 and 20 for 8 AM–8 PM)
- **Average customers per hour**
- **Peak period** (start and end clock hour) and **peak multiplier** (e.g. 1.4 for +40%)
- **Product prices** (Pretzel, Bread, Cake in INR)
- **Base and promotion purchase probabilities** (fractions that sum to 1)

Press **Enter** at any prompt to keep the default value shown in brackets.

**Non-interactive run (defaults only):**

```bash
python brothaus_simulation.py --defaults
```

This skips all prompts and runs with the built-in defaults (8 AM–8 PM, 15 customers/hour, peak 12–2 PM, etc.).

The script will:

- simulate one sample day (hourly table + total revenue),
- run a 100-day Monte Carlo simulation without promotion and with a Pretzel promotion,
- print key business insights to the console,
- save an HTML report with the current configuration (hours, peak, etc.).

4. Run the interactive web UI (recommended for sliders and live simulation):

```bash
python app.py
```

Then open `http://127.0.0.1:5000/` in your browser to adjust parameters via sliders and run simulations from the HTML page.

