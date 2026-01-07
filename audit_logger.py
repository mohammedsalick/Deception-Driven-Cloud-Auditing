"""
Audit Logger - Records attack events and manages system status for honey-token monitoring
"""
import json
import os
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class AttackEvent:
    """Data model for attack events"""
    timestamp: str
    event_type: str
    file_path: str
    filename: str
    attack_id: str
    process_name: str
    process_id: str
    username: str
    command_line: str
    ip_address: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AttackEvent to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttackEvent':
        """Create AttackEvent from dictionary"""
        return cls(**data)


@dataclass
class SystemStatus:
    """Data model for system status"""
    status: str  # "SAFE" or "UNDER_ATTACK"
    last_attack: Optional[str]
    total_attacks: int
    monitoring_active: bool
    uptime_seconds: int
    start_time: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SystemStatus to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemStatus':
        """Create SystemStatus from dictionary"""
        return cls(**data)


class AuditLogger:
    """Manages audit logging and system status for honey-token monitoring"""
    
    def __init__(self, logs_directory: str = "logs"):
        """
        Initialize the AuditLogger
        
        Args:
            logs_directory: Directory where log files will be stored
        """
        self.logs_directory = Path(logs_directory)
        self.logs_directory.mkdir(parents=True, exist_ok=True)
        
        self.attacks_log_file = self.logs_directory / "attacks.json"
        self.status_file = self.logs_directory / "system_status.json"
        
        # Initialize system status
        self.system_start_time = datetime.utcnow()
        self._initialize_system_status()
        
        # Attack counter for generating unique IDs
        self.attack_counter = self._get_next_attack_counter()
    
    def _initialize_system_status(self) -> None:
        """Initialize system status file if it doesn't exist"""
        if not self.status_file.exists():
            initial_status = SystemStatus(
                status="SAFE",
                last_attack=None,
                total_attacks=0,
                monitoring_active=False,
                uptime_seconds=0,
                start_time=self.system_start_time.isoformat() + 'Z'
            )
            self._save_system_status(initial_status)
    
    def _get_next_attack_counter(self) -> int:
        """Get the next attack counter value based on existing logs"""
        try:
            if self.attacks_log_file.exists():
                with open(self.attacks_log_file, 'r', encoding='utf-8') as f:
                    attacks = json.load(f)
                    if attacks:
                        # Find the highest attack ID number
                        max_id = 0
                        for attack in attacks:
                            attack_id = attack.get('attack_id', 'ATK_000')
                            if attack_id.startswith('ATK_'):
                                try:
                                    id_num = int(attack_id.split('_')[1])
                                    max_id = max(max_id, id_num)
                                except (IndexError, ValueError):
                                    continue
                        return max_id + 1
            return 1
        except Exception:
            return 1
    
    def _save_system_status(self, status: SystemStatus) -> None:
        """Save system status to file"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving system status: {e}")
    
    def _load_system_status(self) -> SystemStatus:
        """Load system status from file"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return SystemStatus.from_dict(data)
            else:
                # Return default status
                return SystemStatus(
                    status="SAFE",
                    last_attack=None,
                    total_attacks=0,
                    monitoring_active=False,
                    uptime_seconds=0,
                    start_time=self.system_start_time.isoformat() + 'Z'
                )
        except Exception as e:
            print(f"Error loading system status: {e}")
            # Return default status on error
            return SystemStatus(
                status="SAFE",
                last_attack=None,
                total_attacks=0,
                monitoring_active=False,
                uptime_seconds=0,
                start_time=self.system_start_time.isoformat() + 'Z'
            )
    
    def log_attack_event(self, event_type: str, file_path: str, 
                        process_info: Optional[Dict[str, str]] = None,
                        ip_address: Optional[str] = None) -> AttackEvent:
        """
        Record a new attack event with detailed information
        
        Args:
            event_type: Type of file system event (e.g., 'file_accessed', 'file_modified')
            file_path: Path of the accessed file
            process_info: Optional process information dictionary
            ip_address: Optional IP address of the attacker
            
        Returns:
            AttackEvent: The created attack event
        """
        try:
            # Generate attack event
            timestamp = datetime.utcnow().isoformat() + 'Z'
            filename = Path(file_path).name
            attack_id = f'ATK_{self.attack_counter:03d}'
            
            # Get process information if not provided
            if process_info is None:
                process_info = self._get_current_process_info()
            
            # Get IP address if not provided
            if ip_address is None:
                ip_address = self._get_ip_address()
            
            # Create attack event
            attack_event = AttackEvent(
                timestamp=timestamp,
                event_type=event_type,
                file_path=file_path,
                filename=filename,
                attack_id=attack_id,
                process_name=process_info.get('process_name', 'Unknown'),
                process_id=str(process_info.get('process_id', 'Unknown')),
                username=process_info.get('username', 'Unknown'),
                command_line=process_info.get('command_line', 'Unknown'),
                ip_address=ip_address
            )
            
            # Save attack event to log file
            self._save_attack_event(attack_event)
            
            # Update system status to "UNDER_ATTACK"
            self.update_system_status("UNDER_ATTACK", attack_event.timestamp)
            
            # Increment attack counter
            self.attack_counter += 1
            
            print(f"🚨 ATTACK LOGGED: {attack_event.attack_id} - {attack_event.event_type} on {attack_event.filename}")
            
            return attack_event
            
        except Exception as e:
            print(f"Error logging attack event: {e}")
            raise
    
    def _save_attack_event(self, attack_event: AttackEvent) -> None:
        """Save attack event to the attacks log file"""
        try:
            # Load existing attacks
            attacks = []
            if self.attacks_log_file.exists():
                with open(self.attacks_log_file, 'r', encoding='utf-8') as f:
                    attacks = json.load(f)
            
            # Add new attack
            attacks.append(attack_event.to_dict())
            
            # Save updated attacks list
            with open(self.attacks_log_file, 'w', encoding='utf-8') as f:
                json.dump(attacks, f, indent=2)
                
        except Exception as e:
            print(f"Error saving attack event: {e}")
            raise
    
    def _get_current_process_info(self) -> Dict[str, str]:
        """
        Get information about the current process
        
        Returns:
            Dict containing process information
        """
        try:
            current_process = psutil.Process()
            return {
                'process_name': current_process.name(),
                'process_id': current_process.pid,
                'username': current_process.username(),
                'command_line': ' '.join(current_process.cmdline()) if current_process.cmdline() else 'N/A'
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, Exception):
            return {
                'process_name': 'Unknown',
                'process_id': 'Unknown',
                'username': 'Unknown',
                'command_line': 'Unknown'
            }
    
    def _get_ip_address(self) -> str:
        """
        Get the IP address of the current connection
        
        Returns:
            str: IP address or 'localhost' if not available
        """
        try:
            # For local monitoring, return localhost
            # In a real deployment, this could be enhanced to detect remote connections
            return '127.0.0.1'
        except Exception:
            return 'Unknown'
    
    def update_system_status(self, status: str, last_attack_time: Optional[str] = None) -> None:
        """
        Update the overall system security status
        
        Args:
            status: New system status ("SAFE" or "UNDER_ATTACK")
            last_attack_time: Timestamp of the last attack (optional)
        """
        try:
            # Load current status
            current_status = self._load_system_status()
            
            # Update status
            current_status.status = status
            if last_attack_time:
                current_status.last_attack = last_attack_time
                current_status.total_attacks += 1
            
            # Update uptime
            if current_status.start_time:
                try:
                    start_time = datetime.fromisoformat(current_status.start_time.replace('Z', '+00:00'))
                    current_status.uptime_seconds = int((datetime.utcnow() - start_time.replace(tzinfo=None)).total_seconds())
                except Exception:
                    current_status.uptime_seconds = 0
            
            # Save updated status
            self._save_system_status(current_status)
            
            print(f"📊 System status updated: {status}")
            
        except Exception as e:
            print(f"Error updating system status: {e}")
    
    def get_system_status(self) -> SystemStatus:
        """
        Get the current system status
        
        Returns:
            SystemStatus: Current system status
        """
        status = self._load_system_status()
        
        # Update uptime in real-time
        if status.start_time:
            try:
                start_time = datetime.fromisoformat(status.start_time.replace('Z', '+00:00'))
                status.uptime_seconds = int((datetime.utcnow() - start_time.replace(tzinfo=None)).total_seconds())
            except Exception:
                status.uptime_seconds = 0
        
        return status
    
    def get_recent_attacks(self, limit: int = 10) -> List[AttackEvent]:
        """
        Get list of recent attack events
        
        Args:
            limit: Maximum number of attacks to return
            
        Returns:
            List[AttackEvent]: List of recent attack events
        """
        try:
            if not self.attacks_log_file.exists():
                return []
            
            with open(self.attacks_log_file, 'r', encoding='utf-8') as f:
                attacks_data = json.load(f)
            
            # Convert to AttackEvent objects and sort by timestamp (most recent first)
            attacks = [AttackEvent.from_dict(data) for data in attacks_data]
            attacks.sort(key=lambda x: x.timestamp, reverse=True)
            
            return attacks[:limit]
            
        except Exception as e:
            print(f"Error getting recent attacks: {e}")
            return []
    
    def get_all_attacks(self) -> List[AttackEvent]:
        """
        Get all recorded attack events
        
        Returns:
            List[AttackEvent]: List of all attack events
        """
        try:
            if not self.attacks_log_file.exists():
                return []
            
            with open(self.attacks_log_file, 'r', encoding='utf-8') as f:
                attacks_data = json.load(f)
            
            # Convert to AttackEvent objects
            attacks = [AttackEvent.from_dict(data) for data in attacks_data]
            
            return attacks
            
        except Exception as e:
            print(f"Error getting all attacks: {e}")
            return []
    
    def reset_system(self) -> bool:
        """
        Reset the system to clean state - clear logs and return to "SAFE" status
        
        Returns:
            bool: True if reset was successful, False otherwise
        """
        try:
            # Clear attacks log
            if self.attacks_log_file.exists():
                self.attacks_log_file.unlink()
            
            # Reset system status
            reset_status = SystemStatus(
                status="SAFE",
                last_attack=None,
                total_attacks=0,
                monitoring_active=False,
                uptime_seconds=0,
                start_time=datetime.utcnow().isoformat() + 'Z'
            )
            self._save_system_status(reset_status)
            
            # Reset attack counter
            self.attack_counter = 1
            self.system_start_time = datetime.utcnow()
            
            print("🔄 System reset to clean state")
            return True
            
        except Exception as e:
            print(f"Error resetting system: {e}")
            return False
    
    def set_monitoring_status(self, active: bool) -> None:
        """
        Update the monitoring active status
        
        Args:
            active: Whether monitoring is currently active
        """
        try:
            current_status = self._load_system_status()
            current_status.monitoring_active = active
            self._save_system_status(current_status)
            
            status_text = "ACTIVE" if active else "INACTIVE"
            print(f"📡 Monitoring status: {status_text}")
            
        except Exception as e:
            print(f"Error setting monitoring status: {e}")
    
    def get_attack_statistics(self) -> Dict[str, Any]:
        """
        Get attack statistics and analytics
        
        Returns:
            Dict containing attack statistics
        """
        try:
            attacks = self.get_all_attacks()
            
            if not attacks:
                return {
                    'total_attacks': 0,
                    'event_types': {},
                    'targeted_files': {},
                    'recent_attacks_count': 0,
                    'most_targeted_file': None,
                    'most_common_event': None
                }
            
            # Count event types
            event_types = {}
            targeted_files = {}
            
            for attack in attacks:
                # Count event types
                event_types[attack.event_type] = event_types.get(attack.event_type, 0) + 1
                
                # Count targeted files
                targeted_files[attack.filename] = targeted_files.get(attack.filename, 0) + 1
            
            # Create timeline (last 24 hours)
            recent_attacks = [a for a in attacks if a.timestamp]  # Filter valid timestamps
            
            return {
                'total_attacks': len(attacks),
                'event_types': event_types,
                'targeted_files': targeted_files,
                'recent_attacks_count': len(recent_attacks),
                'most_targeted_file': max(targeted_files.items(), key=lambda x: x[1])[0] if targeted_files else None,
                'most_common_event': max(event_types.items(), key=lambda x: x[1])[0] if event_types else None
            }
            
        except Exception as e:
            print(f"Error getting attack statistics: {e}")
            return {
                'total_attacks': 0,
                'event_types': {},
                'targeted_files': {},
                'recent_attacks_count': 0,
                'most_targeted_file': None,
                'most_common_event': None
            }


