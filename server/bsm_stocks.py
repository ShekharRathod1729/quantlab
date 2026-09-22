import bsm
import utils
import yfinance as yf

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