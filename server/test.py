import bsm_stocks
import price_option_mcs

for i in range(1, 11):
  mcs_price = price_option_mcs.price_option("AAPL", 390, "1m", "call", i * 100000)

  print(f"The price of the option by Monte Carlo simulations is: {mcs_price: .4f}")

bsm_price = bsm_stocks.price_option_bsm("AAPL", 390, "1m", "call")["price"]

print(f"The price of the option by the BSM formulae is: {bsm_price: .4f}")