import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from app import create_app


def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_simulation_rejects_out_of_range_count():
    response = client().post("/api/simulations", json={"ticker": "AAPL", "horizon": "1m", "numSim": 9_999})
    assert response.status_code == 400


@patch("app.sim_stock.sim_stock_paths")
@patch("app.sim_stock.sim_stock_terminal")
def test_simulation_returns_histogram_and_requested_paths(terminal, paths):
    terminal.return_value = np.array([95.0, 100.0, 105.0])
    paths.return_value = (pd.bdate_range("2026-01-01", periods=2), np.array([[100.0, 100.0], [102.0, 98.0]]))
    response = client().post("/api/simulations", json={"ticker": "AAPL", "horizon": "1m", "numSim": 10_000, "pathCount": 1})
    assert response.status_code == 200
    assert len(response.json["paths"]["values"][0]) == 1
    terminal.assert_called_once_with("AAPL", "1m", 10_000)
    paths.assert_called_once_with("AAPL", "1m", 10_000)


@patch("app.price_option_mcs.price_option", return_value=12.34)
@patch("app.bsm_stocks.price_option_bsm", return_value={"price": 12.0, "delta": .5, "gamma": .1, "theta": -.2, "vega": .3, "rho": .4})
def test_monte_carlo_includes_bsm_benchmark(_bsm, _mcs):
    response = client().post("/api/options/mcs", json={"ticker": "AAPL", "strike": 100, "horizon": "1m", "optionType": "call", "numSim": 10_000})
    assert response.status_code == 200
    assert response.json["bsm"]["price"] == 12.0
    assert response.json["monteCarlo"] == 12.34
