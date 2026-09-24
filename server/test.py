import markowitz

ticker_symbols = ["AAPL", "MSFT", "GOOG", "NVDA"]
req_return = 0.5
budget = 10000

result = markowitz.markowitz_long(ticker_symbols, req_return, budget)
print(result)