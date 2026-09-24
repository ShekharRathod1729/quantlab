try:
  from . import option_mcs, utils
except ImportError:  # Allows running this module directly from server/.
  import option_mcs
  import utils
import yfinance as yf

HORIZONS = {
  "1w" : 5,
  "1m" : 21,
  "3m" : 63,
  "6m" : 126,
  "1y" : 252
}

def price_option(
  ticker_symb: str, 
  strike: float,
  horizon:str, 
  opt_type: str,
  num_sim: int
) -> float:
  """
  Calculates the value of a European option on a stock via Monte Carlo simulation.
  
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
  num_sim : int
    Number of simulations
  
  Returns
  =======
  float:
    Value of the European option with the given parameters.
  """

  ticker = yf.Ticker(ticker_symb)
  S = ticker.history(period="1d")["Close"].iloc[-1]
  T = HORIZONS[horizon] / 252
  r = utils.calc_r(T)
  sigma = utils.volatility(ticker)

  return option_mcs.price_european(opt_type, S, strike, r, sigma, T, num_sim)
