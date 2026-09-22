import numpy as np

def price_european(
  option_type : str,
  S : float, 
  K : float,
  r : float, 
  sigma: float,
  T : float,
  num_sim : int,
) -> float:
  """
  Calculates the value of a European option via Monte Carlo simulation.

  Parameters
  ==========
  option_type: str
      Takes either "call" or "put" as value
  S : float
      Stock price/index level at time 0.
  K : float
      Strike price.
  r : float
      Constant riskless short rate.
  sigma : float
      Volatility.
  T : float
      Time to maturity.
  num_sim : int
      Number of simulations.

  Returns
  =======
  float :
      Value of the European option with the given parameters.
  """
  
  Z = np.random.randn(num_sim)
  terminal_prices = S * np.exp((r - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * Z)

  if option_type == "call":
    payoffs = np.maximum(0, terminal_prices - K)
  
  elif option_type == "put":
    payoffs = np.maximum(0, K - terminal_prices)

  else:
    raise ValueError("option_type must be 'call' or 'put'.")
  
  return np.exp(-r * T) * np.mean(payoffs)