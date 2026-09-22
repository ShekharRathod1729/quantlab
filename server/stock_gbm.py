import numpy as np
import numpy.random as npr

def sim_terminal_gbm(
    S0 : float, 
    mu : float, 
    sigma: float,
    T : float,
    N : int,
) -> np.ndarray:
    """
    Simulates the terminal price of a stock after time T

    Parameters
    ==========
    S0 : float
        Stock price at time 0.
    mu : float
        Expected rate of return.
    sigma : float
        Volatility.
    T : float
        Time horizon (in years).
    N : int
        Number of simulations.
    
    Returns
    =======
    np.ndarray :
        ndarray of shape (N,) containing N simulated prices
    """
    
    S_T = S0 * np.exp((mu - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * npr.randn(N))
    return S_T

def sim_path_gbm(
    S0 : float, 
    mu : float,
    sigma : float, 
    T : float, 
    N : int, 
    I : int
) -> np.ndarray:
    """
    Simulates the path of the stock price

    Parameters
    ==========
    S0 : float
        Stock price at time 0.
    mu : float
        Expected rate of return.
    sigma : float
        Volatility.
    T : float
        Time horizon (in years).
    N : int
        Number of simulations.
    I : int
        Number of intervals.

    Returns
    =======
    np.ndarray :
        ndarray of shape (I + 1, N), with each column representing a simulated path
    """
    
    dt = T / I
    paths = np.zeros((I + 1, N))
    paths[0] = S0

    for i in range(1, I + 1):
        paths[i] = paths[i - 1] * np.exp((mu - 0.5 * sigma ** 2) * dt - sigma * np.sqrt(dt) * npr.randn(N))

    return paths