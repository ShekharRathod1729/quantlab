try:
  from . import bsm, utils
except ImportError:  # Allows running this module directly from server/.
  import bsm
  import utils
import yfinance as yf
import numpy as np


HORIZONS = {
  "1w" : 5,
  "1m" : 21,
  "3m" : 63,
  "6m" : 126,
  "1y" : 252
}


def price_option_bsm(
  ticker_symb: str, 
  strike: float,
  horizon:str, 
  opt_type: str
) -> dict[str, float]:
  """
  Calculates the theoretical BSM price and Greeks for a European option on a stock.

  Parameters
  ==========
  ticker_symb : str
    Ticker symbol for the stock to be simulated, e.g., "AAPL"
  strike : float
    Strike price of the option
  horizon : str
    Time horizon as a string, one of the keys in HORIZONS, e.g., "1w"
  opt_type : str
    Takes either "call" or "put" as value

  Returns
  =======
  dict[str, float] :
    Dictionary containing the theoretical option price and Greeks (delta, gamma, theta, rho, vega)
  """

  if not (opt_type == "call" or opt_type == "put"):
    raise ValueError("opt_type must be 'call' or 'put'.")

  ticker = yf.Ticker(ticker_symb)

  S0 = ticker.history(period="1d")["Close"].iloc[-1]
  T = HORIZONS[horizon] / 252
  r = utils.calc_r(T)
  sigma = utils.volatility(ticker)

  delta = bsm.bsm_delta(opt_type, S0, strike, r, sigma, T)
  gamma = bsm.bsm_gamma(opt_type, S0, strike, r, sigma, T)
  theta = bsm.bsm_theta(opt_type, S0, strike, r, sigma, T)
  rho = bsm.bsm_rho(opt_type, S0, strike, r, sigma, T)
  vega = bsm.bsm_vega(opt_type, S0, strike, r, sigma, T)

  if opt_type == "call":
    price = bsm.bsm_call(S0, strike, r, sigma, T)

  else:
    price = bsm.bsm_put(S0, strike, r, sigma, T)
    
  return {
    "price" : price,
    "delta" : delta,
    "gamma" : gamma, 
    "theta" : theta, 
    "rho" : rho, 
    "vega" : vega
  }


def bsm_price_vs_strike(
  ticker_symb: str,
  strike: float,
  horizon: str,
  opt_type: str
) -> dict[str, list[float]]:
  """
  Calculates the theoretical BSM option prices for a range of strike prices.

  Parameters
  ==========
  ticker_symb : str
    Ticker symbol for the stock, e.g., "AAPL"
  strike : float
    Strike price around which the range of strike prices is generated
  horizon : str
    Time horizon as a string, one of the keys in HORIZONS, e.g., "1w"
  opt_type : str
    Takes either "call" or "put" as value

  Returns
  =======
  dict[str, list[float]] :
    Dictionary containing the strike prices and corresponding option prices
  """

  if not (opt_type == "call" or opt_type == "put"):
    raise ValueError("opt_type must be 'call' or 'put'.")

  ticker = yf.Ticker(ticker_symb)

  S0 = ticker.history(period="1d")["Close"].iloc[-1]
  T = HORIZONS[horizon] / 252
  r = utils.calc_r(T)
  sigma = utils.volatility(ticker)

  strikes = np.linspace(max(strike - 20, 0), strike + 20, 100)

  if opt_type == "call":
    opt_vals = np.array([bsm.bsm_call(S0, k, r, sigma, T) for k in strikes])
  else:
    opt_vals = np.array([bsm.bsm_put(S0, k, r, sigma, T) for k in strikes])

  return {
    "strikes": strikes.tolist(),
    "opt_vals": opt_vals.tolist()
  }