if __name__ == "__main__":
    # Demo usage
    print("🔍 Audit Logger Demo")
    print("=" * 30)
    
    # Initialize audit logger
    logger = AuditLogger()
    
    # Demo attack event
    print("\n1. Logging demo attack event...")
    attack = logger.log_attack_event(
        event_type="file_accessed",
        file_path="/home/ubuntu/honey_tokens/passwords.txt"
    )
    
    print(f"   Attack ID: {attack.attack_id}")
    print(f"   Timestamp: {attack.timestamp}")
    print(f"   File: {attack.filename}")
    
    # Check system status
    print("\n2. Current system status:")
    status = logger.get_system_status()
    print(f"   Status: {status.status}")
    print(f"   Total attacks: {status.total_attacks}")
    print(f"   Monitoring active: {status.monitoring_active}")
    
    # Get recent attacks
    print("\n3. Recent attacks:")
    recent = logger.get_recent_attacks(5)
    for attack in recent:
        print(f"   {attack.attack_id}: {attack.event_type} on {attack.filename}")
    
    # Get statistics
    print("\n4. Attack statistics:")
    stats = logger.get_attack_statistics()
    print(f"   Total attacks: {stats['total_attacks']}")
    print(f"   Event types: {stats['event_types']}")
    print(f"   Targeted files: {stats['targeted_files']}")
    
    print("\nDemo completed!")