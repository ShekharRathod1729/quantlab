import stock_gbm
import utils
import numpy as np
import yfinance as yf
import pandas as pd

HORIZONS = {
  "1w" : 5,
  "1m" : 21,
  "3m" : 63,
  "6m" : 126,
  "1y" : 252
}

def sim_stock_terminal(
  tick_symb : str,
  horizon : str,
  N : int
) -> np.ndarray:
  """
  Simulates the terminal price of a stock after the given time horizon.

  Parameters
  ==========
  tick_symb : str
    Ticker symbol for the stock to be simulated, e.g., "AAPL"
  horizon : str
    Time horizon as a string, one of the keys in HORIZONS, e.g., "1w"
  N : int
    Number of simulations
  
  Returns
  =======
  np.ndarray :
    ndarray of shape (N,) containing N simulated terminal prices
  """

  ticker = yf.Ticker(tick_symb)

  mu = utils.exp_return(ticker)
  sigma = utils.volatility(ticker)

  S0 = ticker.history(period="1d")["Close"].iloc[-1]

  T = HORIZONS[horizon] / 252

  return stock_gbm.sim_terminal_gbm(S0, mu, sigma, T, N)

def sim_stock_paths(
  tick_symb : str,
  horizon : str,
  N : int
) -> tuple[pd.DatetimeIndex, np.ndarray]:
  """
  Simulates the path of a stock over the given time horizon.

  Parameters
  ==========
  tick_symb : str
    Ticker symbol for the stock to be simulated, e.g., "AAPL"
  horizon : str
    Time horizon as a string, one of the keys in HORIZONS, e.g., "1w"
  N : int
    Number of simulations
    
  Returns
  =======
  pd.DatetimeIndex :
    dates of business days across the horizon
  np.ndarray :
    ndarray containing N simulated paths
  """

  ticker = yf.Ticker(tick_symb)

  mu = utils.exp_return(ticker)
  sigma = utils.volatility(ticker)
  
  S0 = ticker.history(period="1d")["Close"].iloc[-1]

  T = HORIZONS[horizon] / 252
  I = HORIZONS[horizon]

  paths = stock_gbm.sim_path_gbm(S0, mu, sigma, T, N, I)

  start_date = ticker.history(period="1d").index[-1].normalize()

  dates = pd.bdate_range(
    start=start_date,
    periods=I + 1
  )

  return dates, paths

