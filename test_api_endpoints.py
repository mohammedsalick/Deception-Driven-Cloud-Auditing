"""
Test API endpoints for system reset and management
"""
import requests
import json
import time

def test_api_endpoints():
    """Test the Flask API endpoints"""
    print('Testing Flask API endpoints...')
    
    base_url = 'http://localhost:5000'
    
    try:
        # Test system status
        response = requests.get(f'{base_url}/api/status', timeout=5)
        print(f'Status endpoint: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'  System status: {data.get("status", "Unknown")}')
            print(f'  Total attacks: {data.get("total_attacks", 0)}')
            print(f'  Monitoring active: {data.get("monitoring_active", False)}')
        
        # Test reset endpoint
        response = requests.post(f'{base_url}/api/reset', timeout=5)
        print(f'Reset endpoint: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'  Reset success: {data.get("success", False)}')
            print(f'  Message: {data.get("message", "No message")}')
        
        # Test statistics endpoint
        response = requests.get(f'{base_url}/api/statistics', timeout=5)
        print(f'Statistics endpoint: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            stats = data.get('attack_statistics', {})
            print(f'  Total attacks: {stats.get("total_attacks", 0)}')
            print(f'  Most targeted file: {stats.get("most_targeted_file", "None")}')
        
        # Test monitoring start endpoint
        response = requests.post(f'{base_url}/api/monitoring/start', timeout=5)
        print(f'Start monitoring endpoint: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'  Start success: {data.get("success", False)}')
            print(f'  Message: {data.get("message", "No message")}')
        
        # Test monitoring stop endpoint
        response = requests.post(f'{base_url}/api/monitoring/stop', timeout=5)
        print(f'Stop monitoring endpoint: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'  Stop success: {data.get("success", False)}')
            print(f'  Message: {data.get("message", "No message")}')
        
        print('API endpoints test completed successfully!')
        
    except requests.exceptions.ConnectionError:
        print('Flask app is not running. Please start it with: python app.py')
        return False
    except Exception as e:
        print(f'Error testing endpoints: {e}')
        return False
    
    return True

if __name__ == '__main__':
    test_api_endpoints()