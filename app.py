from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import os
import traceback

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
CORS(app)

# --- Configuration ---
SUMUP_API_KEY = os.getenv('SUMUP_API_KEY')
SUMUP_BASE_URL = "https://api.sumup.com/v0.1"

# Simple cache for the merchant code so we don't fetch it every single request
CACHED_MERCHANT_CODE = None

def get_sumup_headers():
    if not SUMUP_API_KEY:
        raise ValueError("SUMUP_API_KEY environment variable is not set.")
    return {
        "Authorization": f"Bearer {SUMUP_API_KEY}",
        "Content-Type": "application/json"
    }

def get_merchant_code():
    """
    Fetches the Merchant Code from SumUp /me endpoint.
    Uses the cached value if available to save API calls.
    """
    global CACHED_MERCHANT_CODE
    
    if CACHED_MERCHANT_CODE:
        return CACHED_MERCHANT_CODE
        
    try:
        # We know this endpoint works because your logs showed a 200 OK for it
        response = requests.get(
            f"{SUMUP_BASE_URL}/me", 
            headers=get_sumup_headers()
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract the code (e.g., "MH4H92C7")
        code = data.get('merchant_code')
        if not code:
            raise ValueError("Could not find merchant_code in /me response")
            
        CACHED_MERCHANT_CODE = code
        return code
    except Exception as e:
        print(f"Failed to fetch merchant code: {e}")
        raise

# --- Helper Functions ---
def parse_sumup_timestamp(timestamp_str):
    if not timestamp_str:
        return None
    try:
        clean_ts = timestamp_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_ts)
    except ValueError:
        return None

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/merchant', methods=['GET'])
def get_merchant():
    try:
        # We call the API directly here to get fresh data
        response = requests.get(
            f"{SUMUP_BASE_URL}/me",
            headers=get_sumup_headers()
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    try:
        # 1. Get the Merchant Code first
        merchant_code = get_merchant_code()
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 100)
        
        params = {"limit": limit}
        
        if start_date:
            params['oldest_time'] = f"{start_date}T00:00:00Z"
        if end_date:
            params['newest_time'] = f"{end_date}T23:59:59Z"
        
        # 2. Use the explicit URL structure
        url = f"{SUMUP_BASE_URL}/merchants/{merchant_code}/transactions"
        
        response = requests.get(
            url,
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        return jsonify(response.json())
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/summary', methods=['GET'])
def get_summary():
    try:
        # 1. Get the Merchant Code first
        merchant_code = get_merchant_code()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = {
            "limit": 1000,
            "oldest_time": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "newest_time": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        
        # 2. Use the explicit URL structure
        url = f"{SUMUP_BASE_URL}/merchants/{merchant_code}/transactions"
        
        response = requests.get(
            url,
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        transactions = data.get('items', [])
        
        total_revenue = 0.0
        successful_txns = []
        failed_txns = []
        
        for txn in transactions:
            status = txn.get('status', '')
            if status == 'SUCCESSFUL':
                successful_txns.append(txn)
                amount = float(txn.get('amount', 0))
                total_revenue += amount
            elif status == 'FAILED':
                failed_txns.append(txn)
        
        total_transactions = len(successful_txns)
        avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
        
        payment_types = {}
        for txn in successful_txns:
            ptype = txn.get('payment_type', 'UNKNOWN')
            amount = float(txn.get('amount', 0))
            payment_types[ptype] = payment_types.get(ptype, 0) + amount
            
        payment_types = {k: round(v, 2) for k, v in payment_types.items()}
        
        result = {
            "total_revenue": round(total_revenue, 2),
            "total_transactions": total_transactions,
            "avg_transaction": round(avg_transaction, 2),
            "failed_transactions": len(failed_txns),
            "payment_types": payment_types,
            "period": "Last 30 days"
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/daily', methods=['GET'])
def get_daily_analytics():
    try:
        # 1. Get the Merchant Code first
        merchant_code = get_merchant_code()

        days = int(request.args.get('days', 30))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "limit": 1000,
            "oldest_time": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "newest_time": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        
        # 2. Use the explicit URL structure
        url = f"{SUMUP_BASE_URL}/merchants/{merchant_code}/transactions"

        response = requests.get(
            url,
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        transactions = response.json().get('items', [])
        
        daily_agg = {}
        for txn in transactions:
            if txn.get('status') == 'SUCCESSFUL':
                timestamp_str = txn.get('timestamp', '')
                date_key = timestamp_str[:10] if timestamp_str else 'unknown'
                
                if date_key:
                    if date_key not in daily_agg:
                        daily_agg[date_key] = {'revenue': 0.0, 'count': 0}
                    
                    daily_agg[date_key]['revenue'] += float(txn.get('amount', 0))
                    daily_agg[date_key]['count'] += 1
        
        sorted_data = [
            {
                'date': d_key,
                'revenue': round(d_val['revenue'], 2),
                'count': d_val['count']
            }
            for d_key, d_val in sorted(daily_agg.items())
        ]
        
        return jsonify(sorted_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/hourly', methods=['GET'])
def get_hourly_analytics():
    try:
        # 1. Get the Merchant Code first
        merchant_code = get_merchant_code()

        days = int(request.args.get('days', 7))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "limit": 1000,
            "oldest_time": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "newest_time": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        
        # 2. Use the explicit URL structure
        url = f"{SUMUP_BASE_URL}/merchants/{merchant_code}/transactions"

        response = requests.get(
            url,
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        transactions = response.json().get('items', [])
        
        hourly_agg = {str(i): {'revenue': 0.0, 'count': 0} for i in range(24)}
        
        for txn in transactions:
            if txn.get('status') == 'SUCCESSFUL':
                dt = parse_sumup_timestamp(txn.get('timestamp'))
                if dt:
                    hour_key = str(dt.hour)
                    hourly_agg[hour_key]['revenue'] += float(txn.get('amount', 0))
                    hourly_agg[hour_key]['count'] += 1
        
        sorted_data = [
            {
                'hour': int(h_key),
                'revenue': round(h_val['revenue'], 2),
                'count': h_val['count']
            }
            for h_key, h_val in sorted(hourly_agg.items(), key=lambda x: int(x[0]))
        ]
        
        return jsonify(sorted_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/card-types', methods=['GET'])
def get_card_types():
    try:
        # 1. Get the Merchant Code first
        merchant_code = get_merchant_code()

        days = int(request.args.get('days', 30))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "limit": 1000,
            "oldest_time": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "newest_time": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        
        # 2. Use the explicit URL structure
        url = f"{SUMUP_BASE_URL}/merchants/{merchant_code}/transactions"

        response = requests.get(
            url,
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        transactions = response.json().get('items', [])
        
        card_types = {}
        for txn in transactions:
            if txn.get('status') == 'SUCCESSFUL':
                c_type = txn.get('card_type')
                if not c_type and 'card' in txn:
                    c_type = txn['card'].get('type')
                
                c_type = c_type or 'UNKNOWN'
                
                if c_type not in card_types:
                    card_types[c_type] = {'count': 0, 'revenue': 0.0}
                
                card_types[c_type]['count'] += 1
                card_types[c_type]['revenue'] += float(txn.get('amount', 0))
        
        for k in card_types:
            card_types[k]['revenue'] = round(card_types[k]['revenue'], 2)

        return jsonify(card_types)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-sumup', methods=['GET'])
def test_sumup():
    try:
        # Test 1: Check merchant endpoint
        resp_me = requests.get(f"{SUMUP_BASE_URL}/me", headers=get_sumup_headers())
        
        # Extract Merchant Code if successful
        m_code = "UNKNOWN"
        if resp_me.ok:
            m_code = resp_me.json().get('merchant_code', 'UNKNOWN')
            
        # Test 2: Check transactions using explicit URL
        txn_url = f"{SUMUP_BASE_URL}/merchants/{m_code}/transactions?limit=1"
        resp_txn = requests.get(txn_url, headers=get_sumup_headers())
        
        return jsonify({
            "merchant_fetch_status": resp_me.status_code,
            "merchant_code_found": m_code,
            "transaction_fetch_status": resp_txn.status_code,
            "transaction_url_used": txn_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
