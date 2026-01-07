"""
Core System Reset and Management Tests
Focused tests for task 7 without monitoring service interference
"""
import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

from honey_token_manager import HoneyTokenManager
from audit_logger import AuditLogger
from monitor_service import MonitorService


class TestResetManagementCore(unittest.TestCase):
    """Test core reset and management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Initialize components
        self.honey_manager = HoneyTokenManager(base_directory=self.temp_path / "honey_tokens")
        self.audit_logger = AuditLogger(logs_directory=self.temp_path / "logs")
        
        # Create honey tokens for testing
        self.honey_manager.create_honey_tokens()
        
        # Sample process info for testing
        self.sample_process_info = {
            'process_name': 'test_process',
            'process_id': '12345',
            'username': 'test_user',
            'command_line': 'test command'
        }
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_reset_system_clears_logs(self):
        """Test that reset_system() clears all attack logs"""
        # Log multiple attacks
        for i in range(3):
            self.audit_logger.log_attack_event(
                event_type="file_accessed",
                file_path=f"/test/file{i}.txt",
                process_info=self.sample_process_info
            )
        
        # Verify attacks exist
        attacks_before = self.audit_logger.get_all_attacks()
        self.assertEqual(len(attacks_before), 3)
        
        # Reset system
        success = self.audit_logger.reset_system()
        self.assertTrue(success)
        
        # Verify all attacks are cleared
        attacks_after = self.audit_logger.get_all_attacks()
        self.assertEqual(len(attacks_after), 0)
    
    def test_reset_system_restores_safe_state(self):
        """Test that reset_system() restores system to SAFE state"""
        # Log an attack to change status
        self.audit_logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/passwords.txt",
            process_info=self.sample_process_info
        )
        
        # Verify system is under attack
        status_before = self.audit_logger.get_system_status()
        self.assertEqual(status_before.status, "UNDER_ATTACK")
        self.assertEqual(status_before.total_attacks, 1)
        self.assertIsNotNone(status_before.last_attack)
        
        # Reset system
        success = self.audit_logger.reset_system()
        self.assertTrue(success)
        
        # Verify system is restored to safe state
        status_after = self.audit_logger.get_system_status()
        self.assertEqual(status_after.status, "SAFE")
        self.assertEqual(status_after.total_attacks, 0)
        self.assertIsNone(status_after.last_attack)
    
    def test_reset_system_resets_attack_counter(self):
        """Test that reset_system() resets the attack counter"""
        # Log some attacks
        attack1 = self.audit_logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/file1.txt",
            process_info=self.sample_process_info
        )
        attack2 = self.audit_logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/file2.txt",
            process_info=self.sample_process_info
        )
        
        # Verify attack IDs are sequential
        self.assertEqual(attack1.attack_id, "ATK_001")
        self.assertEqual(attack2.attack_id, "ATK_002")
        
        # Reset system
        self.audit_logger.reset_system()
        
        # Create new logger instance to test counter reset
        new_logger = AuditLogger(logs_directory=self.temp_path / "logs")
        
        # Log new attack and verify counter is reset
        new_attack = new_logger.log_attack_event(
            event_type="file_accessed",
            file_path="/test/new_file.txt",
            process_info=self.sample_process_info
        )
        self.assertEqual(new_attack.attack_id, "ATK_001")
    
    def test_monitoring_status_management(self):
        """Test monitoring status can be set and retrieved"""
        # Initially monitoring should be inactive
        status = self.audit_logger.get_system_status()
        self.assertFalse(status.monitoring_active)
        
        # Set monitoring active
        self.audit_logger.set_monitoring_status(True)
        status = self.audit_logger.get_system_status()
        self.assertTrue(status.monitoring_active)
        
        # Set monitoring inactive
        self.audit_logger.set_monitoring_status(False)
        status = self.audit_logger.get_system_status()
        self.assertFalse(status.monitoring_active)
    
    def test_monitoring_status_persistence(self):
        """Test that monitoring status persists across logger instances"""
        # Set monitoring active
        self.audit_logger.set_monitoring_status(True)
        
        # Create new logger instance
        new_logger = AuditLogger(logs_directory=self.temp_path / "logs")
        status = new_logger.get_system_status()
        self.assertTrue(status.monitoring_active)
        
        # Set monitoring inactive with new logger
        new_logger.set_monitoring_status(False)
        
        # Verify with original logger
        status = self.audit_logger.get_system_status()
        self.assertFalse(status.monitoring_active)
    
    def test_system_statistics_calculation(self):
        """Test system statistics are calculated correctly"""
        # Log various types of attacks
        attacks_data = [
            ("file_accessed", "passwords.txt"),
            ("file_accessed", "api_keys.json"),
            ("file_modified", "passwords.txt"),
            ("file_deleted", "config.env"),
            ("file_accessed", "passwords.txt")  # passwords.txt accessed 3 times total
        ]
        
        for event_type, filename in attacks_data:
            self.audit_logger.log_attack_event(
                event_type=event_type,
                file_path=f"/test/{filename}",
                process_info=self.sample_process_info
            )
        
        # Get statistics
        stats = self.audit_logger.get_attack_statistics()
        
        # Verify statistics
        self.assertEqual(stats['total_attacks'], 5)
        self.assertEqual(stats['event_types']['file_accessed'], 3)
        self.assertEqual(stats['event_types']['file_modified'], 1)
        self.assertEqual(stats['event_types']['file_deleted'], 1)
        self.assertEqual(stats['targeted_files']['passwords.txt'], 3)
        self.assertEqual(stats['targeted_files']['api_keys.json'], 1)
        self.assertEqual(stats['targeted_files']['config.env'], 1)
        self.assertEqual(stats['most_targeted_file'], 'passwords.txt')
        self.assertEqual(stats['most_common_event'], 'file_accessed')
    
    def test_system_statistics_empty_state(self):
        """Test system statistics when no attacks have occurred"""
        stats = self.audit_logger.get_attack_statistics()
        
        self.assertEqual(stats['total_attacks'], 0)
        self.assertEqual(stats['event_types'], {})
        self.assertEqual(stats['targeted_files'], {})
        self.assertIsNone(stats['most_targeted_file'])
        self.assertIsNone(stats['most_common_event'])
    
    def test_uptime_calculation(self):
        """Test that system uptime is calculated correctly"""
        import time
        
        # Reset system to start fresh
        self.audit_logger.reset_system()
        
        # Wait a short time
        time.sleep(1)
        
        # Get status and verify uptime
        status = self.audit_logger.get_system_status()
        self.assertGreaterEqual(status.uptime_seconds, 1)
        self.assertLessEqual(status.uptime_seconds, 5)  # Should be close to 1 second
    
    def test_honey_token_recreation(self):
        """Test that honey tokens can be recreated after modification"""
        # Get original content
        passwords_file = self.honey_manager.base_directory / "passwords.txt"
        original_content = passwords_file.read_text()
        
        # Modify the file
        with open(passwords_file, 'a') as f:
            f.write("\n# Modified by attacker")
        
        modified_content = passwords_file.read_text()
        self.assertNotEqual(original_content, modified_content)
        
        # Recreate honey tokens
        self.honey_manager.create_honey_tokens()
        
        # Verify file is restored
        restored_content = passwords_file.read_text()
        self.assertEqual(original_content, restored_content)
    
    def test_monitor_service_status_tracking(self):
        """Test that monitor service status can be tracked"""
        monitor_service = MonitorService(self.honey_manager, self.audit_logger)
        
        # Initially not running
        self.assertFalse(monitor_service.is_running())
        
        # Get status
        status = monitor_service.get_status()
        self.assertFalse(status['is_running'])
        self.assertFalse(status['is_monitoring'])
        self.assertEqual(status['monitored_files'], 5)  # 5 honey token files
        self.assertEqual(status['event_count'], 0)
        self.assertEqual(status['restart_count'], 0)
    
    def test_complete_reset_workflow(self):
        """Test complete reset workflow"""
        # 1. Log some attacks
        for i in range(3):
            self.audit_logger.log_attack_event(
                event_type="file_accessed",
                file_path=f"/test/file{i}.txt",
                process_info=self.sample_process_info
            )
        
        # 2. Set monitoring active
        self.audit_logger.set_monitoring_status(True)
        
        # 3. Verify system state before reset
        status_before = self.audit_logger.get_system_status()
        self.assertEqual(status_before.status, "UNDER_ATTACK")
        self.assertEqual(status_before.total_attacks, 3)
        self.assertTrue(status_before.monitoring_active)
        self.assertEqual(len(self.audit_logger.get_all_attacks()), 3)
        
        # 4. Reset system
        success = self.audit_logger.reset_system()
        self.assertTrue(success)
        
        # 5. Verify system is completely reset
        status_after = self.audit_logger.get_system_status()
        self.assertEqual(status_after.status, "SAFE")
        self.assertEqual(status_after.total_attacks, 0)
        self.assertFalse(status_after.monitoring_active)  # Reset should set monitoring to False
        self.assertEqual(len(self.audit_logger.get_all_attacks()), 0)
        
        # 6. Verify honey tokens still exist
        verification_results = self.honey_manager.verify_tokens()
        self.assertTrue(all(verification_results.values()))


if __name__ == '__main__':
    unittest.main()