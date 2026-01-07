"""
File System Monitoring Service - Monitors honey-token files for unauthorized access
"""
import os
import sys
import time
import json
import psutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from honey_token_manager import HoneyTokenManager
from audit_logger import AuditLogger


class HoneyTokenHandler(FileSystemEventHandler):
    """File system event handler for honey-token monitoring"""
    
    def __init__(self, honey_token_paths: List[str], audit_logger: Optional[AuditLogger] = None):
        """
        Initialize the honey-token event handler
        
        Args:
            honey_token_paths: List of honey-token file paths to monitor
            audit_logger: Optional AuditLogger instance for logging events
        """
        super().__init__()
        self.honey_token_paths = set(str(Path(p).resolve()) for p in honey_token_paths)
        self.audit_logger = audit_logger
        self.event_count = 0
        
    def _is_honey_token(self, file_path: str) -> bool:
        """
        Check if the file path corresponds to a honey-token
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if file is a honey-token, False otherwise
        """
        resolved_path = str(Path(file_path).resolve())
        return resolved_path in self.honey_token_paths
    
    def _get_process_info(self) -> Dict[str, str]:
        """
        Get information about the current process accessing the file
        
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
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return {
                'process_name': 'Unknown',
                'process_id': 'Unknown',
                'username': 'Unknown',
                'command_line': 'Unknown'
            }
    
    def _log_attack_event(self, event_type: str, file_path: str) -> None:
        """
        Log an attack event with detailed information
        
        Args:
            event_type: Type of file system event
            file_path: Path of the accessed file
        """
        self.event_count += 1
        
        if self.audit_logger:
            # Use the new AuditLogger for comprehensive logging
            process_info = self._get_process_info()
            ip_address = self._get_ip_address()
            
            attack_event = self.audit_logger.log_attack_event(
                event_type=event_type,
                file_path=file_path,
                process_info=process_info,
                ip_address=ip_address
            )
            
            print(f"🚨 HONEY-TOKEN ACCESSED! {attack_event.event_type} on {attack_event.filename}")
            print(f"   Attack ID: {attack_event.attack_id}")
            print(f"   Process: {attack_event.process_name} (PID: {attack_event.process_id})")
            print(f"   User: {attack_event.username}")
            print(f"   Time: {attack_event.timestamp}")
        else:
            # Fallback to simple console logging
            filename = Path(file_path).name
            timestamp = datetime.utcnow().isoformat() + 'Z'
            print(f"🚨 HONEY-TOKEN ACCESSED! {event_type} on {filename}")
            print(f"   Time: {timestamp}")
            print(f"   Path: {file_path}")
    
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
    
    def on_accessed(self, event: FileSystemEvent) -> None:
        """
        Handle file access events
        
        Args:
            event: File system event object
        """
        if not event.is_directory and self._is_honey_token(event.src_path):
            self._log_attack_event('file_accessed', event.src_path)
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events
        
        Args:
            event: File system event object
        """
        if not event.is_directory and self._is_honey_token(event.src_path):
            self._log_attack_event('file_modified', event.src_path)
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        """
        Handle file deletion events
        
        Args:
            event: File system event object
        """
        if not event.is_directory and self._is_honey_token(event.src_path):
            self._log_attack_event('file_deleted', event.src_path)
    
    def on_moved(self, event: FileSystemEvent) -> None:
        """
        Handle file move/rename events
        
        Args:
            event: File system event object
        """
        if not event.is_directory:
            # Check if source or destination is a honey-token
            if hasattr(event, 'dest_path'):
                if self._is_honey_token(event.src_path):
                    self._log_attack_event('file_moved_from', event.src_path)
                if self._is_honey_token(event.dest_path):
                    self._log_attack_event('file_moved_to', event.dest_path)
            elif self._is_honey_token(event.src_path):
                self._log_attack_event('file_moved', event.src_path)


