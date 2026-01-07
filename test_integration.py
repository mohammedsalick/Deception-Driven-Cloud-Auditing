"""
Integration test for audit logger with monitor service
"""
import tempfile
import time
from pathlib import Path

from honey_token_manager import HoneyTokenManager
from monitor_service import MonitorService
from audit_logger import AuditLogger


def test_integration():
    """Test integration between monitor service and audit logger"""
    print("🧪 Testing Monitor Service + Audit Logger Integration")
    print("=" * 55)
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize components
        honey_manager = HoneyTokenManager(base_directory=temp_path / "honey_tokens")
        audit_logger = AuditLogger(logs_directory=temp_path / "logs")
        monitor = MonitorService(honey_manager, audit_logger)
        
        # Create honey tokens
        print("1. Creating honey tokens...")
        success = honey_manager.create_honey_tokens()
        print(f"   Honey tokens created: {success}")
        
        # Start monitoring
        print("\n2. Starting monitoring service...")
        monitor_started = monitor.start_monitoring()
        print(f"   Monitoring started: {monitor_started}")
        
        if monitor_started:
            # Simulate file access by reading and modifying a honey token
            print("\n3. Simulating attack by accessing honey token...")
            honey_file = honey_manager.base_directory / "passwords.txt"
            
            # Read the file to trigger monitoring
            print("   - Reading honey token file...")
            with open(honey_file, 'r') as f:
                content = f.read()
            
            # Modify the file to ensure detection (more reliable on Windows)
            print("   - Modifying honey token file...")
            with open(honey_file, 'a') as f:
                f.write("\n# Modified by test")
            
            # Give the monitor a moment to detect the access
            time.sleep(1.0)
            
            # Check audit logs
            print("\n4. Checking audit logs...")
            recent_attacks = audit_logger.get_recent_attacks(5)
            print(f"   Recent attacks detected: {len(recent_attacks)}")
            
            for attack in recent_attacks:
                print(f"   - {attack.attack_id}: {attack.event_type} on {attack.filename}")
            
            # Check system status
            print("\n5. Checking system status...")
            status = audit_logger.get_system_status()
            print(f"   System status: {status.status}")
            print(f"   Total attacks: {status.total_attacks}")
            print(f"   Monitoring active: {status.monitoring_active}")
            
            # Stop monitoring
            print("\n6. Stopping monitoring service...")
            monitor.stop_monitoring()
            print("   Monitoring stopped")
            
        print("\n✅ Integration test completed!")


if __name__ == "__main__":
    test_integration()