from flask import Flask, render_template, jsonify, request, session
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        subdomain = data.get('subdomain')
        username = data.get('username')
        password = data.get('password')
        
        response = requests.post(
            "https://api.thegoodtill.com/api/login",
            json={"subdomain": subdomain, "username": username, "password": password},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            return jsonify({"error": "Authentication failed"}), response.status_code
        
        auth_data = response.json()
        session.permanent = True
        session['token'] = auth_data.get('token')
        session['subdomain'] = subdomain
        session['username'] = username
        
        return jsonify({"success": True, "message": "Login successful"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'token' in session:
        return jsonify({"authenticated": True, "username": session.get('username')})
    return jsonify({"authenticated": False}), 401

@app.route('/api/merchant', methods=['GET'])
def get_merchant():
    if 'token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"subdomain": session.get('subdomain'), "username": session.get('username')})

@app.route('/api/data', methods=['GET'])
def get_data():
    if 'token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        days = int(request.args.get('days', 30))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        response = requests.get(
            "https://api.thegoodtill.com/api/external/get_sales",
            headers={"Authorization": f"Bearer {session['token']}", "Content-Type": "application/json"},
            params={
                'timezone': 'local',
                'from': start_date.strftime("%Y-%m-%d 00:00:00"),
                'to': end_date.strftime("%Y-%m-%d 23:59:59"),
                'limit': 1000,
                'offset': 0
            }
        )
        
        if response.status_code != 200:
            return jsonify({
                "summary": {
                    "total_revenue": 0,
                    "total_transactions": 0,
                    "avg_transaction": 0,
                    "failed_transactions": 0,
                    "payment_types": {}
                },
                "daily": [],
                "transactions": [],
                "error": f"API Error: {response.status_code}"
            })
        
        result = response.json()
        sales = result.get('data', [])
        
        total_revenue = 0.0
        successful_count = 0
        payment_types = {}
        daily_agg = {}
        transactions = []
        
        for sale in sales:
            amount = float(sale.get('total_inc_vat', 0))
            
            transactions.append({
                "id": sale.get('sales_id'),
                "transaction_code": sale.get('receipt_no', sale.get('sales_id')),
                "timestamp": sale.get('sale_date_time'),
                "amount": amount,
                "status": "SUCCESSFUL",
                "payment_type": "CARD",
                "currency": "GBP"
            })
            
            successful_count += 1
            total_revenue += amount
            
            payment_types['CARD'] = payment_types.get('CARD', 0) + amount
            
            date_str = sale.get('sale_date_time', '')
            date_key = date_str[:10] if date_str else ''
            if date_key:
                if date_key not in daily_agg:
                    daily_agg[date_key] = {'revenue': 0.0, 'count': 0}
                daily_agg[date_key]['revenue'] += amount
                daily_agg[date_key]['count'] += 1
        
        avg_transaction = total_revenue / successful_count if successful_count > 0 else 0
        
        sorted_daily = [
            {'date': d_key, 'revenue': round(d_val['revenue'], 2), 'count': d_val['count']}
            for d_key, d_val in sorted(daily_agg.items())
        ]
        
        return jsonify({
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_transactions": successful_count,
                "avg_transaction": round(avg_transaction, 2),
                "failed_transactions": 0,
                "payment_types": {k: round(v, 2) for k, v in payment_types.items()}
            },
            "daily": sorted_daily,
            "transactions": transactions[:100]
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "summary": {
                "total_revenue": 0,
                "total_transactions": 0,
                "avg_transaction": 0,
                "failed_transactions": 0,
                "payment_types": {}
            },
            "daily": [],
            "transactions": [],
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
