# QuantLab

Web interface for simulating stock prices and pricing European options.

## Run locally

Create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app server.app run --debug
```

Open `http://127.0.0.1:5000`. Market data is retrieved at calculation time from Yahoo Finance and FRED. The searchable catalogue refreshes from the S&P 500 and Nifty 50 constituent sources and falls back to its last local cache if they are unavailable.