class MonitorService:
    """Service for managing file system monitoring of honey-tokens"""
    
    def __init__(self, honey_token_manager: HoneyTokenManager, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize the monitoring service
        
        Args:
            honey_token_manager: HoneyTokenManager instance
            audit_logger: Optional AuditLogger instance for logging events
        """
        self.honey_token_manager = honey_token_manager
        self.audit_logger = audit_logger
        self.observer = None
        self.handler = None
        self.is_monitoring = False
        self.start_time = None
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_delay = 1  # seconds
        self.last_error = None
        self.error_count = 0
        self.health_check_interval = 30  # seconds
        self.auto_restart_thread = None
        self.shutdown_requested = False
        
    def start_monitoring(self) -> bool:
        """
        Start monitoring honey-token files with comprehensive error handling
        
        Returns:
            bool: True if monitoring started successfully, False otherwise
        """
        try:
            if self.is_monitoring:
                print("Monitoring is already active")
                return True
            
            # Reset error state on successful start attempt
            self.last_error = None
            
            # Verify honey-tokens exist and recreate if missing
            try:
                verification_results = self.honey_token_manager.verify_tokens()
                missing_tokens = [name for name, exists in verification_results.items() if not exists]
                
                if missing_tokens:
                    print(f"Warning: Some honey-tokens are missing: {missing_tokens}")
                    print("Attempting to recreate missing tokens...")
                    self.honey_token_manager.create_honey_tokens()
                    
                    # Re-verify after recreation
                    verification_results = self.honey_token_manager.verify_tokens()
                    still_missing = [name for name, exists in verification_results.items() if not exists]
                    
                    if still_missing:
                        error_msg = f"Failed to recreate honey-tokens: {still_missing}"
                        self.last_error = error_msg
                        print(f"Error: {error_msg}")
                        return False
                        
            except Exception as e:
                error_msg = f"Failed to verify honey-tokens: {str(e)}"
                self.last_error = error_msg
                print(f"Error: {error_msg}")
                return False
            
            # Get honey-token paths
            try:
                token_paths = self.honey_token_manager.get_token_paths()
                if not token_paths:
                    error_msg = "No honey-token paths found"
                    self.last_error = error_msg
                    print(f"Error: {error_msg}")
                    return False
            except Exception as e:
                error_msg = f"Failed to get honey-token paths: {str(e)}"
                self.last_error = error_msg
                print(f"Error: {error_msg}")
                return False
            
            # Verify watch directory exists and is accessible
            try:
                watch_directory = str(self.honey_token_manager.base_directory.resolve())
                if not Path(watch_directory).exists():
                    error_msg = f"Watch directory does not exist: {watch_directory}"
                    self.last_error = error_msg
                    print(f"Error: {error_msg}")
                    return False
                    
                if not os.access(watch_directory, os.R_OK):
                    error_msg = f"Watch directory is not readable: {watch_directory}"
                    self.last_error = error_msg
                    print(f"Error: {error_msg}")
                    return False
                    
            except Exception as e:
                error_msg = f"Failed to verify watch directory: {str(e)}"
                self.last_error = error_msg
                print(f"Error: {error_msg}")
                return False
            
            # Create event handler with error handling
            try:
                self.handler = HoneyTokenHandler(token_paths, self.audit_logger)
            except Exception as e:
                error_msg = f"Failed to create event handler: {str(e)}"
                self.last_error = error_msg
                print(f"Error: {error_msg}")
                return False
            
            # Create and configure observer with error handling
            try:
                self.observer = Observer()
                self.observer.schedule(self.handler, watch_directory, recursive=False)
            except Exception as e:
                error_msg = f"Failed to configure file observer: {str(e)}"
                self.last_error = error_msg
                print(f"Error: {error_msg}")
                return False
            
            # Start the observer with timeout and error handling
            try:
                self.observer.start()
                
                # Wait a moment to ensure observer started successfully
                time.sleep(0.5)
                
                if not self.observer.is_alive():
                    error_msg = "File observer failed to start properly"
                    self.last_error = error_msg
                    print(f"Error: {error_msg}")
                    return False
                    
            except Exception as e:
                error_msg = f"Failed to start file observer: {str(e)}"
                self.last_error = error_msg
                print(f"Error: {error_msg}")
                return False
            
            # Mark as successfully started
            self.is_monitoring = True
            self.start_time = datetime.utcnow()
            self.error_count = 0  # Reset error count on successful start
            
            # Update audit logger if available
            if self.audit_logger:
                try:
                    self.audit_logger.set_monitoring_status(True)
                except Exception as e:
                    print(f"Warning: Failed to update audit logger status: {e}")
            
            print(f"🔍 Started monitoring {len(token_paths)} honey-tokens in {watch_directory}")
            print("Monitoring for unauthorized access...")
            
            return True
            
        except Exception as e:
            error_msg = f"Unexpected error starting monitoring service: {str(e)}"
            self.last_error = error_msg
            self.error_count += 1
            print(f"Error: {error_msg}")
            self.is_monitoring = False
            
            # Clean up on failure
            try:
                if self.observer:
                    self.observer.stop()
                    self.observer = None
                self.handler = None
            except Exception as cleanup_error:
                print(f"Warning: Error during cleanup: {cleanup_error}")
                
            return False
    
    def stop_monitoring(self) -> bool:
        """
        Stop monitoring honey-token files with comprehensive error handling
        
        Returns:
            bool: True if monitoring stopped successfully, False otherwise
        """
        try:
            if not self.is_monitoring:
                print("Monitoring is not currently active")
                return True
            
            # Signal shutdown to prevent auto-restart
            self.shutdown_requested = True
            
            # Stop auto-restart thread if running
            if self.auto_restart_thread and self.auto_restart_thread.is_alive():
                try:
                    # The thread will check shutdown_requested and exit
                    self.auto_restart_thread.join(timeout=2)
                except Exception as e:
                    print(f"Warning: Error stopping auto-restart thread: {e}")
            
            # Stop the file observer
            if self.observer:
                try:
                    self.observer.stop()
                    
                    # Wait for observer to stop gracefully
                    if self.observer.is_alive():
                        self.observer.join(timeout=10)  # Increased timeout for better reliability
                        
                    # Force stop if still alive
                    if self.observer.is_alive():
                        print("Warning: Observer did not stop gracefully, forcing shutdown")
                        try:
                            # Try to terminate the observer thread more forcefully
                            self.observer.unschedule_all()
                        except Exception as force_error:
                            print(f"Warning: Error during forced observer shutdown: {force_error}")
                            
                except Exception as e:
                    print(f"Warning: Error stopping file observer: {e}")
                    # Continue with cleanup even if observer stop failed
            
            # Update audit logger status
            if self.audit_logger:
                try:
                    self.audit_logger.set_monitoring_status(False)
                except Exception as e:
                    print(f"Warning: Failed to update audit logger status: {e}")
            
            # Clean up state
            self.is_monitoring = False
            self.observer = None
            self.handler = None
            self.shutdown_requested = False
            
            print("🛑 Stopped honey-token monitoring")
            return True
            
        except Exception as e:
            error_msg = f"Error stopping monitoring service: {str(e)}"
            self.last_error = error_msg
            print(f"Error: {error_msg}")
            
            # Force cleanup even on error
            try:
                self.is_monitoring = False
                self.observer = None
                self.handler = None
                self.shutdown_requested = False
            except Exception as cleanup_error:
                print(f"Warning: Error during forced cleanup: {cleanup_error}")
                
            return False
    
    def is_running(self) -> bool:
        """
        Check if monitoring service is currently running
        
        Returns:
            bool: True if monitoring is active, False otherwise
        """
        return self.is_monitoring and self.observer is not None and self.observer.is_alive()
    
    def get_status(self) -> Dict[str, any]:
        """
        Get current status of the monitoring service with comprehensive health information
        
        Returns:
            Dict containing service status information
        """
        uptime_seconds = 0
        if self.start_time and self.is_monitoring:
            uptime_seconds = int((datetime.utcnow() - self.start_time).total_seconds())
        
        # Get honey-token paths safely
        try:
            monitored_files_count = len(self.honey_token_manager.get_token_paths())
        except Exception as e:
            monitored_files_count = 0
            if not self.last_error:
                self.last_error = f"Error getting token paths: {str(e)}"
        
        return {
            'is_monitoring': self.is_monitoring,
            'is_running': self.is_running(),
            'start_time': self.start_time.isoformat() + 'Z' if self.start_time else None,
            'uptime_seconds': uptime_seconds,
            'restart_count': self.restart_count,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'monitored_files': monitored_files_count,
            'event_count': self.handler.event_count if self.handler else 0,
            'health_status': self._get_health_status(),
            'auto_restart_active': self.auto_restart_thread is not None and self.auto_restart_thread.is_alive()
        }
    
    def _get_health_status(self) -> str:
        """
        Get the health status of the monitoring service
        
        Returns:
            str: Health status ('healthy', 'degraded', 'unhealthy')
        """
        if not self.is_monitoring:
            return 'stopped'
        
        if self.last_error:
            return 'degraded'
        
        if self.error_count > 3:
            return 'unhealthy'
        
        if not self.is_running():
            return 'unhealthy'
        
        return 'healthy'
    
    def restart_monitoring(self) -> bool:
        """
        Restart the monitoring service
        
        Returns:
            bool: True if restart was successful, False otherwise
        """
        try:
            if self.restart_count >= self.max_restarts:
                print(f"Maximum restart attempts ({self.max_restarts}) reached. Manual intervention required.")
                return False
            
            print(f"Restarting monitoring service (attempt {self.restart_count + 1}/{self.max_restarts})")
            
            # Stop current monitoring
            self.stop_monitoring()
            
            # Wait before restarting
            time.sleep(self.restart_delay)
            
            # Start monitoring again
            success = self.start_monitoring()
            
            if success:
                self.restart_count += 1
                # Increase delay for next restart (exponential backoff)
                self.restart_delay = min(self.restart_delay * 2, 60)
                print(f"Monitoring service restarted successfully")
            else:
                print(f"Failed to restart monitoring service")
            
            return success
            
        except Exception as e:
            print(f"Error restarting monitoring service: {e}")
            return False
    
    def start_auto_restart_monitoring(self) -> bool:
        """
        Start monitoring with automatic restart in a separate thread
        
        Returns:
            bool: True if auto-restart thread started successfully, False otherwise
        """
        try:
            if self.auto_restart_thread and self.auto_restart_thread.is_alive():
                print("Auto-restart monitoring is already running")
                return True
            
            self.shutdown_requested = False
            self.auto_restart_thread = threading.Thread(
                target=self._auto_restart_worker,
                name="HoneyTokenAutoRestart",
                daemon=True
            )
            self.auto_restart_thread.start()
            
            print("🔄 Started auto-restart monitoring thread")
            return True
            
        except Exception as e:
            error_msg = f"Failed to start auto-restart monitoring: {str(e)}"
            self.last_error = error_msg
            print(f"Error: {error_msg}")
            return False
    
    def _auto_restart_worker(self) -> None:
        """
        Worker thread for automatic restart monitoring
        This method runs in a separate thread and monitors service health
        """
        print("🔄 Auto-restart worker thread started")
        
        while not self.shutdown_requested:
            try:
                # Check if monitoring should be running but isn't
                if not self.is_running() and not self.shutdown_requested:
                    print("🚨 Monitoring service detected as down, attempting restart...")
                    
                    if self.restart_count >= self.max_restarts:
                        print(f"❌ Maximum restart attempts ({self.max_restarts}) reached. Auto-restart disabled.")
                        break
                    
                    # Attempt to restart
                    if self.restart_monitoring():
                        print("✅ Monitoring service restarted successfully")
                    else:
                        print("❌ Failed to restart monitoring service")
                        # Wait longer before next attempt
                        time.sleep(min(self.restart_delay * 2, 60))
                        continue
                
                # Perform health checks
                if self.is_running():
                    self._perform_health_check()
                
                # Wait before next check
                time.sleep(self.health_check_interval)
                
                # Reset restart count if service has been running successfully
                if self.is_running() and self.restart_count > 0:
                    uptime = (datetime.utcnow() - self.start_time).total_seconds()
                    if uptime > 300:  # 5 minutes of successful operation
                        print("✅ Service stable for 5 minutes, resetting restart count")
                        self.restart_count = 0
                        self.restart_delay = 1
                        
            except Exception as e:
                print(f"Error in auto-restart worker: {e}")
                self.error_count += 1
                self.last_error = f"Auto-restart worker error: {str(e)}"
                
                # If too many errors, stop auto-restart
                if self.error_count > 10:
                    print("❌ Too many errors in auto-restart worker, stopping...")
                    break
                
                time.sleep(30)  # Wait before retrying
        
        print("🔄 Auto-restart worker thread stopped")
    
    def _perform_health_check(self) -> None:
        """
        Perform comprehensive health checks on the monitoring service
        """
        try:
            # Check if observer is still alive
            if not self.observer or not self.observer.is_alive():
                print("⚠️ Health check failed: Observer is not alive")
                self.last_error = "Observer thread died"
                return
            
            # Check if honey-tokens still exist
            try:
                verification_results = self.honey_token_manager.verify_tokens()
                missing_tokens = [name for name, exists in verification_results.items() if not exists]
                
                if missing_tokens:
                    print(f"⚠️ Health check warning: Missing honey-tokens detected: {missing_tokens}")
                    print("Attempting to recreate missing tokens...")
                    self.honey_token_manager.create_honey_tokens()
                    
            except Exception as e:
                print(f"⚠️ Health check failed: Error verifying tokens: {e}")
                self.last_error = f"Token verification error: {str(e)}"
            
            # Check watch directory accessibility
            try:
                watch_directory = self.honey_token_manager.base_directory
                if not watch_directory.exists():
                    print(f"⚠️ Health check failed: Watch directory missing: {watch_directory}")
                    self.last_error = f"Watch directory missing: {watch_directory}"
                elif not os.access(watch_directory, os.R_OK):
                    print(f"⚠️ Health check failed: Watch directory not readable: {watch_directory}")
                    self.last_error = f"Watch directory not readable: {watch_directory}"
                    
            except Exception as e:
                print(f"⚠️ Health check failed: Error checking watch directory: {e}")
                self.last_error = f"Watch directory check error: {str(e)}"
            
            # Check audit logger connectivity
            if self.audit_logger:
                try:
                    # Test audit logger by getting status
                    status = self.audit_logger.get_system_status()
                    if not status:
                        print("⚠️ Health check warning: Audit logger returned empty status")
                        
                except Exception as e:
                    print(f"⚠️ Health check failed: Audit logger error: {e}")
                    self.last_error = f"Audit logger error: {str(e)}"
            
        except Exception as e:
            print(f"⚠️ Health check failed with unexpected error: {e}")
            self.last_error = f"Health check error: {str(e)}"
    
    def monitor_with_auto_restart(self) -> None:
        """
        Run monitoring with automatic restart capability
        This method blocks and should be run in a separate thread
        """
        print("🔄 Starting monitoring with auto-restart capability...")
        
        # Start the auto-restart monitoring thread
        if not self.start_auto_restart_monitoring():
            print("❌ Failed to start auto-restart monitoring")
            return
        
        # Start initial monitoring
        if not self.start_monitoring():
            print("❌ Failed to start initial monitoring")
            return
        
        try:
            # Keep the main thread alive and handle shutdown gracefully
            while not self.shutdown_requested:
                time.sleep(1)
                
                # Check for keyboard interrupt
                if self.shutdown_requested:
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user")
        finally:
            self.shutdown_requested = True
            self.stop_monitoring()
            
            # Wait for auto-restart thread to finish
            if self.auto_restart_thread and self.auto_restart_thread.is_alive():
                self.auto_restart_thread.join(timeout=5)
            
            print("🔄 Monitoring with auto-restart stopped")


def main():
    """Main function for running the monitoring service standalone"""
    print("🍯 Honey-Token Monitoring Service")
    print("=" * 40)
    
    # Initialize honey-token manager
    manager = HoneyTokenManager()
    
    # Initialize audit logger
    audit_logger = AuditLogger()
    
    # Initialize monitoring service with audit logger
    monitor = MonitorService(manager, audit_logger)
    
    # Update monitoring status in audit logger
    if audit_logger:
        audit_logger.set_monitoring_status(True)
    
    try:
        # Start monitoring with auto-restart
        print("Starting monitoring service with auto-restart...")
        monitor.monitor_with_auto_restart()
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    finally:
        monitor.stop_monitoring()
        if audit_logger:
            audit_logger.set_monitoring_status(False)
        print("Monitoring service stopped")


if __name__ == "__main__":
    main()