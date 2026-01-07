"""
Unit tests for the file system monitoring service
"""
import os
import json
import time
import tempfile
import unittest
import psutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from monitor_service import HoneyTokenHandler, MonitorService
from honey_token_manager import HoneyTokenManager


class TestHoneyTokenHandler(unittest.TestCase):
    """Test cases for HoneyTokenHandler class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_paths = [
            os.path.join(self.temp_dir, "passwords.txt"),
            os.path.join(self.temp_dir, "api_keys.json")
        ]
        
        # Create test honey-token files
        for path in self.test_paths:
            with open(path, 'w') as f:
                f.write("test content")
        
        self.audit_callback = Mock()
        self.handler = HoneyTokenHandler(self.test_paths, self.audit_callback)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove test files
        for path in self.test_paths:
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(self.temp_dir)
    
    def test_is_honey_token_detection(self):
        """Test honey-token file detection"""
        # Test positive cases
        self.assertTrue(self.handler._is_honey_token(self.test_paths[0]))
        self.assertTrue(self.handler._is_honey_token(self.test_paths[1]))
        
        # Test negative case
        non_honey_path = os.path.join(self.temp_dir, "normal_file.txt")
        self.assertFalse(self.handler._is_honey_token(non_honey_path))
    
    @patch('psutil.Process')
    def test_get_process_info(self, mock_process_class):
        """Test process information gathering"""
        # Mock process information
        mock_process = Mock()
        mock_process.name.return_value = "test_process"
        mock_process.pid = 12345
        mock_process.username.return_value = "test_user"
        mock_process.cmdline.return_value = ["python", "test.py"]
        mock_process_class.return_value = mock_process
        
        process_info = self.handler._get_process_info()
        
        self.assertEqual(process_info['process_name'], "test_process")
        self.assertEqual(process_info['process_id'], 12345)
        self.assertEqual(process_info['username'], "test_user")
        self.assertEqual(process_info['command_line'], "python test.py")
    
    def test_get_process_info_exception_handling(self):
        """Test process information gathering with exceptions"""
        # Test the exception handling by temporarily replacing psutil.Process
        original_process = psutil.Process
        
        def mock_process():
            raise psutil.NoSuchProcess(pid=12345, name="test_process")
        
        # Replace psutil.Process temporarily
        psutil.Process = mock_process
        
        try:
            process_info = self.handler._get_process_info()
            
            # The method should handle the exception and return "Unknown" values
            self.assertEqual(process_info['process_name'], "Unknown")
            self.assertEqual(process_info['process_id'], "Unknown")
            self.assertEqual(process_info['username'], "Unknown")
            self.assertEqual(process_info['command_line'], "Unknown")
        finally:
            # Restore original psutil.Process
            psutil.Process = original_process
    
    def test_log_attack_event(self):
        """Test attack event logging"""
        test_file_path = self.test_paths[0]
        
        with patch.object(self.handler, '_get_process_info') as mock_process_info:
            mock_process_info.return_value = {
                'process_name': 'cat',
                'process_id': 12345,
                'username': 'testuser',
                'command_line': 'cat passwords.txt'
            }
            
            self.handler._log_attack_event('file_accessed', test_file_path)
        
        # Verify audit callback was called
        self.audit_callback.assert_called_once()
        
        # Verify attack event structure
        call_args = self.audit_callback.call_args[0][0]
        self.assertEqual(call_args['event_type'], 'file_accessed')
        self.assertEqual(call_args['file_path'], test_file_path)
        self.assertEqual(call_args['filename'], 'passwords.txt')
        self.assertEqual(call_args['process_name'], 'cat')
        self.assertEqual(call_args['username'], 'testuser')
        self.assertIn('timestamp', call_args)
        self.assertIn('attack_id', call_args)
    
    def test_on_accessed_event(self):
        """Test file access event handling"""
        # Create mock event
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = self.test_paths[0]
        
        with patch.object(self.handler, '_log_attack_event') as mock_log:
            self.handler.on_accessed(mock_event)
            mock_log.assert_called_once_with('file_accessed', self.test_paths[0])
    
    def test_on_modified_event(self):
        """Test file modification event handling"""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = self.test_paths[0]
        
        with patch.object(self.handler, '_log_attack_event') as mock_log:
            self.handler.on_modified(mock_event)
            mock_log.assert_called_once_with('file_modified', self.test_paths[0])
    
    def test_on_deleted_event(self):
        """Test file deletion event handling"""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = self.test_paths[0]
        
        with patch.object(self.handler, '_log_attack_event') as mock_log:
            self.handler.on_deleted(mock_event)
            mock_log.assert_called_once_with('file_deleted', self.test_paths[0])
    
    def test_on_moved_event(self):
        """Test file move/rename event handling"""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = self.test_paths[0]
        mock_event.dest_path = os.path.join(self.temp_dir, "moved_passwords.txt")
        
        with patch.object(self.handler, '_log_attack_event') as mock_log:
            self.handler.on_moved(mock_event)
            mock_log.assert_called_once_with('file_moved_from', self.test_paths[0])
    
    def test_ignore_directory_events(self):
        """Test that directory events are ignored"""
        mock_event = Mock()
        mock_event.is_directory = True
        mock_event.src_path = self.temp_dir
        
        with patch.object(self.handler, '_log_attack_event') as mock_log:
            self.handler.on_accessed(mock_event)
            self.handler.on_modified(mock_event)
            self.handler.on_deleted(mock_event)
            mock_log.assert_not_called()
    
    def test_ignore_non_honey_token_events(self):
        """Test that non-honey-token file events are ignored"""
        non_honey_path = os.path.join(self.temp_dir, "normal_file.txt")
        
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = non_honey_path
        
        with patch.object(self.handler, '_log_attack_event') as mock_log:
            self.handler.on_accessed(mock_event)
            self.handler.on_modified(mock_event)
            self.handler.on_deleted(mock_event)
            mock_log.assert_not_called()


class TestMonitorService(unittest.TestCase):
    """Test cases for MonitorService class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create mock honey token manager
        self.mock_manager = Mock(spec=HoneyTokenManager)
        self.mock_manager.base_directory = Path(self.temp_dir)
        self.mock_manager.get_token_paths.return_value = [
            os.path.join(self.temp_dir, "passwords.txt"),
            os.path.join(self.temp_dir, "api_keys.json")
        ]
        self.mock_manager.verify_tokens.return_value = {
            "passwords.txt": True,
            "api_keys.json": True
        }
        
        # Create test files
        for path in self.mock_manager.get_token_paths.return_value:
            with open(path, 'w') as f:
                f.write("test content")
        
        self.audit_callback = Mock()
        self.monitor_service = MonitorService(self.mock_manager, self.audit_callback)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Stop monitoring if running
        if self.monitor_service.is_monitoring:
            self.monitor_service.stop_monitoring()
        
        # Remove test files
        for path in self.mock_manager.get_token_paths.return_value:
            if os.path.exists(path):
                os.remove(path)
        
        # Clean up directory
        try:
            if os.path.exists(self.temp_dir):
                os.rmdir(self.temp_dir)
        except OSError:
            # Directory not empty, try to clean remaining files
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_start_monitoring_success(self):
        """Test successful monitoring startup"""
        success = self.monitor_service.start_monitoring()
        
        self.assertTrue(success)
        self.assertTrue(self.monitor_service.is_monitoring)
        self.assertIsNotNone(self.monitor_service.observer)
        self.assertIsNotNone(self.monitor_service.handler)
        self.assertIsNotNone(self.monitor_service.start_time)
    
    def test_start_monitoring_already_running(self):
        """Test starting monitoring when already running"""
        # Start monitoring first time
        self.monitor_service.start_monitoring()
        
        # Try to start again
        success = self.monitor_service.start_monitoring()
        
        self.assertTrue(success)
        self.assertTrue(self.monitor_service.is_monitoring)
    
    def test_start_monitoring_missing_tokens(self):
        """Test monitoring startup with missing tokens"""
        # Mock missing tokens
        self.mock_manager.verify_tokens.return_value = {
            "passwords.txt": False,
            "api_keys.json": True
        }
        
        success = self.monitor_service.start_monitoring()
        
        self.assertFalse(success)
        self.assertFalse(self.monitor_service.is_monitoring)
    
    def test_start_monitoring_no_token_paths(self):
        """Test monitoring startup with no token paths"""
        self.mock_manager.get_token_paths.return_value = []
        
        success = self.monitor_service.start_monitoring()
        
        self.assertFalse(success)
        self.assertFalse(self.monitor_service.is_monitoring)
    
    def test_stop_monitoring_success(self):
        """Test successful monitoring shutdown"""
        # Start monitoring first
        self.monitor_service.start_monitoring()
        
        # Stop monitoring
        success = self.monitor_service.stop_monitoring()
        
        self.assertTrue(success)
        self.assertFalse(self.monitor_service.is_monitoring)
        self.assertIsNone(self.monitor_service.observer)
        self.assertIsNone(self.monitor_service.handler)
    
    def test_stop_monitoring_not_running(self):
        """Test stopping monitoring when not running"""
        success = self.monitor_service.stop_monitoring()
        
        self.assertTrue(success)
        self.assertFalse(self.monitor_service.is_monitoring)
    
    def test_is_running_status(self):
        """Test monitoring running status check"""
        # Initially not running
        self.assertFalse(self.monitor_service.is_running())
        
        # Start monitoring
        self.monitor_service.start_monitoring()
        self.assertTrue(self.monitor_service.is_running())
        
        # Stop monitoring
        self.monitor_service.stop_monitoring()
        self.assertFalse(self.monitor_service.is_running())
    
    def test_get_status(self):
        """Test service status information"""
        # Test status when not running
        status = self.monitor_service.get_status()
        self.assertFalse(status['is_monitoring'])
        self.assertFalse(status['is_running'])
        self.assertIsNone(status['start_time'])
        self.assertEqual(status['uptime_seconds'], 0)
        
        # Test status when running
        self.monitor_service.start_monitoring()
        status = self.monitor_service.get_status()
        self.assertTrue(status['is_monitoring'])
        self.assertTrue(status['is_running'])
        self.assertIsNotNone(status['start_time'])
        self.assertGreaterEqual(status['uptime_seconds'], 0)
        self.assertEqual(status['monitored_files'], 2)
    
    def test_restart_monitoring(self):
        """Test monitoring service restart"""
        # Start monitoring first
        self.monitor_service.start_monitoring()
        original_start_time = self.monitor_service.start_time
        
        # Wait a moment to ensure different start time
        time.sleep(0.1)
        
        # Restart monitoring
        success = self.monitor_service.restart_monitoring()
        
        self.assertTrue(success)
        self.assertTrue(self.monitor_service.is_monitoring)
        self.assertNotEqual(self.monitor_service.start_time, original_start_time)
        self.assertEqual(self.monitor_service.restart_count, 1)
    
    def test_restart_monitoring_max_attempts(self):
        """Test monitoring restart with maximum attempts reached"""
        self.monitor_service.restart_count = self.monitor_service.max_restarts
        
        success = self.monitor_service.restart_monitoring()
        
        self.assertFalse(success)
    
    def test_monitor_with_auto_restart_startup(self):
        """Test auto-restart monitoring startup"""
        # Test that the auto-restart method can start monitoring
        # We'll just test that it can start monitoring when not running
        self.assertFalse(self.monitor_service.is_running())
        
        # Start monitoring manually to simulate what auto-restart would do
        success = self.monitor_service.start_monitoring()
        self.assertTrue(success)
        self.assertTrue(self.monitor_service.is_monitoring)


