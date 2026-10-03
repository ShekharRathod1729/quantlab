import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from server.app import create_app
from server.models import db, User, PortfolioHolding

def test_full_portfolio_flow():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    # 1. Unauthenticated check
    r_unauth = client.get('/api/portfolio/holdings')
    assert r_unauth.status_code == 302, f"Expected 302 redirect for unauth, got {r_unauth.status_code}"

    # 2. Register
    r_reg = client.post('/register', data={
        'username': 'quant_trader',
        'email': 'quant@trade.com',
        'password': 'SecurePassword123',
        'confirm': 'SecurePassword123'
    }, follow_redirects=True)
    assert r_reg.status_code == 200

    # 3. Add holdings
    r_add1 = client.post('/api/portfolio/holdings', json={'ticker': 'AAPL', 'shares': 10, 'buyPrice': 170.0})
    r_add2 = client.post('/api/portfolio/holdings', json={'ticker': 'MSFT', 'shares': 5, 'buyPrice': 350.0})
    assert r_add1.status_code == 200
    assert r_add2.status_code == 200

    # 4. Get holdings
    r_get = client.get('/api/portfolio/holdings')
    h_data = r_get.get_json()
    assert h_data['count'] == 2
    assert h_data['totalCost'] == 3450.0
    assert h_data['totalValue'] > 0
    assert len(h_data['holdings']) == 2
    print(f"Total Market Value: ${h_data['totalValue']}, PnL: ${h_data['totalPnl']} ({h_data['totalPnlPct']}%)")

    # 5. Update holding
    h_id = h_data['holdings'][0]['id']
    r_put = client.put(f'/api/portfolio/holdings/{h_id}', json={'shares': 15, 'buyPrice': 175.0})
    assert r_put.status_code == 200
    assert r_put.get_json()['holding']['shares'] == 15.0

    # 6. Apply allocation
    r_alloc = client.post('/api/portfolio/apply-allocation', json={
        'allocation': {'AAPL': 6000, 'GOOGL': 4000},
        'mode': 'replace'
    })
    assert r_alloc.status_code == 200
    r_get2 = client.get('/api/portfolio/holdings')
    tickers = [h['ticker'] for h in r_get2.get_json()['holdings']]
    assert 'AAPL' in tickers and 'GOOGL' in tickers

    # 7. Delete holding
    h_del_id = r_get2.get_json()['holdings'][0]['id']
    r_del = client.delete(f'/api/portfolio/holdings/{h_del_id}')
    assert r_del.status_code == 200
    r_get3 = client.get('/api/portfolio/holdings')
    assert r_get3.get_json()['count'] == 1

    # 8. Clean up
    with app.app_context():
        u = User.query.filter_by(username='quant_trader').first()
        if u:
            db.session.delete(u)
            db.session.commit()
    print("All integration tests in test_portfolio_auth.py passed successfully!")

if __name__ == '__main__':
    test_full_portfolio_flow()
