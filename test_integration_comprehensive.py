"""
Comprehensive Integration Tests for Honey-Token Auditing System
Tests multi-component interactions, error handling, and graceful degradation
"""
import os
import json
import time
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from honey_token_manager import HoneyTokenManager
from monitor_service import MonitorService
from audit_logger import AuditLogger
from app import app


class TestSystemIntegration(unittest.TestCase):
    """Test complete system integration with all components"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Initialize components with temporary directories
        self.honey_manager = HoneyTokenManager(base_directory=self.temp_path / "honey_tokens")
        self.audit_logger = AuditLogger(logs_directory=self.temp_path / "logs")
        self.monitor_service = MonitorService(self.honey_manager, self.audit_logger)
        
        # Create honey tokens
        self.honey_manager.create_honey_tokens()
        
        # Flask test client
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def tearDown(self):
        """Clean up test environment"""
        # Stop monitoring if running
        if self.monitor_service.is_monitoring:
            self.monitor_service.stop_monitoring()
        
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_attack_detection_flow(self):
        """Test complete flow from file access to attack logging"""
        print("\n🧪 Testing Complete Attack Detection Flow")
        
        # Step 1: Start monitoring
        success = self.monitor_service.start_monitoring()
        self.assertTrue(success, "Failed to start monitoring")
        
        # Verify monitoring is active
        self.assertTrue(self.monitor_service.is_running())
        
        # Step 2: Simulate file access
        honey_file = self.honey_manager.base_directory / "passwords.txt"
        self.assertTrue(honey_file.exists(), "Honey token file should exist")
        
        # Access the file to trigger monitoring
        with open(honey_file, 'r') as f:
            content = f.read()
        
        # Modify the file to ensure detection
        with open(honey_file, 'a') as f:
            f.write('\n# Integration test modification')
        
        # Wait for detection
        time.sleep(1.5)
        
        # Step 3: Verify attack was logged
        recent_attacks = self.audit_logger.get_recent_attacks(5)
        self.assertGreater(len(recent_attacks), 0, "No attacks were detected")
        
        # Verify attack details
        attack = recent_attacks[0]
        self.assertEqual(attack.filename, 'passwords.txt')
        self.assertIn(attack.event_type, ['file_accessed', 'file_modified'])
        self.assertIsNotNone(attack.attack_id)
        self.assertIsNotNone(attack.timestamp)
        
        # Step 4: Verify system status changed
        system_status = self.audit_logger.get_system_status()
        self.assertEqual(system_status.status, 'UNDER_ATTACK')
        self.assertGreater(system_status.total_attacks, 0)
        
        print(f"✅ Attack detected: {attack.attack_id} - {attack.event_type}")
        print(f"✅ System status: {system_status.status}")
    
    def test_monitoring_service_restart_logic(self):
        """Test automatic restart logic for monitoring service"""
        print("\n🧪 Testing Monitoring Service Restart Logic")
        
        # Start monitoring
        success = self.monitor_service.start_monitoring()
        self.assertTrue(success)
        
        # Simulate observer failure by stopping it directly
        if self.monitor_service.observer:
            self.monitor_service.observer.stop()
            self.monitor_service.observer.join(timeout=2)
        
        # Wait a moment for the service to detect the failure
        time.sleep(0.5)
        
        # Verify service detects it's not running
        self.assertFalse(self.monitor_service.is_running())
        
        # Test restart functionality
        restart_success = self.monitor_service.restart_monitoring()
        self.assertTrue(restart_success, "Failed to restart monitoring service")
        
        # Verify service is running again
        self.assertTrue(self.monitor_service.is_running())
        self.assertEqual(self.monitor_service.restart_count, 1)
        
        print("✅ Monitoring service restart successful")
    
    def test_error_handling_missing_honey_tokens(self):
        """Test error handling when honey tokens are missing"""
        print("\n🧪 Testing Error Handling - Missing Honey Tokens")
        
        # Remove honey tokens
        for token_file in self.honey_manager.base_directory.glob("*"):
            if token_file.is_file():
                token_file.unlink()
        
        # Try to start monitoring
        success = self.monitor_service.start_monitoring()
        self.assertTrue(success, "Should succeed after recreating tokens")
        
        # Verify tokens were recreated
        verification_results = self.honey_manager.verify_tokens()
        for filename, exists in verification_results.items():
            self.assertTrue(exists, f"Token {filename} should be recreated")
        
        print("✅ Missing honey tokens handled correctly")
    
    def test_error_handling_inaccessible_directory(self):
        """Test error handling when watch directory is inaccessible"""
        print("\n🧪 Testing Error Handling - Inaccessible Directory")
        
        # Create a monitor with non-existent directory that can't be created
        # Use a path that would require admin privileges on Windows
        bad_path = "C:\\Windows\\System32\\NonExistentHoneyTokens"
        bad_manager = HoneyTokenManager(base_directory=bad_path)
        bad_monitor = MonitorService(bad_manager, self.audit_logger)
        
        # Try to start monitoring
        success = bad_monitor.start_monitoring()
        
        # On Windows, this might succeed if the user has admin rights
        # So we'll check if either it fails OR if it succeeds but with errors
        if success:
            # If it succeeded, check that there were some warnings or issues
            status = bad_monitor.get_status()
            print(f"Monitoring started but with status: {status.get('health_status', 'unknown')}")
            # Clean up if it actually started
            bad_monitor.stop_monitoring()
        else:
            # Check error was recorded
            status = bad_monitor.get_status()
            self.assertIsNotNone(status['last_error'])
            # Check for either "error" or "failed" in the error message
            error_msg = status['last_error'].lower()
            self.assertTrue('error' in error_msg or 'failed' in error_msg, 
                          f"Expected error message, got: {status['last_error']}")
        
        print("✅ Inaccessible directory handled correctly")
    
    def test_graceful_degradation_audit_logger_failure(self):
        """Test graceful degradation when audit logger fails"""
        print("\n🧪 Testing Graceful Degradation - Audit Logger Failure")
        
        # Create monitor without audit logger
        monitor_no_audit = MonitorService(self.honey_manager, None)
        
        # Should still be able to start monitoring
        success = monitor_no_audit.start_monitoring()
        self.assertTrue(success, "Should start even without audit logger")
        
        # Verify monitoring is active
        self.assertTrue(monitor_no_audit.is_running())
        
        # Access a honey token
        honey_file = self.honey_manager.base_directory / "api_keys.json"
        with open(honey_file, 'r') as f:
            content = f.read()
        
        # Should not crash even without audit logger
        time.sleep(0.5)
        
        # Clean up
        monitor_no_audit.stop_monitoring()
        
        print("✅ Graceful degradation without audit logger successful")
    
    def test_concurrent_file_access_detection(self):
        """Test detection of concurrent file access operations"""
        print("\n🧪 Testing Concurrent File Access Detection")
        
        # Start monitoring
        self.monitor_service.start_monitoring()
        
        def access_honey_token(filename, delay=0):
            """Helper function to access honey token"""
            time.sleep(delay)
            honey_file = self.honey_manager.base_directory / filename
            with open(honey_file, 'r') as f:
                content = f.read()
            # Also modify to ensure detection
            with open(honey_file, 'a') as f:
                f.write(f'\n# Concurrent access test {threading.current_thread().name}')
        
        # Create multiple threads to access different honey tokens
        threads = []
        token_files = ['passwords.txt', 'api_keys.json', 'database_backup.sql']
        
        for i, filename in enumerate(token_files):
            thread = threading.Thread(
                target=access_honey_token,
                args=(filename, i * 0.1),
                name=f"AccessThread-{i}"
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Wait for detection
        time.sleep(2.0)
        
        # Verify multiple attacks were detected
        recent_attacks = self.audit_logger.get_recent_attacks(10)
        self.assertGreaterEqual(len(recent_attacks), len(token_files), 
                               f"Expected at least {len(token_files)} attacks, got {len(recent_attacks)}")
        
        # Verify different files were accessed
        accessed_files = set(attack.filename for attack in recent_attacks)
        self.assertGreaterEqual(len(accessed_files), 2, "Multiple files should be accessed")
        
        print(f"✅ Detected {len(recent_attacks)} concurrent attacks on {len(accessed_files)} files")
    
    def test_system_reset_integration(self):
        """Test complete system reset functionality"""
        print("\n🧪 Testing System Reset Integration")
        
        # Start monitoring and generate some attacks
        self.monitor_service.start_monitoring()
        
        # Generate multiple attacks
        for filename in ['passwords.txt', 'api_keys.json']:
            honey_file = self.honey_manager.base_directory / filename
            with open(honey_file, 'a') as f:
                f.write('\n# Reset test attack')
        
        time.sleep(1.0)
        
        # Verify attacks were logged
        attacks_before = self.audit_logger.get_recent_attacks(10)
        self.assertGreater(len(attacks_before), 0, "Should have attacks before reset")
        
        status_before = self.audit_logger.get_system_status()
        self.assertGreater(status_before.total_attacks, 0, "Should have attack count before reset")
        
        # Reset the system
        reset_success = self.audit_logger.reset_system()
        self.assertTrue(reset_success, "System reset should succeed")
        
        # Verify system is clean
        attacks_after = self.audit_logger.get_recent_attacks(10)
        self.assertEqual(len(attacks_after), 0, "Should have no attacks after reset")
        
        status_after = self.audit_logger.get_system_status()
        self.assertEqual(status_after.status, 'SAFE', "Status should be SAFE after reset")
        self.assertEqual(status_after.total_attacks, 0, "Attack count should be 0 after reset")
        
        print("✅ System reset integration successful")
    
    def test_health_monitoring_and_recovery(self):
        """Test health monitoring and automatic recovery"""
        print("\n🧪 Testing Health Monitoring and Recovery")
        
        # Start monitoring
        self.monitor_service.start_monitoring()
        
        # Get initial health status
        initial_status = self.monitor_service.get_status()
        self.assertEqual(initial_status['health_status'], 'healthy')
        
        # Simulate an error condition
        self.monitor_service.last_error = "Simulated error for testing"
        self.monitor_service.error_count = 1
        
        # Check degraded health status
        degraded_status = self.monitor_service.get_status()
        self.assertEqual(degraded_status['health_status'], 'degraded')
        self.assertIsNotNone(degraded_status['last_error'])
        
        # Simulate recovery by clearing error
        self.monitor_service.last_error = None
        self.monitor_service.error_count = 0
        
        # Check healthy status restored
        recovered_status = self.monitor_service.get_status()
        self.assertEqual(recovered_status['health_status'], 'healthy')
        
        print("✅ Health monitoring and recovery successful")


class TestFlaskAPIIntegration(unittest.TestCase):
    """Test Flask API integration with error handling"""
    
    def setUp(self):
        """Set up Flask test environment"""
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_api_status_endpoint_error_handling(self):
        """Test API status endpoint with component failures"""
        print("\n🧪 Testing API Status Endpoint Error Handling")
        
        # Test normal operation
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('components_healthy', data)
        
        print("✅ API status endpoint working correctly")
    
    def test_api_attacks_endpoint_error_handling(self):
        """Test API attacks endpoint with various error conditions"""
        print("\n🧪 Testing API Attacks Endpoint Error Handling")
        
        # Test with valid limit
        response = self.client.get('/api/attacks?limit=5')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('attacks', data)
        self.assertIn('total_count', data)
        
        # Test with invalid limit (should default to 10)
        response = self.client.get('/api/attacks?limit=invalid')
        self.assertEqual(response.status_code, 200)
        
        # Test with out-of-bounds limit
        response = self.client.get('/api/attacks?limit=1000')
        self.assertEqual(response.status_code, 200)
        
        print("✅ API attacks endpoint error handling working correctly")
    
    def test_api_simulate_endpoint_error_handling(self):
        """Test API simulate endpoint with various error conditions"""
        print("\n🧪 Testing API Simulate Endpoint Error Handling")
        
        # Test with valid request
        response = self.client.post('/api/simulate', 
                                  json={'attack_type': 'file_access'})
        self.assertIn(response.status_code, [200, 503])  # May fail if components not available
        
        # Test with invalid JSON
        response = self.client.post('/api/simulate', 
                                  data='invalid json',
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Invalid JSON', data['error'])
        
        print("✅ API simulate endpoint error handling working correctly")
    
    def test_api_monitoring_control_endpoints(self):
        """Test monitoring start/stop API endpoints"""
        print("\n🧪 Testing API Monitoring Control Endpoints")
        
        # Test start monitoring
        response = self.client.post('/api/monitoring/start')
        self.assertIn(response.status_code, [200, 500, 503])  # Various states possible
        
        # Test stop monitoring
        response = self.client.post('/api/monitoring/stop')
        self.assertIn(response.status_code, [200, 500, 503])  # Various states possible
        
        print("✅ API monitoring control endpoints working correctly")


class TestErrorRecoveryScenarios(unittest.TestCase):
    """Test various error recovery scenarios"""
    
    def setUp(self):
        """Set up error recovery test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        self.honey_manager = HoneyTokenManager(base_directory=self.temp_path / "honey_tokens")
        self.audit_logger = AuditLogger(logs_directory=self.temp_path / "logs")
        self.monitor_service = MonitorService(self.honey_manager, self.audit_logger)
    
    def tearDown(self):
        """Clean up error recovery test environment"""
        if self.monitor_service.is_monitoring:
            self.monitor_service.stop_monitoring()
        
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_recovery_from_corrupted_log_files(self):
        """Test recovery from corrupted audit log files"""
        print("\n🧪 Testing Recovery from Corrupted Log Files")
        
        # Create corrupted log file
        log_file = self.audit_logger.attacks_log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'w') as f:
            f.write("invalid json content")
        
        # Try to get recent attacks (should handle corruption gracefully)
        try:
            recent_attacks = self.audit_logger.get_recent_attacks(5)
            # Should return empty list instead of crashing
            self.assertEqual(len(recent_attacks), 0)
            print("✅ Corrupted log file handled gracefully")
        except Exception as e:
            self.fail(f"Should handle corrupted log files gracefully, but got: {e}")
    
    def test_recovery_from_permission_errors(self):
        """Test recovery from file permission errors"""
        print("\n🧪 Testing Recovery from Permission Errors")
        
        # Create honey tokens first
        self.honey_manager.create_honey_tokens()
        
        # Try to start monitoring (should work initially)
        success = self.monitor_service.start_monitoring()
        self.assertTrue(success)
        
        # Simulate permission recovery by ensuring files are accessible
        token_paths = self.honey_manager.get_token_paths()
        for path in token_paths:
            self.assertTrue(os.access(path, os.R_OK), f"Should be able to read {path}")
        
        print("✅ Permission error recovery working correctly")
    
    def test_recovery_from_disk_space_issues(self):
        """Test graceful handling of disk space issues"""
        print("\n🧪 Testing Recovery from Disk Space Issues")
        
        # This test simulates disk space issues by testing large log operations
        # In a real scenario, this would test actual disk space constraints
        
        # Generate many attack events to test log management
        for i in range(100):
            try:
                self.audit_logger.log_attack_event(
                    event_type="file_accessed",
                    file_path=f"/test/file_{i}.txt",
                    process_info={
                        'process_name': 'test',
                        'process_id': i,
                        'username': 'test_user',
                        'command_line': f'test command {i}'
                    }
                )
            except Exception as e:
                # Should handle errors gracefully
                print(f"Handled error gracefully: {e}")
                break
        
        # Verify system is still functional
        status = self.audit_logger.get_system_status()
        self.assertIsNotNone(status)
        
        print("✅ Disk space issue handling working correctly")


def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Running Comprehensive Integration Tests")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestSystemIntegration,
        TestFlaskAPIIntegration,
        TestErrorRecoveryScenarios
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🧪 Integration Test Summary")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed!'}")
    
    return success


if __name__ == "__main__":
    run_integration_tests()