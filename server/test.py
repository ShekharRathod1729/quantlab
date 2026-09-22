import sim_stock
import matplotlib.pylab as plt

terminal_prices = sim_stock.sim_stock_terminal("AAPL", "1m", 100000)

dates, paths = sim_stock.sim_stock_paths("AAPL", "1m", 1000)
plt.figure(figsize=(10, 6))
plt.plot(dates, paths)
plt.xlabel("Date")
plt.ylabel("Price")
plt.show()
