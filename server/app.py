"""Flask application for QuantLab's stock and option models."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import numpy as np
from flask import Flask, jsonify, render_template, request

try:  # Supports both `python server/app.py` and `flask --app server.app run`.
    from . import bsm_stocks, price_option_mcs, sim_stock
    from .stock_catalog import get_catalog
except ImportError:
    import bsm_stocks
    import price_option_mcs
    import sim_stock
    from stock_catalog import get_catalog


HORIZONS = {"1w", "1m", "3m", "6m", "1y"}
OPTION_TYPES = {"call", "put"}
MIN_SIMULATIONS, MAX_SIMULATIONS = 10_000, 1_000_000


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    @app.get("/")
    def simulation_page():
        return render_template("simulation.html")

    @app.get("/options")
    def options_page():
        return render_template("options.html")

    @app.get("/api/stocks")
    def stocks():
        return jsonify(get_catalog())

    @app.post("/api/simulations")
    def simulations():
        data = _payload(request.get_json(silent=True))
        ticker, horizon, count = _simulation_inputs(data)
        path_count = _integer(data.get("pathCount", 20), "pathCount", 1, 100)
        # These functions have no shared calculation hook, so execute their two
        # independent simulations concurrently without changing their API.
        with ThreadPoolExecutor(max_workers=2) as pool:
            terminal_future = pool.submit(sim_stock.sim_stock_terminal, ticker, horizon, count)
            paths_future = pool.submit(sim_stock.sim_stock_paths, ticker, horizon, count)
            terminal = np.asarray(terminal_future.result(), dtype=float)
            dates, paths = paths_future.result()
        bins = min(80, max(20, int(np.sqrt(count))))
        frequencies, edges = np.histogram(terminal, bins=bins)
        return jsonify({
            "ticker": ticker, "horizon": horizon, "simulations": count,
            "histogram": {"edges": edges.tolist(), "frequencies": frequencies.tolist()},
            "paths": {"dates": [date.isoformat() for date in dates], "values": np.asarray(paths)[:, :path_count].tolist()},
            "summary": {"mean": float(terminal.mean()), "median": float(np.median(terminal)), "p05": float(np.percentile(terminal, 5)), "p95": float(np.percentile(terminal, 95))},
        })

    @app.post("/api/options/bsm")
    def bsm_price():
        ticker, strike, horizon, option_type = _option_inputs(_payload(request.get_json(silent=True)))
        return jsonify({"ticker": ticker, "result": _finite_dict(bsm_stocks.price_option_bsm(ticker, strike, horizon, option_type))})

    @app.post("/api/options/mcs")
    def mcs_price():
        data = _payload(request.get_json(silent=True))
        ticker, strike, horizon, option_type = _option_inputs(data)
        count = _integer(data.get("numSim"), "numSim", MIN_SIMULATIONS, MAX_SIMULATIONS)
        bsm = bsm_stocks.price_option_bsm(ticker, strike, horizon, option_type)
        mcs = price_option_mcs.price_option(ticker, strike, horizon, option_type, count)
        return jsonify({"ticker": ticker, "bsm": _finite_dict(bsm), "monteCarlo": float(mcs), "simulations": count})

    @app.post("/api/options/comparison")
    def option_comparison():
        ticker, strike, horizon, option_type = _option_inputs(_payload(request.get_json(silent=True)))
        bsm = bsm_stocks.price_option_bsm(ticker, strike, horizon, option_type)
        counts = [10_000, *range(60_000, 1_000_000, 50_000), 1_000_000]
        prices = [price_option_mcs.price_option(ticker, strike, horizon, option_type, n) for n in counts]
        return jsonify({"bsm": _finite_dict(bsm), "simulations": counts, "prices": [float(price) for price in prices]})

    @app.errorhandler(ValueError)
    def invalid_input(error: ValueError):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(Exception)
    def calculation_failure(error: Exception):
        app.logger.exception("QuantLab calculation failed")
        return jsonify({"error": "Unable to retrieve market data or complete the calculation. Please try again."}), 502

    return app


def _payload(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("A JSON request body is required.")
    return data


def _ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if not ticker or len(ticker) > 20 or not all(char.isalnum() or char in ".-^" for char in ticker):
        raise ValueError("Select a valid stock ticker.")
    return ticker


def _integer(value: object, field: str, lower: int, upper: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an integer.") from None
    if not lower <= result <= upper:
        raise ValueError(f"{field} must be between {lower:,} and {upper:,}.")
    return result


def _simulation_inputs(data: dict) -> tuple[str, str, int]:
    horizon = data.get("horizon")
    if horizon not in HORIZONS:
        raise ValueError("Select a valid time horizon.")
    return _ticker(data.get("ticker")), horizon, _integer(data.get("numSim"), "numSim", MIN_SIMULATIONS, MAX_SIMULATIONS)


def _option_inputs(data: dict) -> tuple[str, float, str, str]:
    ticker = _ticker(data.get("ticker"))
    try:
        strike = float(data.get("strike"))
    except (TypeError, ValueError):
        raise ValueError("Strike must be a number.") from None
    if not np.isfinite(strike) or strike <= 0:
        raise ValueError("Strike must be a positive number.")
    horizon = data.get("horizon")
    option_type = data.get("optionType")
    if horizon not in HORIZONS or option_type not in OPTION_TYPES:
        raise ValueError("Select a valid horizon and option type.")
    return ticker, strike, horizon, option_type


def _finite_dict(values: dict[str, float]) -> dict[str, float]:
    return {key: float(value) for key, value in values.items() if np.isfinite(value)}


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
