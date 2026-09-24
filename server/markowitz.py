import yfinance as yf
import numpy as np
from scipy.optimize import minimize

def markowitz_general(
  ticker_symbols: list[str], 
  req_return: float, 
  budget: float
) -> dict[str, float]:
  """
  Calculates the minimum-variance portfolio for a required return using
  Markowitz mean-variance portfolio theory, allowing short selling.

  Parameters
  ==========
  ticker_symbols : list[str]
    List of ticker symbols for the stocks to include in the portfolio,
    e.g., ["AAPL", "MSFT", "GOOGL"].
  req_return : float
    Required annual portfolio return as a decimal, e.g., 0.20 for 20%.
  budget : float
    Total amount of money available for investment.

  Returns
  =======
  dict[str, float] :
    Dictionary mapping each ticker symbol to its recommended dollar
    allocation. Short positions are permitted.
  """
  
  n = len(ticker_symbols)
    
  tickers = yf.Tickers(ticker_symbols)
  closing_prices = tickers.history(period="2y")["Close"].to_numpy()
  returns = (closing_prices[1:] - closing_prices[:-1]) / closing_prices[:-1]

  mu = np.mean(returns, axis=0) * 252
  sigma = np.cov(returns, rowvar=False, ddof=1) * 252

  ones = np.ones(n)
    
  A = np.block([
    [sigma, -mu[:, None], -ones[:, None]],
    [mu[None, :], 0, 0],
    [ones[None, :], 0, 0]
  ])

  b = np.concatenate([
    np.zeros(n), 
    [req_return, 1]
  ])

  w = np.linalg.solve(A, b)
  allocation = w * budget

  return dict(zip(ticker_symbols, allocation))

def markowitz_long(
  ticker_symbols: list[str], 
  req_return: float, 
  budget: float
) -> dict[str, float]:
  """
  Calculates the minimum-variance portfolio for a required return using
  Markowitz mean-variance portfolio theory with no short selling.

  Parameters
  ==========
  ticker_symbols : list[str]
    List of ticker symbols for the stocks to include in the portfolio,
    e.g., ["AAPL", "MSFT", "GOOGL"].
  req_return : float
    Required annual portfolio return as a decimal, e.g., 0.20 for 20%.
  budget : float
    Total amount of money available for investment.

  Returns
  =======
  dict[str, float] :
    Dictionary mapping each ticker symbol to its recommended dollar
    allocation. All allocations are non-negative.
  """
  
  n = len(ticker_symbols)
    
  tickers = yf.Tickers(ticker_symbols)
  closing_prices = tickers.history(period="2y")["Close"].to_numpy()
  returns = (closing_prices[1:] - closing_prices[:-1]) / closing_prices[:-1]

  mu = np.mean(returns, axis=0) * 252
  sigma = np.cov(returns, rowvar=False, ddof=1) * 252

  ones = np.ones(n)

  result = minimize(
    lambda w: w @ sigma @ w,
    ones / n,
    method="SLSQP", 
    bounds=[(0, None)] * n,
    constraints=[
      {"type": "eq", "fun": lambda w: mu @ w - req_return},
      {"type": "eq", "fun": lambda w: w.sum() - 1}
     ]
  )

  allocation = result.x * budget
  return dict(zip(ticker_symbols, allocation))