import matplotlib.pylab as plt
import bsm_stocks

A = bsm_stocks.bsm_price_vs_time("AAPL", 350, "1m", "call")

strikes, values = A["time"], A["opt_vals"]

plt.figure(figsize=(10, 6))
plt.plot(strikes, values)
plt.show()