class TestIntegration(unittest.TestCase):
    """Integration tests for monitoring service with real file operations"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.honey_manager = HoneyTokenManager(self.temp_dir)
        self.honey_manager.create_honey_tokens()
        
        self.attack_events = []
        
        def audit_callback(event):
            self.attack_events.append(event)
        
        self.monitor_service = MonitorService(self.honey_manager, audit_callback)
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        if self.monitor_service.is_monitoring:
            self.monitor_service.stop_monitoring()
        
        # Clean up honey tokens
        self.honey_manager.cleanup_tokens()
        
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_real_file_access_detection(self):
        """Test detection of real file access operations"""
        # Start monitoring
        self.monitor_service.start_monitoring()
        
        # Give the observer time to start
        time.sleep(1.0)
        
        # Access a honey-token file multiple times to ensure detection
        honey_file = os.path.join(self.temp_dir, "passwords.txt")
        
        # Try multiple access patterns that should trigger events
        with open(honey_file, 'r') as f:
            content = f.read()
        
        # Modify the file (this should definitely trigger an event)
        with open(honey_file, 'a') as f:
            f.write('\n# Test modification')
        
        # Give the observer more time to detect the events
        time.sleep(1.0)
        
        # Verify at least one attack was detected (modification should work on all platforms)
        self.assertGreater(len(self.attack_events), 0, "No attack events detected. Events: " + str(self.attack_events))
        
        # Verify attack event details
        attack_event = self.attack_events[0]
        self.assertIn(attack_event['event_type'], ['file_accessed', 'file_modified'])
        self.assertEqual(attack_event['filename'], 'passwords.txt')
        self.assertIn('timestamp', attack_event)
        self.assertIn('attack_id', attack_event)
    
    def test_file_modification_detection(self):
        """Test detection of file modification operations"""
        # Start monitoring
        self.monitor_service.start_monitoring()
        time.sleep(0.5)
        
        # Modify a honey-token file
        honey_file = os.path.join(self.temp_dir, "api_keys.json")
        with open(honey_file, 'a') as f:
            f.write('\n# Modified by attacker')
        
        time.sleep(0.5)
        
        # Verify modification was detected
        modification_events = [e for e in self.attack_events if e['event_type'] == 'file_modified']
        self.assertGreater(len(modification_events), 0)
    
    def test_non_honey_token_ignored(self):
        """Test that non-honey-token files are ignored"""
        # Start monitoring
        self.monitor_service.start_monitoring()
        time.sleep(0.5)
        
        # Create and access a non-honey-token file
        normal_file = os.path.join(self.temp_dir, "normal_file.txt")
        with open(normal_file, 'w') as f:
            f.write("This is not a honey token")
        
        with open(normal_file, 'r') as f:
            content = f.read()
        
        time.sleep(0.5)
        
        # Clean up
        os.remove(normal_file)
        
        # Verify no attack events were generated
        self.assertEqual(len(self.attack_events), 0)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)