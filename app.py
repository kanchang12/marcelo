from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# SumUp API Configuration - FROM ENVIRONMENT
SUMUP_API_KEY = os.getenv('SUMUP_API_KEY')
SUMUP_BASE_URL = "https://api.sumup.com/v0.1"

def get_sumup_headers():
    return {
        "Authorization": f"Bearer {SUMUP_API_KEY}",
        "Content-Type": "application/json"
    }

# API Routes
@app.route('/')
def index():
    return render_template('index.html')

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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """Get transaction history with optional filters"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 100)
        
        params = {
            "limit": limit
        }
        
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
        
        data = response.json()
        return jsonify(data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/summary', methods=['GET'])
def get_summary():
    """Get summary analytics"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
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
        
        # Calculate summary stats
        total_revenue = sum(txn['amount'] for txn in transactions if txn.get('status') == 'SUCCESSFUL')
        total_transactions = len([txn for txn in transactions if txn.get('status') == 'SUCCESSFUL'])
        avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
        
        # Failed transactions
        failed_count = len([txn for txn in transactions if txn.get('status') == 'FAILED'])
        
        # Payment types breakdown
        payment_types = {}
        for txn in transactions:
            if txn.get('status') == 'SUCCESSFUL':
                ptype = txn.get('payment_type', 'UNKNOWN')
                payment_types[ptype] = payment_types.get(ptype, 0) + txn.get('amount', 0)
        
        return jsonify({
            "total_revenue": total_revenue,
            "total_transactions": total_transactions,
            "avg_transaction": avg_transaction,
            "failed_transactions": failed_count,
            "payment_types": payment_types,
            "period": "Last 30 days"
        })
        
    except Exception as e:
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
        daily_data = {}
        for txn in transactions:
            if txn.get('status') == 'SUCCESSFUL':
                timestamp = txn.get('timestamp', '')
                date = timestamp[:10] if timestamp else ''
                if date:
                    if date not in daily_data:
                        daily_data[date] = {
                            'revenue': 0,
                            'count': 0
                        }
                    daily_data[date]['revenue'] += txn.get('amount', 0)
                    daily_data[date]['count'] += 1
        
        # Sort by date
        sorted_data = [
            {
                'date': date,
                'revenue': data['revenue'],
                'count': data['count']
            }
            for date, data in sorted(daily_data.items())
        ]
        
        return jsonify(sorted_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/hourly', methods=['GET'])
def get_hourly_analytics():
    """Get hourly distribution of transactions"""
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
        
        # Group by hour
        hourly_data = {str(i): {'revenue': 0, 'count': 0} for i in range(24)}
        
        for txn in transactions:
            if txn.get('status') == 'SUCCESSFUL':
                timestamp = txn.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        hour = str(dt.hour)
                        hourly_data[hour]['revenue'] += txn.get('amount', 0)
                        hourly_data[hour]['count'] += 1
                    except:
                        pass
        
        sorted_data = [
            {
                'hour': int(hour),
                'revenue': data['revenue'],
                'count': data['count']
            }
            for hour, data in sorted(hourly_data.items(), key=lambda x: int(x[0]))
        ]
        
        return jsonify(sorted_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/card-types', methods=['GET'])
def get_card_types():
    """Get breakdown by card type"""
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
                card_type = txn.get('card_type', 'UNKNOWN')
                if card_type not in card_types:
                    card_types[card_type] = {
                        'count': 0,
                        'revenue': 0
                    }
                card_types[card_type]['count'] += 1
                card_types[card_type]['revenue'] += txn.get('amount', 0)
        
        return jsonify(card_types)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug', methods=['GET'])
def debug():
    """Debug endpoint to check configuration"""
    return jsonify({
        "api_key_set": bool(SUMUP_API_KEY),
        "api_key_prefix": SUMUP_API_KEY[:15] + "..." if SUMUP_API_KEY else "NOT SET",
        "base_url": SUMUP_BASE_URL
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
