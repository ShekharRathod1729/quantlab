import numpy as np
import yfinance as yf
import datetime as dt
from pandas_datareader import data as web

def calc_daily_log_return(ticker: yf.Ticker) -> np.ndarray:
    """
    Takes a yf.Ticker object and returns the daily log returns of the stock over the last 2 years in an ndarray.
    """
    
    close_history = ticker.history(period="2y")["Close"].to_numpy()

    daily_log_return = np.log(close_history[1:] / close_history[:-1])

    return daily_log_return

def exp_return(ticker: yf.Ticker) -> float:
    """
    Takes a yf.Ticker object and returns the annualised expected rate of return of the stock.
    """

    daily_ret = calc_daily_log_return(ticker)
    mu = np.mean(daily_ret) * 252

    return mu

def volatility(ticker: yf.Ticker) -> float:
    """
    Takes a yf.Ticker object and returns the annualised volatility of the stock.
    """

    daily_ret = calc_daily_log_return(ticker)
    sigma = np.std(daily_ret, ddof=1) * np.sqrt(252) 

    return sigma

def calc_r(T: float) -> float:
    """
    Takes the time interval between today and maturity in years and returns the T-bill rate as an approximation for riskless rate.
    """

    start = dt.datetime(2026,1,1)  # start date, irrelevant here but required as an argument in the DataReader function

    end = dt.datetime.today()
    r_y = 0

    # 3 month horizon, use 3-month T-bill
    if T <= 0.25:
        r_y = web.DataReader("DTB3", "fred", start, end).iloc[:, 0].dropna().iloc[-1] / 100 # rates are returned in percentage and so division by 100
    
    # 3 to 6 month horizon, use 6-month T-bill
    elif T <= 0.5:
        r_y = web.DataReader("DTB6", "fred", start, end).iloc[:, 0].dropna().iloc[-1] / 100
    
    # for longer time horizons, use 1-year T-bill
    else:
        r_y = web.DataReader("DTB1YR", "fred", start, end).iloc[:, 0].dropna().iloc[-1] / 100

    r = np.log(1 + r_y)  # this is the annual riskless rate

    return r

