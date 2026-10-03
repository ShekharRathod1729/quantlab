"""Flask application for QuantLab's stock and option models."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.exceptions import HTTPException

try:  # Supports both `python server/app.py` and `flask --app server.app run`.
    from . import bsm_stocks, markowitz, price_option_mcs, risk_analytics, sim_stock
    from .stock_catalog import get_catalog
    from .models import PortfolioHolding, User, db
except ImportError:
    import bsm_stocks
    import markowitz
    import price_option_mcs
    import risk_analytics
    import sim_stock
    from stock_catalog import get_catalog
    from models import PortfolioHolding, User, db


HORIZONS = {"1w", "1m", "3m", "6m", "1y"}
OPTION_TYPES = {"call", "put"}
MIN_SIMULATIONS, MAX_SIMULATIONS = 10_000, 1_000_000


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # ── Authentication & database configuration ──────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "quantlab-dev-key-change-in-production")
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quantlab.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = "login_page"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ------------------------------------------------------------------ #
    #  Authentication                                                      #
    # ------------------------------------------------------------------ #

    @app.get("/register")
    def register_page():
        if current_user.is_authenticated:
            return redirect(url_for("simulation_page"))
        return render_template("register.html")

    @app.post("/register")
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("simulation_page"))
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        errors = []
        if not username or len(username) < 3 or len(username) > 40:
            errors.append("Username must be 3–40 characters.")
        if not email or "@" not in email:
            errors.append("Enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is already taken.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with that email already exists.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html"), 400
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Welcome to QuantLab, {username}!", "success")
        return redirect(url_for("simulation_page"))

    @app.get("/login")
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for("simulation_page"))
        return render_template("login.html")

    @app.post("/login")
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("simulation_page"))
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()
        if user is None or not user.check_password(password):
            flash("Invalid username/email or password.", "error")
            return render_template("login.html"), 401
        login_user(user, remember=request.form.get("remember") == "on")
        next_page = request.args.get("next")
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(next_page or url_for("simulation_page"))

    @app.get("/logout")
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("simulation_page"))

    # ------------------------------------------------------------------ #
    #  Pages                                                               #
    # ------------------------------------------------------------------ #

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

    @app.post("/api/options/bsm/sensitivity")
    def bsm_sensitivity():
        """Return price-vs-parameter data for strike, time, rate, and vol."""
        ticker, strike, horizon, option_type = _option_inputs(_payload(request.get_json(silent=True)))
        with ThreadPoolExecutor(max_workers=4) as pool:
            fs = pool.submit(bsm_stocks.bsm_price_vs_strike, ticker, strike, horizon, option_type)
            ft = pool.submit(bsm_stocks.bsm_price_vs_time, ticker, strike, horizon, option_type)
            fr = pool.submit(bsm_stocks.bsm_price_vs_rate, ticker, strike, horizon, option_type)
            fv = pool.submit(bsm_stocks.bsm_price_vs_vol, ticker, strike, horizon, option_type)
            vs_strike = fs.result()
            vs_time = ft.result()
            vs_rate = fr.result()
            vs_vol = fv.result()
        return jsonify({
            "ticker": ticker,
            "vsStrike": vs_strike,
            "vsTime": vs_time,
            "vsRate": vs_rate,
            "vsVol": vs_vol,
        })

    @app.post("/api/options/bsm/terminal")
    def bsm_terminal():
        """Simulate terminal stock prices for the option's underlying."""
        data = _payload(request.get_json(silent=True))
        ticker = _ticker(data.get("ticker"))
        horizon = data.get("horizon")
        if horizon not in HORIZONS:
            raise ValueError("Select a valid time horizon.")
        count = _integer(data.get("numSim"), "numSim", MIN_SIMULATIONS, MAX_SIMULATIONS)
        terminal = np.asarray(sim_stock.sim_stock_terminal(ticker, horizon, count), dtype=float)
        bins = min(80, max(20, int(np.sqrt(count))))
        frequencies, edges = np.histogram(terminal, bins=bins)
        return jsonify({
            "ticker": ticker, "horizon": horizon, "simulations": count,
            "histogram": {"edges": edges.tolist(), "frequencies": frequencies.tolist()},
            "summary": {"mean": float(terminal.mean()), "median": float(np.median(terminal)), "p05": float(np.percentile(terminal, 5)), "p95": float(np.percentile(terminal, 95))},
        })

    # ------------------------------------------------------------------ #
    #  Portfolio management & optimisation (Markowitz)                   #
    # ------------------------------------------------------------------ #

    @app.get("/portfolio")
    @login_required
    def portfolio_page():
        return render_template("portfolio.html")

    @app.get("/api/portfolio/holdings")
    @login_required
    def get_portfolio_holdings():
        holdings = PortfolioHolding.query.filter_by(user_id=current_user.id).order_by(PortfolioHolding.ticker).all()
        if not holdings:
            return jsonify({
                "holdings": [],
                "totalValue": 0.0,
                "totalCost": 0.0,
                "totalPnl": 0.0,
                "totalPnlPct": 0.0,
                "count": 0,
            })

        tickers = [h.ticker for h in holdings]
        prices = _fetch_stock_prices(tickers)
        name_map = _stock_name_map()

        items = []
        total_val = 0.0
        total_cost = 0.0

        for h in holdings:
            p = prices.get(h.ticker)
            d = h.to_dict(current_price=p)
            d["name"] = name_map.get(h.ticker, h.ticker)
            items.append(d)
            total_val += d["currentValue"]
            total_cost += d["costBasis"]

        for d in items:
            d["weight"] = round((d["currentValue"] / total_val * 100.0) if total_val > 0 else 0.0, 1)

        total_pnl = total_val - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100.0) if total_cost > 0 else 0.0

        return jsonify({
            "holdings": items,
            "totalValue": round(total_val, 2),
            "totalCost": round(total_cost, 2),
            "totalPnl": round(total_pnl, 2),
            "totalPnlPct": round(total_pnl_pct, 2),
            "count": len(items),
        })

    @app.post("/api/portfolio/holdings")
    @login_required
    def add_portfolio_holding():
        data = _payload(request.get_json(silent=True))
        ticker = _ticker(data.get("ticker"))
        shares = _float_field(data.get("shares", 1.0), "shares", 0.0001, 1e9)
        raw_price = data.get("buyPrice")
        if raw_price is not None and str(raw_price).strip() != "":
            buy_price = _float_field(raw_price, "buyPrice", 0.01, 1e9)
        else:
            prices = _fetch_stock_prices([ticker])
            buy_price = prices.get(ticker, 100.0)

        existing = PortfolioHolding.query.filter_by(user_id=current_user.id, ticker=ticker).first()
        if existing:
            total_shares = existing.shares + shares
            existing_cost = (existing.buy_price or buy_price) * existing.shares
            new_cost = buy_price * shares
            existing.buy_price = round((existing_cost + new_cost) / total_shares, 2)
            existing.shares = round(total_shares, 4)
            holding = existing
        else:
            holding = PortfolioHolding(
                user_id=current_user.id,
                ticker=ticker,
                shares=shares,
                buy_price=buy_price,
            )
            db.session.add(holding)

        db.session.commit()
        prices = _fetch_stock_prices([ticker])
        result = holding.to_dict(current_price=prices.get(ticker))
        result["name"] = _stock_name_map().get(ticker, ticker)
        return jsonify({"success": True, "holding": result})

    @app.put("/api/portfolio/holdings/<int:holding_id>")
    @login_required
    def update_portfolio_holding(holding_id: int):
        holding = db.session.get(PortfolioHolding, holding_id)
        if not holding or holding.user_id != current_user.id:
            return jsonify({"error": "Holding not found."}), 404
        data = _payload(request.get_json(silent=True))
        if "shares" in data:
            holding.shares = _float_field(data["shares"], "shares", 0.0001, 1e9)
        if "buyPrice" in data and data["buyPrice"] is not None:
            holding.buy_price = _float_field(data["buyPrice"], "buyPrice", 0.01, 1e9)
        db.session.commit()
        prices = _fetch_stock_prices([holding.ticker])
        result = holding.to_dict(current_price=prices.get(holding.ticker))
        result["name"] = _stock_name_map().get(holding.ticker, holding.ticker)
        return jsonify({"success": True, "holding": result})

    @app.delete("/api/portfolio/holdings/<int:holding_id>")
    @login_required
    def delete_portfolio_holding(holding_id: int):
        holding = db.session.get(PortfolioHolding, holding_id)
        if not holding or holding.user_id != current_user.id:
            return jsonify({"error": "Holding not found."}), 404
        db.session.delete(holding)
        db.session.commit()
        return jsonify({"success": True, "id": holding_id})

    @app.post("/api/portfolio/apply-allocation")
    @login_required
    def apply_portfolio_allocation():
        data = _payload(request.get_json(silent=True))
        alloc = data.get("allocation")
        if not isinstance(alloc, dict) or not alloc:
            raise ValueError("No allocation data provided.")
        mode = data.get("mode", "replace")

        tickers = [_ticker(t) for t in alloc.keys()]
        prices = _fetch_stock_prices(tickers)

        if mode == "replace":
            PortfolioHolding.query.filter_by(user_id=current_user.id).delete()

        saved_count = 0
        for ticker, amount in alloc.items():
            t = _ticker(ticker)
            amt = float(amount)
            if amt <= 0:
                continue
            cur_price = prices.get(t, 100.0)
            shares = round(amt / cur_price, 4) if cur_price > 0 else 1.0

            existing = PortfolioHolding.query.filter_by(user_id=current_user.id, ticker=t).first()
            if existing and mode != "replace":
                existing.shares = round(existing.shares + shares, 4)
            elif not existing:
                h = PortfolioHolding(
                    user_id=current_user.id,
                    ticker=t,
                    shares=shares,
                    buy_price=cur_price,
                )
                db.session.add(h)
            saved_count += 1

        db.session.commit()
        return jsonify({"success": True, "saved": saved_count})

    @app.post("/api/portfolio/optimise")
    def portfolio_optimise():
        data = _payload(request.get_json(silent=True))
        tickers = _ticker_list(data.get("tickers"))
        req_return = _float_field(data.get("reqReturn"), "reqReturn", 0.0, 10.0)
        budget = _float_field(data.get("budget"), "budget", 1.0, 1e12)
        allow_short = bool(data.get("allowShort", False))
        fn = markowitz.markowitz_general if allow_short else markowitz.markowitz_long
        allocation = fn(tickers, req_return, budget)
        return jsonify({"tickers": tickers, "allocation": allocation, "allowShort": allow_short})

    # ------------------------------------------------------------------ #
    #  Risk analytics                                                      #
    # ------------------------------------------------------------------ #

    @app.get("/risk")
    def risk_page():
        return render_template("risk.html")

    @app.post("/api/risk")
    def risk():
        data = _payload(request.get_json(silent=True))
        tickers = _ticker_list(data.get("tickers"))
        raw_weights = data.get("weights")
        if not isinstance(raw_weights, list) or len(raw_weights) != len(tickers):
            raise ValueError("Provide one weight per selected stock.")
        try:
            weights = np.array([float(w) for w in raw_weights])
        except (TypeError, ValueError):
            raise ValueError("Weights must be numbers.") from None
        if not np.isfinite(weights).all() or weights.min() < 0:
            raise ValueError("Weights must be non-negative numbers.")
        total = weights.sum()
        if not np.isclose(total, 1.0, atol=1e-4):
            raise ValueError(f"Weights must sum to 1 (currently {total:.4f}).")
        period = data.get("period", "1y")
        VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "10y"}
        if period not in VALID_PERIODS:
            raise ValueError("Select a valid historical period.")
        portfolio_value = _float_field(data.get("portfolioValue"), "portfolioValue", 1.0, 1e12)
        confidence = data.get("confidence")
        if confidence not in (90, 95, 99):
            raise ValueError("Confidence level must be 90, 95, or 99.")
        result = risk_analytics.risk_measures(tickers, weights, period, portfolio_value, confidence)
        return jsonify({k: (float(v) if np.isfinite(v) else None) for k, v in result.items()})

    @app.errorhandler(ValueError)
    def invalid_input(error: ValueError):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(Exception)
    def calculation_failure(error: Exception):
        if isinstance(error, HTTPException):
            return error  # 404, 405, etc. – let Flask/Werkzeug handle them normally
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