def bsm_price_vs_time(
  ticker_symb: str,
  strike: float,
  horizon: str,
  opt_type: str
) -> dict[str, list[float]]:
  """
  Calculates the theoretical BSM option prices for a range of times to maturity.

  Parameters
  ==========
  ticker_symb : str
    Ticker symbol for the stock, e.g., "AAPL"
  strike : float
    Strike price of the option
  horizon : str
    Time horizon as a string, one of the keys in HORIZONS, e.g., "1w"
  opt_type : str
    Takes either "call" or "put" as value

  Returns
  =======
  dict[str, list[float]] :
    Dictionary containing the times to maturity and corresponding option prices
  """

  if not (opt_type == "call" or opt_type == "put"):
    raise ValueError("opt_type must be 'call' or 'put'.")

  ticker = yf.Ticker(ticker_symb)

  S0 = ticker.history(period="1d")["Close"].iloc[-1]
  T = HORIZONS[horizon] / 252
  r = utils.calc_r(T)
  sigma = utils.volatility(ticker)

  tvals = np.linspace(0.00001, 1, 100)

  if opt_type == "call":
    opt_vals = np.array([bsm.bsm_call(S0, strike, r, sigma, t) for t in tvals])
  else:
    opt_vals = np.array([bsm.bsm_put(S0, strike, r, sigma, t) for t in tvals])

  return {
    "time": tvals.tolist(),
    "opt_vals": opt_vals.tolist()
  }


def bsm_price_vs_rate(
  ticker_symb: str,
  strike: float,
  horizon: str,
  opt_type: str
) -> dict[str, list[float]]:
  """
  Calculates the theoretical BSM option prices for a range of risk-free interest rates.

  Parameters
  ==========
  ticker_symb : str
    Ticker symbol for the stock, e.g., "AAPL"
  strike : float
    Strike price of the option
  horizon : str
    Time horizon as a string, one of the keys in HORIZONS, e.g., "1w"
  opt_type : str
    Takes either "call" or "put" as value

  Returns
  =======
  dict[str, list[float]] :
    Dictionary containing the risk-free interest rates and corresponding option prices
  """

  if not (opt_type == "call" or opt_type == "put"):
    raise ValueError("opt_type must be 'call' or 'put'.")

  ticker = yf.Ticker(ticker_symb)

  S0 = ticker.history(period="1d")["Close"].iloc[-1]
  T = HORIZONS[horizon] / 252
  sigma = utils.volatility(ticker)

  rvals = np.linspace(0, 0.2, 100)

  if opt_type == "call":
    opt_vals = np.array([bsm.bsm_call(S0, strike, r, sigma, T) for r in rvals])
  else:
    opt_vals = np.array([bsm.bsm_put(S0, strike, r, sigma, T) for r in rvals])

  return {
    "rate": rvals.tolist(),
    "opt_vals": opt_vals.tolist()
  }


def bsm_price_vs_vol(
  ticker_symb: str,
  strike: float,
  horizon: str,
  opt_type: str
) -> dict[str, list[float]]:
  """
  Calculates the theoretical BSM option prices for a range of volatility values.

  Parameters
  ==========
  ticker_symb : str
    Ticker symbol for the stock, e.g., "AAPL"
  strike : float
    Strike price of the option
  horizon : str
    Time horizon as a string, one of the keys in HORIZONS, e.g., "1w"
  opt_type : str
    Takes either "call" or "put" as value

  Returns
  =======
  dict[str, list[float]] :
    Dictionary containing the volatility values and corresponding option prices
  """

  if not (opt_type == "call" or opt_type == "put"):
    raise ValueError("opt_type must be 'call' or 'put'.")

  ticker = yf.Ticker(ticker_symb)

  S0 = ticker.history(period="1d")["Close"].iloc[-1]
  T = HORIZONS[horizon] / 252
  r = utils.calc_r(T)

  sigma_vals = np.linspace(0.01, 0.5, 100)

  if opt_type == "call":
    opt_vals = np.array([bsm.bsm_call(S0, strike, r, sigma, T) for sigma in sigma_vals])
  else:
    opt_vals = np.array([bsm.bsm_put(S0, strike, r, sigma, T) for sigma in sigma_vals])

  return {
    "sigma_vals": sigma_vals.tolist(),
    "opt_vals": opt_vals.tolist()
  }