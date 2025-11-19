from flask import Flask, render_template_string, jsonify, request, session
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
CORS(app)

GOODTILL_API_ROOT = "https://api.thegoodtill.com/api"

# Serve the HTML
@app.route('/')
def index():
    with open('index.html', 'r') as f:
        return render_template_string(f.read())

# Login - Get JWT from GoodTill
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        subdomain = data.get('subdomain')
        username = data.get('username')
        password = data.get('password')
        
        # Call GoodTill login API
        response = requests.post(
            f"{GOODTILL_API_ROOT}/login",
            json={"subdomain": subdomain, "username": username, "password": password},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            return jsonify({"error": "Authentication failed"}), response.status_code
        
        auth_data = response.json()
        
        # Store JWT token in session
        session.permanent = True
        session['token'] = auth_data.get('token')
        session['subdomain'] = subdomain
        session['username'] = username
        
        return jsonify({"success": True, "message": "Login successful"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Logout
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

# Check if authenticated
@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'token' in session:
        return jsonify({"authenticated": True, "username": session.get('username')})
    return jsonify({"authenticated": False}), 401

# Get merchant info
@app.route('/api/merchant', methods=['GET'])
def get_merchant():
    if 'token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"subdomain": session.get('subdomain'), "username": session.get('username')})

# Get transactions
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    if 'token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        end_date = request.args.get('end_date', datetime.now().strftime("%Y-%m-%d"))
        limit = int(request.args.get('limit', 100))
        
        response = requests.get(
            f"{GOODTILL_API_ROOT}/external/get_sales_details",
            headers={"Authorization": f"Bearer {session['token']}", "Content-Type": "application/json"},
            params={'timezone': 'local', 'from': start_date, 'to': end_date, 'limit': limit, 'offset': 0}
        )
        response.raise_for_status()
        
        sales = response.json().get('data', [])
        
        # Transform to standard format
        transformed = []
        for sale in sales:
            transformed.append({
                "id": sale.get('id'),
                "transaction_code": sale.get('receipt_no', sale.get('id')),
                "timestamp": sale.get('datetime_completed') or sale.get('datetime_created'),
                "amount": float(sale.get('total', 0)),
                "status": "SUCCESSFUL" if sale.get('status') == 'completed' else "FAILED",
                "payment_type": sale.get('payments', [{}])[0].get('type', 'CARD') if sale.get('payments') else 'CARD',
                "currency": "GBP"
            })
        
        return jsonify({"items": transformed, "total": len(transformed)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Analytics summary
@app.route('/api/analytics/summary', methods=['GET'])
def get_summary():
    if 'token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        response = requests.get(
            f"{GOODTILL_API_ROOT}/external/get_sales_details",
            headers={"Authorization": f"Bearer {session['token']}", "Content-Type": "application/json"},
            params={
                'timezone': 'local',
                'from': start_date.strftime("%Y-%m-%d"),
                'to': end_date.strftime("%Y-%m-%d"),
                'limit': 1000,
                'offset': 0
            }
        )
        response.raise_for_status()
        
        sales = response.json().get('data', [])
        
        total_revenue = 0.0
        successful_count = 0
        failed_count = 0
        payment_types = {}
        
        for sale in sales:
            status = sale.get('status', '').lower()
            amount = float(sale.get('total', 0))
            
            if status == 'completed':
                successful_count += 1
                total_revenue += amount
                
                payments = sale.get('payments', [])
                if payments:
                    ptype = payments[0].get('type', 'CARD')
                    payment_types[ptype] = payment_types.get(ptype, 0) + amount
            elif status in ['voided', 'cancelled']:
                failed_count += 1
        
        avg_transaction = total_revenue / successful_count if successful_count > 0 else 0
        
        return jsonify({
            "total_revenue": round(total_revenue, 2),
            "total_transactions": successful_count,
            "avg_transaction": round(avg_transaction, 2),
            "failed_transactions": failed_count,
            "payment_types": {k: round(v, 2) for k, v in payment_types.items()},
            "period": "Last 30 days"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Daily analytics
@app.route('/api/analytics/daily', methods=['GET'])
def get_daily_analytics():
    if 'token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        days = int(request.args.get('days', 30))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        response = requests.get(
            f"{GOODTILL_API_ROOT}/external/get_sales_details",
            headers={"Authorization": f"Bearer {session['token']}", "Content-Type": "application/json"},
            params={
                'timezone': 'local',
                'from': start_date.strftime("%Y-%m-%d"),
                'to': end_date.strftime("%Y-%m-%d"),
                'limit': 1000,
                'offset': 0
            }
        )
        response.raise_for_status()
        
        sales = response.json().get('data', [])
        
        daily_agg = {}
        for sale in sales:
            if sale.get('status', '').lower() == 'completed':
                date_str = sale.get('datetime_completed') or sale.get('datetime_created', '')
                date_key = date_str[:10] if date_str else 'unknown'
                
                if date_key and date_key != 'unknown':
                    if date_key not in daily_agg:
                        daily_agg[date_key] = {'revenue': 0.0, 'count': 0}
                    daily_agg[date_key]['revenue'] += float(sale.get('total', 0))
                    daily_agg[date_key]['count'] += 1
        
        sorted_data = [
            {'date': d_key, 'revenue': round(d_val['revenue'], 2), 'count': d_val['count']}
            for d_key, d_val in sorted(daily_agg.items())
        ]
        
        return jsonify(sorted_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
