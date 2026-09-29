import numpy as np
import yfinance as yf
from scipy.stats import norm

try:
    from . import utils
except ImportError:
    import utils

def ret_and_vol(
    mu: np.ndarray, 
    w: np.ndarray, 
    Sigma: np.ndarray
) -> dict[str, float]:
    """
    Calculates the rate of return and the volatility of the portfolio.

    Parameters
    ==========
    mu : np.ndarray
        ndarray (n,) containing the rates of return of n assets in the portfolio as decimals (e.g., 23% is written as 0.23)
    w : np.ndarray
        ndarray (n,) containing the weights of n assets in the portfolio summing to 1
    Sigma : np.ndarray
        ndarray (n, n), covariance matrix

    Returns
    =======
    dict[str, float] :
        a dictionary containing the rate of return and volatility of the portfolio
    """
    
    ret = w @ mu
    vol = np.sqrt(w @ Sigma @ w)

    return ret, vol

def hist_var_cvar(
    asset_prices: np.ndarray, 
    weights: np.ndarray, 
    total_amount: float, 
    confidence: float
) -> list[float]:
    """
    Calculates the (daily) historical VaR and CVaR of the portfolio.

    Parameters
    ==========
    asset_prices : np.ndarray
        ndarray (t x n), with rows representing days and columns representing assets
    weights : np.ndarray
        ndarray (n,) containing the weights of n assets in the portfolio summing to 1
    total_amount : float
        current portfolio value
    confidence : float
        confidence level in percentage, e.g., 95

    Returns
    =======
    list[float] :
        a list containing the rate of return at the specified loss tolerance percentile, the value at risk, expected shortfall rate of return for the specified confidence interval, and expected shortfall
    """
    
    asset_returns = (asset_prices[1:] - asset_prices[:-1]) / asset_prices[:-1]
    portfolio_returns = asset_returns @ weights
    
    var_return = np.percentile(portfolio_returns, 100 - confidence)
    var = var_return * total_amount

    tail_returns = portfolio_returns[portfolio_returns <= var_return]
    cvar_return = np.mean(tail_returns)
    cvar = cvar_return * total_amount
    
    return [-var_return, -var, -cvar_return, -cvar]

def parametric_var_cvar(
    mu: np.ndarray, 
    w: np.ndarray, 
    Sigma: np.ndarray, 
    total_amount: float, 
    confidence: float
) -> list[float]:
    """
    Calculates the parametric VaR and CVaR of the portfolio, assuming portfolio returns are normally distributed.

    Parameters
    ==========
    mu : np.ndarray
        ndarray (n,), containing the expected returns of n assets
    w : np.ndarray
        ndarray (n,), containing the weights of n assets in the portfolio
    Sigma : np.ndarray
        ndarray (n x n), covariance matrix of the asset returns
    total_amount : float
        current portfolio value
    confidence : float
        confidence level in percentage, e.g., 95

    Returns
    =======
    list[float] :
        a list containing the rate of return at the specified loss tolerance percentile, the value at risk, expected shortfall rate of return for the specified confidence interval, and expected shortfall
    """
    
    mu_p, sigma_p = ret_and_vol(mu, w, Sigma)
    alpha = (100 - confidence) / 100
    
    var_return = mu_p + sigma_p * norm.ppf(alpha)
    var = var_return * total_amount

    z = (var_return - mu_p) / sigma_p
    cvar_return = mu_p - sigma_p * norm.pdf(z) / alpha
    cvar = cvar_return * total_amount

    return [-var_return, -var, -cvar_return, -cvar]

def mdd(
    asset_prices: np.ndarray, 
    weights: np.ndarray
) -> float:
    """
    Calculates the maximum drawdown of a portfolio over the given period.

    Parameters
    ==========
    asset_prices : np.ndarray
        ndarray (T x n), containing the prices of n assets over T time periods
    weights : np.ndarray
        ndarray (n,), containing the weights of n assets in the portfolio

    Returns
    =======
    float :
        the maximum drawdown of the portfolio as a decimal. The value is negative, e.g. -0.20 represents a 20% maximum drawdown.
    """
    
    v = (asset_prices / asset_prices[0]) @ weights
    peak = -np.inf
    max_dd = 0
    
    for value in v:
        peak = max(peak, value)
        drawdown = (value - peak) / peak
        max_dd = min(max_dd, drawdown)
    
    return max_dd

def sharpe(
    asset_prices: np.ndarray, 
    weights: np.ndarray,
    r: float
) -> float:
    """
    Calculates the annualized Sharpe ratio of a portfolio over the given period.

    Parameters
    ==========
    asset_prices : np.ndarray
        ndarray (T x n), containing the prices of n assets over T time periods
    weights : np.ndarray
        ndarray (n,), containing the weights of n assets in the portfolio
    r : float
        annualized risk-free rate as a decimal

    Returns
    =======
    float :
        the annualized Sharpe ratio of the portfolio.
    """
    
    asset_returns = (asset_prices[1:] - asset_prices[:-1]) / asset_prices[:-1]
    mu = np.mean(asset_returns, axis=0)
    Sigma = np.cov(asset_returns.T)

    mu_p, sigma_p = ret_and_vol(mu, weights, Sigma)
    
    S = np.sqrt(252) * (mu_p - r / 252) / sigma_p
    
    return S

def risk_measures(
    ticker_symbols: list[str],
    w: np.ndarray,
    T: str,
    total_amount: float,
    confidence: float
) -> dict[str, float]:
    """
    Calculates various risk measures of a portfolio over the given period.

    Parameters
    ==========
    ticker_symbols : list[str]
        List of ticker symbols for the assets in the portfolio.
    w : np.ndarray
        ndarray (n,) containing the weights of n assets in the portfolio
    T : str
        Historical period over which the risk measures are calculated.
    total_amount : float
        Current portfolio value.
    confidence : float
        Confidence level in percentage, e.g., 95

    Returns
    =======
    dict[str, float] :
        A dictionary containing the portfolio return, volatility, historical VaR
        and CVaR, parametric VaR and CVaR, maximum drawdown, and Sharpe ratio.
    """

    tickers = yf.Tickers(ticker_symbols)
    asset_prices = tickers.history(period=T)["Close"].to_numpy()
    
    asset_returns = (asset_prices[1:] - asset_prices[:-1]) / asset_prices[:-1]
    mu = np.mean(asset_returns, axis=0)
    Sigma = np.cov(asset_returns.T)
    r = utils.calc_r(1.0)

    pf_exp_ret, pf_vol = ret_and_vol(mu, w, Sigma)
    hvar_rate, hvar, hcvar_rate, hcvar = hist_var_cvar(asset_prices, w, total_amount, confidence)
    pvar_rate, pvar, pcvar_rate, pcvar = parametric_var_cvar(mu, w, Sigma, total_amount, confidence)
    max_drawdown = mdd(asset_prices, w)
    sharpe_ratio = sharpe(asset_prices, w, r)

    return {
        "portfolio_return": pf_exp_ret,
        "portfolio_volatility": pf_vol,
        "hist_var_rate": hvar_rate * 100,
        "hist_var": hvar,
        "hist_cvar_rate": hcvar_rate * 100,
        "hist_cvar": hcvar,
        "param_var_rate": pvar_rate * 100,
        "param_var": pvar,
        "param_cvar_rate": pcvar_rate * 100,
        "param_cvar": pcvar,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe_ratio
    }