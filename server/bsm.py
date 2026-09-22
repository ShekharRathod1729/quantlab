import numpy as np
from scipy.integrate import quad

def snv_pdf(x: float) -> float:
  """
  Probability density function (PDF) of the standard normal variable (SNV).
  """

  return np.exp(-0.5 * x ** 2) / (np.sqrt(2 * np.pi))

def snv_cdf(d: float) -> float:
  """
  Cumulative distribution function (CDF) of the normal distribution.

  Parameters
  ==========
  d : float
      Upper limit of the integral.

  Returns
  =======
  float :
      CDF of the normal distribution evaluated at d.
  
  """
  
  return quad(lambda x: snv_pdf(x), -np.inf, d)[0]

def calc_d1(
  S: float,
  K: float, 
  r: float, 
  sigma: float, 
  T: float,
) -> float:
  """
  Calculates d1 in the BSM model.

  Parameters
  ==========
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

  Returns
  =======
  float :
      value of d1.

  """

  num = np.log(S / K) + (r + (sigma ** 2) / 2) * T
  den = sigma * np.sqrt(T)
  d1 = num / den
  return d1

def bsm_call(
  S : float, 
  K : float,
  r : float, 
  sigma: float,
  T : float,  
) -> float:
  """
  Calculates the BSM value of a European call option.

  Parameters
  ==========
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

  Returns
  =======
  float :
      BSM value of a European call option.
  """
  
  d1 = calc_d1(S, K, r, sigma, T)
  d2 = d1 - sigma * np.sqrt(T)

  call_value = S * snv_cdf(d1) - K * np.exp(-r * T) * snv_cdf(d2)

  return call_value

def bsm_put(
  S : float, 
  K : float,
  r : float, 
  sigma: float,
  T : float,  
) -> float:
  """
  Calculates the BSM value of a European put option.

  Parameters
  ==========
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

  Returns
  =======
  float :
      BSM value of a European put option.
  """
  
  d1 = calc_d1(S, K, r, sigma, T)
  d2 = d1 - sigma * np.sqrt(T)

  put_value = K * np.exp(-r * T) * snv_cdf(-d2) - S * snv_cdf(-d1)

  return put_value

def bsm_delta(  
  option_type: str,
  S : float, 
  K : float,
  r : float, 
  sigma: float,
  T : float,  
) -> float:
  """
  Calculates the BSM delta of a European option.

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

  Returns
  =======
  float :
      BSM delta of a European option.
  """
  d1 = calc_d1(S, K, r, sigma, T)
  delta_call = snv_cdf(d1)

  if option_type == "call":
    return delta_call
  
  elif option_type == "put":
    return delta_call - 1
  
  else:
    raise ValueError("option_type must be 'call' or 'put'.")
  

def bsm_gamma(  
  option_type: str,
  S : float, 
  K : float,
  r : float, 
  sigma: float,
  T : float,  
) -> float:
  """
  Calculates the BSM gamma of a European option.

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

  Returns
  =======
  float :
      BSM gamma of a European option.
  """
  d1 = calc_d1(S, K, r, sigma, T)
  gamma = snv_pdf(d1) / (S * sigma * np.sqrt(T))

  if option_type == "call" or option_type == "put":
    return gamma
 
  else:
    raise ValueError("option_type must be 'call' or 'put'.")
  

def bsm_theta(  
  option_type: str,
  S : float, 
  K : float,
  r : float, 
  sigma: float,
  T : float,  
) -> float:
  """
  Calculates the BSM theta of a European option.

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

  Returns
  =======
  float :
      BSM theta of a European option.
  """
  d1 = calc_d1(S, K, r, sigma, T)
  d2 = d1 - sigma * np.sqrt(T)
  theta = - S * snv_pdf(d1) * sigma / (2 * np.sqrt(T)) - r * np.exp(-r * T) * K * snv_cdf(d2)

  if option_type == "call":
    return theta
  
  elif option_type == "put":
    return theta + r * K * np.exp(-r * T)
  
  else:
    raise ValueError("option_type must be 'call' or 'put'.")
  
def bsm_rho(  
  option_type: str,
  S : float, 
  K : float,
  r : float, 
  sigma: float,
  T : float,  
) -> float:
  """
  Calculates the BSM rho of a European option.

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

  Returns
  =======
  float :
      BSM rho of a European option.
  """
  d1 = calc_d1(S, K, r, sigma, T)
  d2 = d1 - sigma * np.sqrt(T)
  

  if option_type == "call":
    return K * T * np.exp(-r * T) * snv_cdf(d2)
  
  elif option_type == "put":
    return -K * T * np.exp(-r * T) * snv_cdf(-d2)
  
  else:
    raise ValueError("option_type must be 'call' or 'put'.")
  
def bsm_vega(  
  option_type: str,
  S : float, 
  K : float,
  r : float, 
  sigma: float,
  T : float,  
) -> float:
  """
  Calculates the BSM vega of a European option.

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

  Returns
  =======
  float :
      BSM vega of a European option.
  """
  d1 = calc_d1(S, K, r, sigma, T)

  if option_type == "call" or option_type == "put":
    return S * snv_pdf(d1) * np.sqrt(T)
 
  else:
    raise ValueError("option_type must be 'call' or 'put'.")