def _ticker_list(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("Select at least one stock ticker.")
    tickers = [_ticker(t) for t in value]
    if len(tickers) > 50:
        raise ValueError("A maximum of 50 tickers is supported.")
    return tickers


def _float_field(value: object, field: str, lower: float, upper: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number.") from None
    if not np.isfinite(result) or not lower <= result <= upper:
        raise ValueError(f"{field} must be between {lower} and {upper}.")
    return result


def _fetch_stock_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch latest prices for a list of tickers with concurrent requests."""
    if not tickers:
        return {}
    import yfinance as yf
    prices: dict[str, float] = {}

    def _fetch_one(t: str):
        try:
            ticker_obj = yf.Ticker(t)
            if hasattr(ticker_obj, "fast_info") and "lastPrice" in ticker_obj.fast_info:
                p = ticker_obj.fast_info["lastPrice"]
                if p is not None and np.isfinite(p) and p > 0:
                    return t, float(p)
            hist = ticker_obj.history(period="5d")
            if not hist.empty and "Close" in hist:
                val = float(hist["Close"].dropna().iloc[-1])
                if np.isfinite(val) and val > 0:
                    return t, val
        except Exception:
            pass
        return t, None

    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as pool:
        for t, p in pool.map(_fetch_one, tickers):
            if p is not None:
                prices[t] = p
    return prices


def _stock_name_map() -> dict[str, str]:
    try:
        catalog = get_catalog()
        return {item["symbol"]: item["name"] for item in catalog}
    except Exception:
        return {}


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
