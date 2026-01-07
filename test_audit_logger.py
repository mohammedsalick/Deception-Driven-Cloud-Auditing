"""
Unit tests for the Audit Logger system
"""
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from audit_logger import AuditLogger, AttackEvent, SystemStatus


class TestAttackEvent(unittest.TestCase):
    """Test cases for AttackEvent data model"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_attack_data = {
            'timestamp': '2024-01-07T10:30:45Z',
            'event_type': 'file_accessed',
            'file_path': '/home/ubuntu/passwords.txt',
            'filename': 'passwords.txt',
            'attack_id': 'ATK_001',
            'process_name': 'cat',
            'process_id': '1234',
            'username': 'ubuntu',
            'command_line': 'cat passwords.txt',
            'ip_address': '127.0.0.1'
        }
    
    def test_attack_event_creation(self):
        """Test AttackEvent creation from parameters"""
        attack = AttackEvent(**self.sample_attack_data)
        
        self.assertEqual(attack.timestamp, '2024-01-07T10:30:45Z')
        self.assertEqual(attack.event_type, 'file_accessed')
        self.assertEqual(attack.file_path, '/home/ubuntu/passwords.txt')
        self.assertEqual(attack.filename, 'passwords.txt')
        self.assertEqual(attack.attack_id, 'ATK_001')
        self.assertEqual(attack.process_name, 'cat')
        self.assertEqual(attack.process_id, '1234')
        self.assertEqual(attack.username, 'ubuntu')
        self.assertEqual(attack.command_line, 'cat passwords.txt')
        self.assertEqual(attack.ip_address, '127.0.0.1')
    
    def test_attack_event_to_dict(self):
        """Test AttackEvent conversion to dictionary"""
        attack = AttackEvent(**self.sample_attack_data)
        attack_dict = attack.to_dict()
        
        self.assertEqual(attack_dict, self.sample_attack_data)
        self.assertIsInstance(attack_dict, dict)
    
    def test_attack_event_from_dict(self):
        """Test AttackEvent creation from dictionary"""
        attack = AttackEvent.from_dict(self.sample_attack_data)
        
        self.assertEqual(attack.timestamp, '2024-01-07T10:30:45Z')
        self.assertEqual(attack.event_type, 'file_accessed')
        self.assertEqual(attack.filename, 'passwords.txt')
        self.assertEqual(attack.attack_id, 'ATK_001')


class TestSystemStatus(unittest.TestCase):
    """Test cases for SystemStatus data model"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_status_data = {
            'status': 'SAFE',
            'last_attack': None,
            'total_attacks': 0,
            'monitoring_active': True,
            'uptime_seconds': 3600,
            'start_time': '2024-01-07T09:00:00Z'
        }
    
    def test_system_status_creation(self):
        """Test SystemStatus creation from parameters"""
        status = SystemStatus(**self.sample_status_data)
        
        self.assertEqual(status.status, 'SAFE')
        self.assertIsNone(status.last_attack)
        self.assertEqual(status.total_attacks, 0)
        self.assertTrue(status.monitoring_active)
        self.assertEqual(status.uptime_seconds, 3600)
        self.assertEqual(status.start_time, '2024-01-07T09:00:00Z')
    
    def test_system_status_to_dict(self):
        """Test SystemStatus conversion to dictionary"""
        status = SystemStatus(**self.sample_status_data)
        status_dict = status.to_dict()
        
        self.assertEqual(status_dict, self.sample_status_data)
        self.assertIsInstance(status_dict, dict)
    
    def test_system_status_from_dict(self):
        """Test SystemStatus creation from dictionary"""
        status = SystemStatus.from_dict(self.sample_status_data)
        
        self.assertEqual(status.status, 'SAFE')
        self.assertEqual(status.total_attacks, 0)
        self.assertTrue(status.monitoring_active)


