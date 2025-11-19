from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import os
import traceback

app = Flask(__name__)
# Use a secure secret key in production
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
CORS(app)

# --- Configuration ---
SUMUP_API_KEY = os.getenv('SUMUP_API_KEY')
# Note: The analytics endpoints usually reside under v0.1/me/transactions
SUMUP_BASE_URL = "https://api.sumup.com/v0.1"

def get_sumup_headers():
    if not SUMUP_API_KEY:
        raise ValueError("SUMUP_API_KEY environment variable is not set.")
    return {
        "Authorization": f"Bearer {SUMUP_API_KEY}",
        "Content-Type": "application/json"
    }

# --- Helper Functions ---
def parse_sumup_timestamp(timestamp_str):
    """Parses SumUp ISO8601 timestamp safely."""
    if not timestamp_str:
        return None
    try:
        # Handle the 'Z' which python < 3.11 might struggle with depending on lib versions
        clean_ts = timestamp_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_ts)
    except ValueError:
        return None

# --- Routes ---

@app.route('/')
def index():
    return "SumUp Analytics Backend is Running"

@app.route('/api/merchant', methods=['GET'])
def get_merchant():
    """Get merchant profile information"""
    try:
        response = requests.get(
            f"{SUMUP_BASE_URL}/me",
            headers=get_sumup_headers()
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """Get transaction history with optional filters"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 100)
        
        params = {"limit": limit}
        
        if start_date:
            params['oldest_time'] = f"{start_date}T00:00:00Z"
        if end_date:
            params['newest_time'] = f"{end_date}T23:59:59Z"
        
        response = requests.get(
            f"{SUMUP_BASE_URL}/me/transactions",
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/summary', methods=['GET'])
def get_summary():
    """Get summary analytics for the last 30 days"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = {
            "limit": 1000, # Max limit to get as much data as possible
            "oldest_time": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "newest_time": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        
        response = requests.get(
            f"{SUMUP_BASE_URL}/me/transactions",
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        transactions = data.get('items', [])
        
        # Calculate summary stats
        total_revenue = 0.0
        successful_txns = []
        failed_txns = []
        
        for txn in transactions:
            status = txn.get('status', '')
            if status == 'SUCCESSFUL':
                successful_txns.append(txn)
                # Float conversion safety
                amount = float(txn.get('amount', 0))
                total_revenue += amount
            elif status == 'FAILED':
                failed_txns.append(txn)
        
        total_transactions = len(successful_txns)
        avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
        
        # Payment types breakdown
        payment_types = {}
        for txn in successful_txns:
            ptype = txn.get('payment_type', 'UNKNOWN')
            amount = float(txn.get('amount', 0))
            payment_types[ptype] = payment_types.get(ptype, 0) + amount
            
        # Round monetary values for JSON response
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
    """Get daily revenue breakdown"""
    try:
        days = int(request.args.get('days', 30))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "limit": 1000,
            "oldest_time": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "newest_time": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        
        response = requests.get(
            f"{SUMUP_BASE_URL}/me/transactions",
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        transactions = response.json().get('items', [])
        
        # Group by day
        daily_agg = {}
        for txn in transactions:
            if txn.get('status') == 'SUCCESSFUL':
                timestamp_str = txn.get('timestamp', '')
                # Simple string slicing is strictly safe only if format is ISO
                # Using slice [0:10] extracts YYYY-MM-DD
                date_key = timestamp_str[:10] if timestamp_str else 'unknown'
                
                if date_key:
                    if date_key not in daily_agg:
                        daily_agg[date_key] = {'revenue': 0.0, 'count': 0}
                    
                    daily_agg[date_key]['revenue'] += float(txn.get('amount', 0))
                    daily_agg[date_key]['count'] += 1
        
        # Format for chart consumption
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
    """Get hourly distribution of transactions (Heatmap data)"""
    try:
        days = int(request.args.get('days', 7))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "limit": 1000,
            "oldest_time": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "newest_time": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        
        response = requests.get(
            f"{SUMUP_BASE_URL}/me/transactions",
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        transactions = response.json().get('items', [])
        
        # Initialize 24 hours
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
    """Get breakdown by card type (Visa, Mastercard, etc)"""
    try:
        days = int(request.args.get('days', 30))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "limit": 1000,
            "oldest_time": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "newest_time": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        
        response = requests.get(
            f"{SUMUP_BASE_URL}/me/transactions",
            headers=get_sumup_headers(),
            params=params
        )
        response.raise_for_status()
        transactions = response.json().get('items', [])
        
        card_types = {}
        for txn in transactions:
            if txn.get('status') == 'SUCCESSFUL':
                # Depending on the API version, this might be in 'card' object or root
                # Safe access pattern:
                c_type = txn.get('card_type')
                if not c_type and 'card' in txn:
                    c_type = txn['card'].get('type')
                
                c_type = c_type or 'UNKNOWN'
                
                if c_type not in card_types:
                    card_types[c_type] = {'count': 0, 'revenue': 0.0}
                
                card_types[c_type]['count'] += 1
                card_types[c_type]['revenue'] += float(txn.get('amount', 0))
        
        # Round values
        for k in card_types:
            card_types[k]['revenue'] = round(card_types[k]['revenue'], 2)

        return jsonify(card_types)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-sumup', methods=['GET'])
def test_sumup():
    """Test Connectivity"""
    try:
        # Test 1: Check merchant endpoint
        resp_me = requests.get(f"{SUMUP_BASE_URL}/me", headers=get_sumup_headers())
        
        # Test 2: Check transactions endpoint (minimal payload)
        resp_txn = requests.get(f"{SUMUP_BASE_URL}/me/transactions?limit=1", headers=get_sumup_headers())
        
        return jsonify({
            "auth_status": "OK" if resp_me.ok else "FAILED",
            "merchant_code": resp_me.status_code,
            "transaction_code": resp_txn.status_code,
            "merchant_data_preview": resp_me.json() if resp_me.ok else resp_me.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # In development, debug=True is helpful, but ensure it's False in prod
    app.run(debug=True, host='0.0.0.0', port=port)
