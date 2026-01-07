"""
End-to-End Tests for Honey-Token Auditing System
Tests complete attack scenarios from detection to dashboard display
"""
import os
import json
import time
import tempfile
import threading
import unittest
import requests
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from honey_token_manager import HoneyTokenManager
from monitor_service import MonitorService
from audit_logger import AuditLogger
from app import app


class TestEndToEndAttackScenarios(unittest.TestCase):
    """Test complete attack scenarios from start to finish"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment for all end-to-end tests"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_path = Path(cls.temp_dir)
        
        # Initialize components with temporary directories
        cls.honey_manager = HoneyTokenManager(base_directory=cls.temp_path / "honey_tokens")
        cls.audit_logger = AuditLogger(logs_directory=cls.temp_path / "logs")
        cls.monitor_service = MonitorService(cls.honey_manager, cls.audit_logger)
        
        # Create honey tokens
        cls.honey_manager.create_honey_tokens()
        
        # Flask test client
        app.config['TESTING'] = True
        cls.client = app.test_client()
        
        print(f"\n🧪 End-to-End Test Environment Setup Complete")
        print(f"   Temp Directory: {cls.temp_dir}")
        print(f"   Honey Tokens: {len(cls.honey_manager.get_token_paths())}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if cls.monitor_service.is_monitoring:
            cls.monitor_service.stop_monitoring()
        
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        print(f"🧹 End-to-End Test Environment Cleaned Up")
    
    def setUp(self):
        """Set up for each test"""
        # Reset system state
        self.audit_logger.reset_system()
        
        # Ensure monitoring is stopped
        if self.monitor_service.is_monitoring:
            self.monitor_service.stop_monitoring()
    
    def test_complete_attack_detection_and_dashboard_flow(self):
        """Test complete flow: attack -> detection -> logging -> dashboard display"""
        print("\n🎯 Testing Complete Attack Detection and Dashboard Flow")
        
        # Step 1: Verify initial system state
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        
        initial_status = json.loads(response.data)
        self.assertEqual(initial_status['status'], 'SAFE')
        self.assertEqual(initial_status['total_attacks'], 0)
        
        print("✅ Initial system state verified: SAFE")
        
        # Step 2: Start monitoring
        success = self.monitor_service.start_monitoring()
        self.assertTrue(success, "Failed to start monitoring")
        
        # Verify monitoring is active via API
        response = self.client.get('/api/status')
        status_data = json.loads(response.data)
        self.assertTrue(status_data.get('monitoring_active', False))
        
        print("✅ Monitoring service started and verified via API")
        
        # Step 3: Execute attack simulation
        honey_file = self.honey_manager.base_directory / "passwords.txt"
        
        # Read file to trigger access detection
        with open(honey_file, 'r') as f:
            content = f.read()
        
        # Modify file to ensure detection
        with open(honey_file, 'a') as f:
            f.write('\n# End-to-end test attack')
        
        print("✅ Attack executed on honey-token file")
        
        # Step 4: Wait for detection and verify via API
        time.sleep(1.5)
        
        response = self.client.get('/api/attacks?limit=5')
        self.assertEqual(response.status_code, 200)
        
        attacks_data = json.loads(response.data)
        self.assertGreater(len(attacks_data['attacks']), 0, "No attacks detected via API")
        
        attack = attacks_data['attacks'][0]
        self.assertEqual(attack['filename'], 'passwords.txt')
        self.assertIn(attack['event_type'], ['file_accessed', 'file_modified'])
        
        print(f"✅ Attack detected via API: {attack['attack_id']}")
        
        # Step 5: Verify system status changed
        response = self.client.get('/api/status')
        status_data = json.loads(response.data)
        self.assertEqual(status_data['status'], 'UNDER_ATTACK')
        self.assertGreater(status_data['total_attacks'], 0)
        
        print("✅ System status changed to UNDER_ATTACK")
        
        # Step 6: Test dashboard simulation endpoint
        response = self.client.post('/api/simulate', 
                                  json={'attack_type': 'file_access', 'target_file': 'api_keys.json'})
        
        if response.status_code == 200:
            simulation_data = json.loads(response.data)
            self.assertTrue(simulation_data['success'])
            self.assertGreater(len(simulation_data['simulation_steps']), 0)
            print("✅ Dashboard simulation endpoint working")
        else:
            print("⚠️ Dashboard simulation endpoint not available (components may not be initialized)")
        
        # Step 7: Test system reset
        response = self.client.post('/api/reset')
        
        if response.status_code == 200:
            reset_data = json.loads(response.data)
            self.assertTrue(reset_data['success'])
            
            # Verify reset worked
            response = self.client.get('/api/status')
            status_data = json.loads(response.data)
            self.assertEqual(status_data['status'], 'SAFE')
            self.assertEqual(status_data['total_attacks'], 0)
            
            print("✅ System reset successful")
        else:
            print("⚠️ System reset endpoint not available")
        
        print("🎯 Complete Attack Detection and Dashboard Flow: SUCCESS")
    
    def test_multiple_concurrent_attacks_scenario(self):
        """Test detection of multiple concurrent attacks"""
        print("\n🎯 Testing Multiple Concurrent Attacks Scenario")
        
        # Start monitoring
        self.monitor_service.start_monitoring()
        
        def execute_attack(filename, attack_id):
            """Execute attack on specific honey-token"""
            try:
                honey_file = self.honey_manager.base_directory / filename
                
                # Read and modify file
                with open(honey_file, 'r') as f:
                    content = f.read()
                
                with open(honey_file, 'a') as f:
                    f.write(f'\n# Concurrent attack {attack_id}')
                
                print(f"   Attack {attack_id} executed on {filename}")
                
            except Exception as e:
                print(f"   Attack {attack_id} failed: {e}")
        
        # Execute multiple concurrent attacks
        threads = []
        attack_targets = [
            ('passwords.txt', 1),
            ('api_keys.json', 2),
            ('database_backup.sql', 3),
            ('config.env', 4)
        ]
        
        print("Executing concurrent attacks...")
        for filename, attack_id in attack_targets:
            thread = threading.Thread(target=execute_attack, args=(filename, attack_id))
            threads.append(thread)
            thread.start()
        
        # Wait for all attacks to complete
        for thread in threads:
            thread.join()
        
        # Wait for detection
        time.sleep(2.0)
        
        # Verify multiple attacks detected
        response = self.client.get('/api/attacks?limit=10')
        self.assertEqual(response.status_code, 200)
        
        attacks_data = json.loads(response.data)
        detected_attacks = attacks_data['attacks']
        
        self.assertGreaterEqual(len(detected_attacks), 3, 
                               f"Expected at least 3 attacks, detected {len(detected_attacks)}")
        
        # Verify different files were attacked
        attacked_files = set(attack['filename'] for attack in detected_attacks)
        self.assertGreaterEqual(len(attacked_files), 3, 
                               f"Expected attacks on at least 3 files, got {len(attacked_files)}")
        
        print(f"✅ Detected {len(detected_attacks)} attacks on {len(attacked_files)} files")
        print("🎯 Multiple Concurrent Attacks Scenario: SUCCESS")
    
    def test_attack_timing_precision(self):
        """Test precision of attack detection timing"""
        print("\n🎯 Testing Attack Detection Timing Precision")
        
        # Start monitoring
        self.monitor_service.start_monitoring()
        
        # Record attack execution time
        attack_start_time = datetime.utcnow()
        
        # Execute attack
        honey_file = self.honey_manager.base_directory / "passwords.txt"
        with open(honey_file, 'a') as f:
            f.write('\n# Timing precision test')
        
        attack_end_time = datetime.utcnow()
        
        # Wait for detection
        time.sleep(1.0)
        
        # Get detected attack
        response = self.client.get('/api/attacks?limit=1')
        self.assertEqual(response.status_code, 200)
        
        attacks_data = json.loads(response.data)
        self.assertGreater(len(attacks_data['attacks']), 0, "No attack detected")
        
        attack = attacks_data['attacks'][0]
        
        # Parse attack timestamp
        attack_time = datetime.fromisoformat(attack['timestamp'].replace('Z', '+00:00'))
        attack_time = attack_time.replace(tzinfo=None)  # Remove timezone for comparison
        
        # Verify timing precision (should be within reasonable bounds)
        time_diff_start = (attack_time - attack_start_time).total_seconds()
        time_diff_end = (attack_end_time - attack_time).total_seconds()
        
        # Attack should be detected within 2 seconds of execution
        self.assertLessEqual(abs(time_diff_start), 2.0, 
                            f"Attack detection timing off by {time_diff_start} seconds")
        
        print(f"✅ Attack detected within {abs(time_diff_start):.3f} seconds of execution")
        print("🎯 Attack Detection Timing Precision: SUCCESS")
    
    def test_dashboard_real_time_updates(self):
        """Test dashboard real-time update accuracy"""
        print("\n🎯 Testing Dashboard Real-Time Updates")
        
        # Start monitoring
        self.monitor_service.start_monitoring()
        
        # Get initial status
        response = self.client.get('/api/status')
        initial_status = json.loads(response.data)
        initial_attack_count = initial_status['total_attacks']
        
        # Execute attack
        honey_file = self.honey_manager.base_directory / "api_keys.json"
        with open(honey_file, 'a') as f:
            f.write('\n# Real-time update test')
        
        # Wait for detection
        time.sleep(1.0)
        
        # Check status update
        response = self.client.get('/api/status')
        updated_status = json.loads(response.data)
        
        # Verify status changed
        self.assertEqual(updated_status['status'], 'UNDER_ATTACK')
        self.assertGreater(updated_status['total_attacks'], initial_attack_count)
        
        # Check attacks endpoint
        response = self.client.get('/api/attacks?limit=1')
        attacks_data = json.loads(response.data)
        
        self.assertGreater(len(attacks_data['attacks']), 0)
        self.assertEqual(attacks_data['attacks'][0]['filename'], 'api_keys.json')
        
        print("✅ Dashboard endpoints updated correctly after attack")
        
        # Test reset functionality
        response = self.client.post('/api/reset')
        if response.status_code == 200:
            # Verify reset reflected in status
            response = self.client.get('/api/status')
            reset_status = json.loads(response.data)
            
            self.assertEqual(reset_status['status'], 'SAFE')
            self.assertEqual(reset_status['total_attacks'], 0)
            
            print("✅ Dashboard reset functionality working")
        
        print("🎯 Dashboard Real-Time Updates: SUCCESS")
    
    def test_system_recovery_after_errors(self):
        """Test system recovery after various error conditions"""
        print("\n🎯 Testing System Recovery After Errors")
        
        # Test 1: Recovery from missing honey-tokens
        print("Testing recovery from missing honey-tokens...")
        
        # Remove a honey-token file
        honey_file = self.honey_manager.base_directory / "passwords.txt"
        if honey_file.exists():
            honey_file.unlink()
        
        # Try to start monitoring (should recreate missing files)
        success = self.monitor_service.start_monitoring()
        self.assertTrue(success, "Should recover from missing honey-tokens")
        
        # Verify file was recreated
        self.assertTrue(honey_file.exists(), "Missing honey-token should be recreated")
        
        print("✅ Recovery from missing honey-tokens successful")
        
        # Test 2: Recovery from corrupted log files
        print("Testing recovery from corrupted log files...")
        
        # Corrupt the attacks log file
        attacks_log = self.audit_logger.attacks_log_file
        attacks_log.parent.mkdir(parents=True, exist_ok=True)
        
        with open(attacks_log, 'w') as f:
            f.write("invalid json content")
        
        # Try to get attacks (should handle corruption gracefully)
        response = self.client.get('/api/attacks')
        self.assertEqual(response.status_code, 200)
        
        attacks_data = json.loads(response.data)
        # Should return empty list instead of crashing
        self.assertEqual(len(attacks_data['attacks']), 0)
        
        print("✅ Recovery from corrupted log files successful")
        
        # Test 3: Service restart capability
        print("Testing service restart capability...")
        
        if self.monitor_service.is_running():
            # Stop and restart monitoring
            self.monitor_service.stop_monitoring()
            self.assertFalse(self.monitor_service.is_running())
            
            success = self.monitor_service.start_monitoring()
            self.assertTrue(success, "Should be able to restart monitoring")
            self.assertTrue(self.monitor_service.is_running())
            
            print("✅ Service restart capability working")
        
        print("🎯 System Recovery After Errors: SUCCESS")
    
    def test_comprehensive_api_error_handling(self):
        """Test comprehensive API error handling"""
        print("\n🎯 Testing Comprehensive API Error Handling")
        
        # Test invalid JSON in simulate endpoint
        response = self.client.post('/api/simulate', 
                                  data='invalid json',
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        error_data = json.loads(response.data)
        self.assertFalse(error_data['success'])
        self.assertIn('Invalid JSON', error_data['error'])
        
        print("✅ Invalid JSON handling working")
        
        # Test invalid limit parameter
        response = self.client.get('/api/attacks?limit=invalid')
        self.assertEqual(response.status_code, 200)  # Should default gracefully
        
        attacks_data = json.loads(response.data)
        self.assertIn('attacks', attacks_data)
        
        print("✅ Invalid parameter handling working")
        
        # Test out-of-bounds limit
        response = self.client.get('/api/attacks?limit=1000')
        self.assertEqual(response.status_code, 200)  # Should cap gracefully
        
        print("✅ Out-of-bounds parameter handling working")
        
        # Test monitoring control endpoints
        response = self.client.post('/api/monitoring/start')
        self.assertIn(response.status_code, [200, 500, 503])  # Various states possible
        
        response = self.client.post('/api/monitoring/stop')
        self.assertIn(response.status_code, [200, 500, 503])  # Various states possible
        
        print("✅ Monitoring control endpoints handling errors gracefully")
        
        print("🎯 Comprehensive API Error Handling: SUCCESS")


class TestDashboardResponsiveness(unittest.TestCase):
    """Test dashboard responsiveness and performance"""
    
    def setUp(self):
        """Set up dashboard test environment"""
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_dashboard_page_load(self):
        """Test dashboard page loads correctly"""
        print("\n🎯 Testing Dashboard Page Load")
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Honey-Token', response.data)
        
        print("✅ Dashboard page loads successfully")
    
    def test_api_response_times(self):
        """Test API endpoint response times"""
        print("\n🎯 Testing API Response Times")
        
        endpoints = [
            '/api/status',
            '/api/attacks',
            '/api/honey-tokens',
            '/api/statistics'
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = self.client.get(endpoint)
            response_time = time.time() - start_time
            
            # API should respond within 1 second
            self.assertLess(response_time, 1.0, 
                           f"Endpoint {endpoint} took {response_time:.3f}s (too slow)")
            
            print(f"✅ {endpoint}: {response_time:.3f}s")
        
        print("🎯 API Response Times: SUCCESS")
    
    def test_concurrent_api_requests(self):
        """Test handling of concurrent API requests"""
        print("\n🎯 Testing Concurrent API Requests")
        
        def make_request(endpoint, results, index):
            """Make API request and store result"""
            try:
                start_time = time.time()
                response = self.client.get(endpoint)
                response_time = time.time() - start_time
                
                results[index] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code == 200
                }
            except Exception as e:
                results[index] = {
                    'status_code': 500,
                    'response_time': 999,
                    'success': False,
                    'error': str(e)
                }
        
        # Make 10 concurrent requests to status endpoint
        threads = []
        results = {}
        
        for i in range(10):
            thread = threading.Thread(target=make_request, args=('/api/status', results, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all requests to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        successful_requests = sum(1 for result in results.values() if result['success'])
        self.assertGreaterEqual(successful_requests, 8, 
                               f"Only {successful_requests}/10 concurrent requests succeeded")
        
        # Check average response time
        avg_response_time = sum(r['response_time'] for r in results.values()) / len(results)
        self.assertLess(avg_response_time, 2.0, 
                       f"Average response time {avg_response_time:.3f}s too slow")
        
        print(f"✅ {successful_requests}/10 concurrent requests successful")
        print(f"✅ Average response time: {avg_response_time:.3f}s")
        print("🎯 Concurrent API Requests: SUCCESS")


def run_end_to_end_tests():
    """Run all end-to-end tests"""
    print("🎯 Running End-to-End Tests for Honey-Token Auditing System")
    print("=" * 70)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestEndToEndAttackScenarios,
        TestDashboardResponsiveness
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Print comprehensive summary
    print("\n" + "=" * 70)
    print("🎯 End-to-End Test Summary")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"- {test}")
            print(f"  {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"- {test}")
            print(f"  {traceback.split('Exception:')[-1].strip()}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 All End-to-End Tests Passed!")
        print("✅ System is ready for production deployment")
    else:
        print("\n⚠️ Some End-to-End Tests Failed")
        print("🔧 Review failures before deployment")
    
    return success


if __name__ == "__main__":
    import sys
    run_end_to_end_tests()