class TestAuditLogger(unittest.TestCase):
    """Test cases for AuditLogger class"""
    
    def setUp(self):
        """Set up test environment with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = AuditLogger(logs_directory=self.temp_dir)
        
        # Sample process info for testing
        self.sample_process_info = {
            'process_name': 'test_process',
            'process_id': 9999,
            'username': 'test_user',
            'command_line': 'test command'
        }
    
    def tearDown(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_audit_logger_initialization(self):
        """Test AuditLogger initialization"""
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertTrue(self.logger.logs_directory.exists())
        self.assertTrue(self.logger.status_file.exists())
        self.assertEqual(self.logger.attack_counter, 1)
    
    def test_log_attack_event(self):
        """Test logging an attack event"""
        # Log an attack event
        attack = self.logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/passwords.txt",
            process_info=self.sample_process_info,
            ip_address="192.168.1.100"
        )
        
        # Verify attack event properties
        self.assertEqual(attack.event_type, "file_accessed")
        self.assertEqual(attack.file_path, "/test/passwords.txt")
        self.assertEqual(attack.filename, "passwords.txt")
        self.assertEqual(attack.attack_id, "ATK_001")
        self.assertEqual(attack.process_name, "test_process")
        self.assertEqual(attack.process_id, "9999")
        self.assertEqual(attack.username, "test_user")
        self.assertEqual(attack.ip_address, "192.168.1.100")
        
        # Verify attack was saved to file
        self.assertTrue(self.logger.attacks_log_file.exists())
        
        with open(self.logger.attacks_log_file, 'r') as f:
            attacks_data = json.load(f)
        
        self.assertEqual(len(attacks_data), 1)
        self.assertEqual(attacks_data[0]['attack_id'], 'ATK_001')
        self.assertEqual(attacks_data[0]['event_type'], 'file_accessed')
    
    def test_multiple_attack_events(self):
        """Test logging multiple attack events"""
        # Log multiple attacks
        attack1 = self.logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/passwords.txt",
            process_info=self.sample_process_info
        )
        
        attack2 = self.logger.log_attack_event(
            event_type="file_modified",
            file_path="/test/api_keys.json",
            process_info=self.sample_process_info
        )
        
        # Verify unique attack IDs
        self.assertEqual(attack1.attack_id, "ATK_001")
        self.assertEqual(attack2.attack_id, "ATK_002")
        
        # Verify both attacks are saved
        attacks = self.logger.get_all_attacks()
        self.assertEqual(len(attacks), 2)
    
    def test_update_system_status(self):
        """Test updating system status"""
        # Update status to UNDER_ATTACK
        attack_time = "2024-01-07T10:30:45Z"
        self.logger.update_system_status("UNDER_ATTACK", attack_time)
        
        # Verify status update
        status = self.logger.get_system_status()
        self.assertEqual(status.status, "UNDER_ATTACK")
        self.assertEqual(status.last_attack, attack_time)
        self.assertEqual(status.total_attacks, 1)
    
    def test_get_recent_attacks(self):
        """Test getting recent attacks"""
        # Log several attacks
        for i in range(5):
            self.logger.log_attack_event(
                event_type="file_accessed",
                file_path=f"/test/file_{i}.txt",
                process_info=self.sample_process_info
            )
        
        # Get recent attacks
        recent_attacks = self.logger.get_recent_attacks(3)
        
        self.assertEqual(len(recent_attacks), 3)
        # Should be in reverse chronological order (most recent first)
        self.assertEqual(recent_attacks[0].attack_id, "ATK_005")
        self.assertEqual(recent_attacks[1].attack_id, "ATK_004")
        self.assertEqual(recent_attacks[2].attack_id, "ATK_003")
    
    def test_get_all_attacks(self):
        """Test getting all attacks"""
        # Log attacks
        for i in range(3):
            self.logger.log_attack_event(
                event_type="file_accessed",
                file_path=f"/test/file_{i}.txt",
                process_info=self.sample_process_info
            )
        
        # Get all attacks
        all_attacks = self.logger.get_all_attacks()
        
        self.assertEqual(len(all_attacks), 3)
        self.assertEqual(all_attacks[0].attack_id, "ATK_001")
        self.assertEqual(all_attacks[1].attack_id, "ATK_002")
        self.assertEqual(all_attacks[2].attack_id, "ATK_003")
    
    def test_reset_system(self):
        """Test system reset functionality"""
        # Log some attacks first
        self.logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/passwords.txt",
            process_info=self.sample_process_info
        )
        
        # Verify attacks exist
        self.assertEqual(len(self.logger.get_all_attacks()), 1)
        status = self.logger.get_system_status()
        self.assertEqual(status.total_attacks, 1)
        
        # Reset system
        success = self.logger.reset_system()
        self.assertTrue(success)
        
        # Verify system is reset
        self.assertEqual(len(self.logger.get_all_attacks()), 0)
        status = self.logger.get_system_status()
        self.assertEqual(status.status, "SAFE")
        self.assertEqual(status.total_attacks, 0)
        self.assertIsNone(status.last_attack)
    
    def test_set_monitoring_status(self):
        """Test setting monitoring status"""
        # Set monitoring active
        self.logger.set_monitoring_status(True)
        status = self.logger.get_system_status()
        self.assertTrue(status.monitoring_active)
        
        # Set monitoring inactive
        self.logger.set_monitoring_status(False)
        status = self.logger.get_system_status()
        self.assertFalse(status.monitoring_active)
    
    def test_get_attack_statistics(self):
        """Test getting attack statistics"""
        # Log various types of attacks
        attacks_data = [
            ("file_accessed", "passwords.txt"),
            ("file_accessed", "api_keys.json"),
            ("file_modified", "passwords.txt"),
            ("file_deleted", "config.env"),
            ("file_accessed", "passwords.txt")  # passwords.txt accessed 3 times total
        ]
        
        for event_type, filename in attacks_data:
            self.logger.log_attack_event(
                event_type=event_type,
                file_path=f"/test/{filename}",
                process_info=self.sample_process_info
            )
        
        # Get statistics
        stats = self.logger.get_attack_statistics()
        
        self.assertEqual(stats['total_attacks'], 5)
        self.assertEqual(stats['event_types']['file_accessed'], 3)
        self.assertEqual(stats['event_types']['file_modified'], 1)
        self.assertEqual(stats['event_types']['file_deleted'], 1)
        self.assertEqual(stats['targeted_files']['passwords.txt'], 3)
        self.assertEqual(stats['targeted_files']['api_keys.json'], 1)
        self.assertEqual(stats['most_targeted_file'], 'passwords.txt')
        self.assertEqual(stats['most_common_event'], 'file_accessed')
    
    def test_attack_counter_persistence(self):
        """Test that attack counter continues from existing logs"""
        # Create a logger and log some attacks
        logger1 = AuditLogger(logs_directory=self.temp_dir)
        attack1 = logger1.log_attack_event(
            event_type="file_accessed",
            file_path="/test/file1.txt",
            process_info=self.sample_process_info
        )
        attack2 = logger1.log_attack_event(
            event_type="file_accessed",
            file_path="/test/file2.txt",
            process_info=self.sample_process_info
        )
        
        self.assertEqual(attack1.attack_id, "ATK_001")
        self.assertEqual(attack2.attack_id, "ATK_002")
        
        # Create a new logger instance (simulating restart)
        logger2 = AuditLogger(logs_directory=self.temp_dir)
        attack3 = logger2.log_attack_event(
            event_type="file_accessed",
            file_path="/test/file3.txt",
            process_info=self.sample_process_info
        )
        
        # Should continue from where the previous logger left off
        self.assertEqual(attack3.attack_id, "ATK_003")
    
    @patch('audit_logger.psutil.Process')
    def test_get_current_process_info(self, mock_process_class):
        """Test getting current process information"""
        # Mock process information
        mock_process = MagicMock()
        mock_process.name.return_value = 'python'
        mock_process.pid = 1234
        mock_process.username.return_value = 'testuser'
        mock_process.cmdline.return_value = ['python', 'test.py']
        mock_process_class.return_value = mock_process
        
        # Test process info retrieval
        process_info = self.logger._get_current_process_info()
        
        self.assertEqual(process_info['process_name'], 'python')
        self.assertEqual(process_info['process_id'], 1234)
        self.assertEqual(process_info['username'], 'testuser')
        self.assertEqual(process_info['command_line'], 'python test.py')
    
    @patch('audit_logger.psutil.Process')
    def test_get_current_process_info_error_handling(self, mock_process_class):
        """Test process info error handling"""
        # Mock process access error
        mock_process_class.side_effect = Exception("Access denied")
        
        # Should return unknown values on error
        process_info = self.logger._get_current_process_info()
        
        self.assertEqual(process_info['process_name'], 'Unknown')
        self.assertEqual(process_info['process_id'], 'Unknown')
        self.assertEqual(process_info['username'], 'Unknown')
        self.assertEqual(process_info['command_line'], 'Unknown')
    
    def test_empty_logs_handling(self):
        """Test handling of empty log files"""
        # Test with no existing logs
        recent_attacks = self.logger.get_recent_attacks()
        all_attacks = self.logger.get_all_attacks()
        stats = self.logger.get_attack_statistics()
        
        self.assertEqual(len(recent_attacks), 0)
        self.assertEqual(len(all_attacks), 0)
        self.assertEqual(stats['total_attacks'], 0)
        self.assertEqual(stats['event_types'], {})
        self.assertEqual(stats['targeted_files'], {})
    
    def test_file_permissions_and_creation(self):
        """Test that log files are created with proper permissions"""
        # Log an attack to create files
        self.logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/passwords.txt",
            process_info=self.sample_process_info
        )
        
        # Verify files exist
        self.assertTrue(self.logger.attacks_log_file.exists())
        self.assertTrue(self.logger.status_file.exists())
        
        # Verify files are readable
        with open(self.logger.attacks_log_file, 'r') as f:
            data = json.load(f)
            self.assertIsInstance(data, list)
        
        with open(self.logger.status_file, 'r') as f:
            data = json.load(f)
            self.assertIsInstance(data, dict)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)