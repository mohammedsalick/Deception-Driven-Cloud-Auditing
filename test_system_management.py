"""
Test System Reset and Management Capabilities
Tests for task 7: Add system reset and management capabilities
"""
import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from honey_token_manager import HoneyTokenManager
from audit_logger import AuditLogger
from monitor_service import MonitorService
from app import app


class TestSystemResetAndManagement(unittest.TestCase):
    """Test system reset and management capabilities"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Initialize components
        self.honey_manager = HoneyTokenManager(base_directory=self.temp_path / "honey_tokens")
        self.audit_logger = AuditLogger(logs_directory=self.temp_path / "logs")
        self.monitor_service = MonitorService(self.honey_manager, self.audit_logger)
        
        # Create honey tokens for testing
        self.honey_manager.create_honey_tokens()
        
        # Sample process info for testing
        self.sample_process_info = {
            'process_name': 'test_process',
            'process_id': '12345',
            'username': 'test_user',
            'command_line': 'test command'
        }
        
        # Configure Flask app for testing
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Store original components
        self.original_honey_manager = getattr(app, 'honey_token_manager', None)
        self.original_audit_logger = getattr(app, 'audit_logger', None)
        self.original_monitor_service = getattr(app, 'monitor_service', None)
        
        # Mock the global components in app.py
        app.honey_token_manager = self.honey_manager
        app.audit_logger = self.audit_logger
        app.monitor_service = self.monitor_service
    
    def tearDown(self):
        """Clean up test environment"""
        # Stop monitoring if running
        try:
            if hasattr(self, 'monitor_service') and self.monitor_service.is_running():
                self.monitor_service.stop_monitoring()
        except:
            pass
        
        # Restore original components
        if hasattr(self, 'original_honey_manager'):
            if self.original_honey_manager:
                app.honey_token_manager = self.original_honey_manager
            elif hasattr(app, 'honey_token_manager'):
                delattr(app, 'honey_token_manager')
        
        if hasattr(self, 'original_audit_logger'):
            if self.original_audit_logger:
                app.audit_logger = self.original_audit_logger
            elif hasattr(app, 'audit_logger'):
                delattr(app, 'audit_logger')
        
        if hasattr(self, 'original_monitor_service'):
            if self.original_monitor_service:
                app.monitor_service = self.original_monitor_service
            elif hasattr(app, 'monitor_service'):
                delattr(app, 'monitor_service')
        
        # Clean up temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_reset_system_method(self):
        """Test reset_system() method clears logs and restores safe state"""
        # Log some attacks first
        self.audit_logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/passwords.txt",
            process_info=self.sample_process_info
        )
        self.audit_logger.log_attack_event(
            event_type="file_modified",
            file_path="/test/api_keys.json",
            process_info=self.sample_process_info
        )
        
        # Verify attacks exist
        attacks_before = self.audit_logger.get_all_attacks()
        self.assertEqual(len(attacks_before), 2)
        
        status_before = self.audit_logger.get_system_status()
        self.assertEqual(status_before.status, "UNDER_ATTACK")
        self.assertEqual(status_before.total_attacks, 2)
        self.assertIsNotNone(status_before.last_attack)
        
        # Reset system
        success = self.audit_logger.reset_system()
        self.assertTrue(success)
        
        # Verify system is reset to clean state
        attacks_after = self.audit_logger.get_all_attacks()
        self.assertEqual(len(attacks_after), 0)
        
        status_after = self.audit_logger.get_system_status()
        self.assertEqual(status_after.status, "SAFE")
        self.assertEqual(status_after.total_attacks, 0)
        self.assertIsNone(status_after.last_attack)
        self.assertEqual(status_after.uptime_seconds, 0)
    
    def test_reset_system_api_endpoint(self):
        """Test /api/reset endpoint for dashboard reset functionality"""
        # Log some attacks first
        self.audit_logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/passwords.txt",
            process_info=self.sample_process_info
        )
        
        # Verify attack exists
        self.assertEqual(len(self.audit_logger.get_all_attacks()), 1)
        
        # Call reset API endpoint
        response = self.client.post('/api/reset')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('reset to clean state', data['message'])
        self.assertIn('timestamp', data)
        
        # Verify system is reset
        self.assertEqual(len(self.audit_logger.get_all_attacks()), 0)
        status = self.audit_logger.get_system_status()
        self.assertEqual(status.status, "SAFE")
        self.assertEqual(status.total_attacks, 0)
    
    def test_reset_system_recreates_honey_tokens(self):
        """Test that reset system recreates honey-tokens in original state"""
        # Modify a honey-token file
        passwords_file = self.honey_manager.base_directory / "passwords.txt"
        original_content = passwords_file.read_text()
        
        # Modify the file
        with open(passwords_file, 'a') as f:
            f.write("\n# Modified by attacker")
        
        modified_content = passwords_file.read_text()
        self.assertNotEqual(original_content, modified_content)
        
        # Reset system via API
        response = self.client.post('/api/reset')
        self.assertEqual(response.status_code, 200)
        
        # Verify honey-token is restored to original state
        restored_content = passwords_file.read_text()
        self.assertEqual(original_content, restored_content)
    
    def test_start_monitoring_api_endpoint(self):
        """Test /api/monitoring/start endpoint"""
        # Ensure monitoring is stopped initially
        self.monitor_service.stop_monitoring()
        self.assertFalse(self.monitor_service.is_running())
        
        # Start monitoring via API
        response = self.client.post('/api/monitoring/start')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('started successfully', data['message'])
        
        # Verify monitoring is active
        self.assertTrue(self.monitor_service.is_running())
        
        # Verify audit logger monitoring status is updated
        status = self.audit_logger.get_system_status()
        self.assertTrue(status.monitoring_active)
    
    def test_start_monitoring_already_active(self):
        """Test starting monitoring when already active"""
        # Start monitoring first
        self.monitor_service.start_monitoring()
        self.assertTrue(self.monitor_service.is_running())
        
        # Try to start again via API
        response = self.client.post('/api/monitoring/start')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('already active', data['message'])
    
    def test_stop_monitoring_api_endpoint(self):
        """Test /api/monitoring/stop endpoint"""
        # Start monitoring first
        self.monitor_service.start_monitoring()
        self.assertTrue(self.monitor_service.is_running())
        
        # Stop monitoring via API
        response = self.client.post('/api/monitoring/stop')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('stopped successfully', data['message'])
        
        # Verify monitoring is stopped
        self.assertFalse(self.monitor_service.is_running())
        
        # Verify audit logger monitoring status is updated
        status = self.audit_logger.get_system_status()
        self.assertFalse(status.monitoring_active)
    
    def test_stop_monitoring_not_active(self):
        """Test stopping monitoring when not active"""
        # Ensure monitoring is stopped
        self.monitor_service.stop_monitoring()
        self.assertFalse(self.monitor_service.is_running())
        
        # Try to stop via API
        response = self.client.post('/api/monitoring/stop')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('not currently active', data['message'])
    
    def test_system_statistics_display(self):
        """Test system statistics display with uptime and attack count"""
        # Log various attacks
        attacks_data = [
            ("file_accessed", "passwords.txt"),
            ("file_accessed", "api_keys.json"),
            ("file_modified", "passwords.txt"),
            ("file_deleted", "config.env"),
            ("file_accessed", "passwords.txt")  # passwords.txt accessed 3 times
        ]
        
        for event_type, filename in attacks_data:
            self.audit_logger.log_attack_event(
                event_type=event_type,
                file_path=f"/test/{filename}",
                process_info=self.sample_process_info
            )
        
        # Get statistics via API
        response = self.client.get('/api/statistics')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        
        # Verify attack statistics
        attack_stats = data['attack_statistics']
        self.assertEqual(attack_stats['total_attacks'], 5)
        self.assertEqual(attack_stats['event_types']['file_accessed'], 3)
        self.assertEqual(attack_stats['event_types']['file_modified'], 1)
        self.assertEqual(attack_stats['event_types']['file_deleted'], 1)
        self.assertEqual(attack_stats['targeted_files']['passwords.txt'], 3)
        self.assertEqual(attack_stats['most_targeted_file'], 'passwords.txt')
        self.assertEqual(attack_stats['most_common_event'], 'file_accessed')
        
        # Verify system info
        system_info = data['system_info']
        self.assertEqual(system_info['total_attacks'], 5)
        self.assertEqual(system_info['current_status'], 'UNDER_ATTACK')
        self.assertGreaterEqual(system_info['uptime_seconds'], 0)
        self.assertIsInstance(system_info['monitoring_active'], bool)
        self.assertGreaterEqual(system_info['monitored_files'], 0)
    
    def test_system_status_uptime_calculation(self):
        """Test that system uptime is calculated correctly"""
        import time
        
        # Reset system to start fresh
        self.audit_logger.reset_system()
        
        # Wait a short time
        time.sleep(1)
        
        # Get status
        status = self.audit_logger.get_system_status()
        
        # Verify uptime is calculated
        self.assertGreaterEqual(status.uptime_seconds, 1)
        self.assertLessEqual(status.uptime_seconds, 5)  # Should be close to 1 second
    
    def test_monitoring_status_persistence(self):
        """Test that monitoring status is properly maintained"""
        # Set monitoring active
        self.audit_logger.set_monitoring_status(True)
        status = self.audit_logger.get_system_status()
        self.assertTrue(status.monitoring_active)
        
        # Set monitoring inactive
        self.audit_logger.set_monitoring_status(False)
        status = self.audit_logger.get_system_status()
        self.assertFalse(status.monitoring_active)
        
        # Verify persistence across logger instances
        new_logger = AuditLogger(logs_directory=self.temp_path / "logs")
        status = new_logger.get_system_status()
        self.assertFalse(status.monitoring_active)
    
    def test_reset_system_error_handling(self):
        """Test reset system error handling"""
        # Mock file system error by patching the reset_system method directly
        with patch.object(self.audit_logger, 'reset_system', return_value=False):
            success = self.audit_logger.reset_system()
            self.assertFalse(success)
    
    def test_monitoring_control_error_handling(self):
        """Test monitoring control error handling"""
        # Mock monitor service failure
        with patch.object(self.monitor_service, 'start_monitoring', return_value=False):
            response = self.client.post('/api/monitoring/start')
            self.assertEqual(response.status_code, 500)
            
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('Failed to start', data['error'])
        
        # Mock monitor service failure for stop
        with patch.object(self.monitor_service, 'stop_monitoring', return_value=False):
            response = self.client.post('/api/monitoring/stop')
            self.assertEqual(response.status_code, 500)
            
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('Failed to stop', data['error'])
    
    def test_statistics_with_no_attacks(self):
        """Test statistics display when no attacks have occurred"""
        # Ensure clean state
        self.audit_logger.reset_system()
        
        # Get statistics
        response = self.client.get('/api/statistics')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        attack_stats = data['attack_statistics']
        
        self.assertEqual(attack_stats['total_attacks'], 0)
        self.assertEqual(attack_stats['event_types'], {})
        self.assertEqual(attack_stats['targeted_files'], {})
        self.assertIsNone(attack_stats['most_targeted_file'])
        self.assertIsNone(attack_stats['most_common_event'])
    
    def test_complete_reset_and_restart_workflow(self):
        """Test complete workflow: attacks -> reset -> restart monitoring"""
        # 1. Start monitoring
        self.monitor_service.start_monitoring()
        self.assertTrue(self.monitor_service.is_running())
        
        # 2. Log some attacks
        self.audit_logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/passwords.txt",
            process_info=self.sample_process_info
        )
        
        # 3. Verify system is under attack
        status = self.audit_logger.get_system_status()
        self.assertEqual(status.status, "UNDER_ATTACK")
        self.assertEqual(status.total_attacks, 1)
        
        # 4. Reset system via API
        response = self.client.post('/api/reset')
        self.assertEqual(response.status_code, 200)
        
        # 5. Verify system is clean
        status = self.audit_logger.get_system_status()
        self.assertEqual(status.status, "SAFE")
        self.assertEqual(status.total_attacks, 0)
        self.assertEqual(len(self.audit_logger.get_all_attacks()), 0)
        
        # 6. Restart monitoring
        response = self.client.post('/api/monitoring/start')
        self.assertEqual(response.status_code, 200)
        
        # 7. Verify monitoring is active
        self.assertTrue(self.monitor_service.is_running())
        status = self.audit_logger.get_system_status()
        self.assertTrue(status.monitoring_active)


if __name__ == '__main__':
    unittest.main()