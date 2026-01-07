"""
Flask Web Dashboard for Honey-Token Auditing System
Provides real-time monitoring interface and attack simulation capabilities
"""
import os
import json
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from pathlib import Path

from honey_token_manager import HoneyTokenManager
from audit_logger import AuditLogger
from monitor_service import MonitorService


# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'honey-token-dashboard-secret-key-2024'

# Initialize components with error handling
try:
    honey_token_manager = HoneyTokenManager()
    audit_logger = AuditLogger()
    monitor_service = MonitorService(honey_token_manager, audit_logger)
    
    # Component initialization status
    components_healthy = True
    initialization_errors = []
    
except Exception as e:
    print(f"Critical error during component initialization: {e}")
    components_healthy = False
    initialization_errors = [str(e)]
    
    # Create fallback components to prevent crashes
    honey_token_manager = None
    audit_logger = None
    monitor_service = None

# Global monitoring thread
monitoring_thread = None


@app.route('/')
def dashboard():
    """Main dashboard route - displays system status and attack history"""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_system_status():
    """
    API endpoint to get current system status with graceful degradation
    
    Returns:
        JSON response with system status information
    """
    try:
        # Check if components are available
        if not components_healthy:
            return jsonify({
                'status': 'SYSTEM_ERROR',
                'error': 'System components not initialized properly',
                'initialization_errors': initialization_errors,
                'components_healthy': False
            }), 503
        
        # Default response structure
        response_data = {
            'status': 'UNKNOWN',
            'last_attack': None,
            'total_attacks': 0,
            'monitoring_active': False,
            'uptime_seconds': 0,
            'start_time': None,
            'monitored_files': 0,
            'event_count': 0,
            'components_healthy': components_healthy,
            'component_errors': []
        }
        
        # Get system status from audit logger with error handling
        if audit_logger:
            try:
                system_status = audit_logger.get_system_status()
                response_data.update({
                    'status': system_status.status,
                    'last_attack': system_status.last_attack,
                    'total_attacks': system_status.total_attacks,
                    'uptime_seconds': system_status.uptime_seconds,
                    'start_time': system_status.start_time
                })
            except Exception as e:
                response_data['component_errors'].append(f'Audit logger error: {str(e)}')
                response_data['status'] = 'DEGRADED'
        else:
            response_data['component_errors'].append('Audit logger not available')
            response_data['status'] = 'DEGRADED'
        
        # Get monitoring service status with error handling
        if monitor_service:
            try:
                monitor_status = monitor_service.get_status()
                response_data.update({
                    'monitoring_active': monitor_status.get('is_running', False),
                    'monitored_files': monitor_status.get('monitored_files', 0),
                    'event_count': monitor_status.get('event_count', 0),
                    'monitor_health': monitor_status.get('health_status', 'unknown'),
                    'monitor_errors': monitor_status.get('last_error', None)
                })
            except Exception as e:
                response_data['component_errors'].append(f'Monitor service error: {str(e)}')
                response_data['status'] = 'DEGRADED'
        else:
            response_data['component_errors'].append('Monitor service not available')
            response_data['status'] = 'DEGRADED'
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'error': f'System status check failed: {str(e)}',
            'components_healthy': False
        }), 500


@app.route('/api/attacks')
def get_recent_attacks():
    """
    API endpoint to get recent attack events with graceful degradation
    
    Returns:
        JSON response with list of recent attacks
    """
    try:
        # Check if components are available
        if not components_healthy or not audit_logger:
            return jsonify({
                'attacks': [],
                'total_count': 0,
                'error': 'Audit logger not available',
                'components_healthy': components_healthy
            }), 503
        
        # Get limit from query parameter (default 10)
        try:
            limit = request.args.get('limit', 10, type=int)
            if limit < 1 or limit > 100:  # Reasonable bounds
                limit = 10
        except (ValueError, TypeError):
            limit = 10
        
        # Get recent attacks from audit logger with error handling
        try:
            recent_attacks = audit_logger.get_recent_attacks(limit)
        except Exception as e:
            return jsonify({
                'attacks': [],
                'total_count': 0,
                'error': f'Failed to retrieve attacks: {str(e)}'
            }), 500
        
        # Convert to JSON-serializable format with error handling
        attacks_data = []
        for attack in recent_attacks:
            try:
                attacks_data.append({
                    'attack_id': attack.attack_id,
                    'timestamp': attack.timestamp,
                    'event_type': attack.event_type,
                    'filename': attack.filename,
                    'file_path': attack.file_path,
                    'process_name': attack.process_name,
                    'process_id': attack.process_id,
                    'username': attack.username,
                    'command_line': attack.command_line,
                    'ip_address': attack.ip_address
                })
            except Exception as e:
                print(f"Warning: Error serializing attack data: {e}")
                # Continue with other attacks even if one fails
                continue
        
        return jsonify({
            'attacks': attacks_data,
            'total_count': len(attacks_data),
            'components_healthy': components_healthy
        })
        
    except Exception as e:
        return jsonify({
            'attacks': [],
            'total_count': 0,
            'error': f'Attack retrieval failed: {str(e)}',
            'components_healthy': False
        }), 500


@app.route('/api/simulate', methods=['POST'])
def simulate_attack():
    """
    API endpoint to simulate an attack on honey-tokens with step-by-step demonstration
    
    Returns:
        JSON response with detailed simulation results
    """
    simulation_steps = []
    
    try:
        # Check if components are available
        if not components_healthy or not honey_token_manager or not audit_logger:
            return jsonify({
                'success': False,
                'error': 'Required system components not available',
                'simulation_steps': [],
                'components_healthy': components_healthy
            }), 503
        
        # Get simulation parameters from request
        request_data = {}
        try:
            request_data = request.get_json() or {}
        except Exception as json_error:
            return jsonify({
                'success': False,
                'error': f'Invalid JSON in request: {str(json_error)}',
                'simulation_steps': []
            }), 400
        
        attack_type = request_data.get('attack_type', 'file_access')
        target_file_name = request_data.get('target_file', None)
        
        # Get honey-token paths with error handling
        try:
            token_paths = honey_token_manager.get_token_paths()
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to get honey-token paths: {str(e)}',
                'simulation_steps': []
            }), 500
        
        if not token_paths:
            return jsonify({
                'success': False,
                'error': 'No honey-tokens available for simulation',
                'simulation_steps': []
            }), 400
        
        # Select target file for simulation
        if target_file_name:
            # Find specific file if requested
            target_file = None
            for path in token_paths:
                if Path(path).name == target_file_name:
                    target_file = path
                    break
            if not target_file:
                return jsonify({
                    'success': False,
                    'error': f'Honey-token file "{target_file_name}" not found',
                    'simulation_steps': []
                }), 400
        else:
            # Select first available honey-token
            target_file = token_paths[0]
        
        # Get system status before attack
        status_before = audit_logger.get_system_status()
        
        # Perform the attack simulation based on type
        
        # Step 1: Record initial state
        simulation_steps.append({
            'step': 1,
            'action': 'Initial System State',
            'description': f'System status: {status_before.status}',
            'details': {
                'status': status_before.status,
                'total_attacks': status_before.total_attacks,
                'monitoring_active': status_before.monitoring_active
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Step 2: Target selection
        target_filename = Path(target_file).name
        simulation_steps.append({
            'step': 2,
            'action': 'Target Selection',
            'description': f'Selected honey-token: {target_filename}',
            'details': {
                'target_file': target_filename,
                'file_path': target_file,
                'attack_type': attack_type
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Step 3: Execute attack simulation
        attack_executed = False
        attack_content = None
        
        try:
            if attack_type == 'file_access':
                # Simulate file access by reading the file
                with open(target_file, 'r') as f:
                    content = f.read()
                    attack_content = content[:100] + '...' if len(content) > 100 else content
                attack_executed = True
                
            elif attack_type == 'file_modification':
                # Simulate file modification
                with open(target_file, 'a') as f:
                    f.write('\n# Simulated modification by attacker')
                attack_executed = True
                
            elif attack_type == 'file_copy':
                # Simulate file copying
                import shutil
                temp_copy = target_file + '.copy'
                shutil.copy2(target_file, temp_copy)
                # Read the copied file to trigger access
                with open(temp_copy, 'r') as f:
                    content = f.read()
                    attack_content = content[:100] + '...' if len(content) > 100 else content
                # Clean up the copy
                os.remove(temp_copy)
                attack_executed = True
            else:
                # Default to file access for unknown types
                with open(target_file, 'r') as f:
                    content = f.read()
                    attack_content = content[:100] + '...' if len(content) > 100 else content
                attack_executed = True
                attack_type = 'file_access'  # Normalize the type
                
        except Exception as attack_error:
            simulation_steps.append({
                'step': 3,
                'action': 'Attack Execution',
                'description': f'Attack simulation failed: {str(attack_error)}',
                'details': {'error': str(attack_error)},
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            return jsonify({
                'success': False,
                'error': f'Attack simulation failed: {str(attack_error)}',
                'simulation_steps': simulation_steps
            }), 500
        
        simulation_steps.append({
            'step': 3,
            'action': 'Attack Execution',
            'description': f'Successfully executed {attack_type} on {target_filename}',
            'details': {
                'attack_type': attack_type,
                'content_preview': attack_content[:50] + '...' if attack_content and len(attack_content) > 50 else attack_content
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Step 4: Wait for monitoring system to detect
        import time
        time.sleep(0.8)  # Give monitoring system time to detect
        
        simulation_steps.append({
            'step': 4,
            'action': 'Detection Processing',
            'description': 'Waiting for monitoring system to detect unauthorized access...',
            'details': {'wait_time': '0.8 seconds'},
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Step 5: Check for attack detection
        recent_attacks = audit_logger.get_recent_attacks(3)
        detected_attack = None
        
        # Find the most recent attack that matches our simulation
        for attack in recent_attacks:
            if attack.filename == target_filename:
                detected_attack = attack
                break
        
        if detected_attack:
            simulation_steps.append({
                'step': 5,
                'action': 'Attack Detected',
                'description': f'Honey-token access detected! Attack ID: {detected_attack.attack_id}',
                'details': {
                    'attack_id': detected_attack.attack_id,
                    'event_type': detected_attack.event_type,
                    'process_name': detected_attack.process_name,
                    'username': detected_attack.username,
                    'detection_time': detected_attack.timestamp
                },
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        else:
            simulation_steps.append({
                'step': 5,
                'action': 'Detection Status',
                'description': 'Attack may not have been detected (monitoring might be inactive)',
                'details': {'monitoring_active': status_before.monitoring_active},
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        
        # Step 6: Get final system status
        status_after = audit_logger.get_system_status()
        
        simulation_steps.append({
            'step': 6,
            'action': 'Final System State',
            'description': f'System status changed to: {status_after.status}',
            'details': {
                'status_before': status_before.status,
                'status_after': status_after.status,
                'total_attacks_before': status_before.total_attacks,
                'total_attacks_after': status_after.total_attacks,
                'attack_detected': detected_attack is not None
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Prepare comprehensive simulation result
        simulation_result = {
            'success': True,
            'message': 'Attack simulation completed with step-by-step demonstration',
            'simulation_id': f'SIM_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}',
            'simulation_steps': simulation_steps,
            'summary': {
                'attack_type': attack_type,
                'target_file': target_filename,
                'attack_detected': detected_attack is not None,
                'status_changed': status_before.status != status_after.status,
                'detection_time': detected_attack.timestamp if detected_attack else None
            },
            'before_state': {
                'status': status_before.status,
                'total_attacks': status_before.total_attacks,
                'monitoring_active': status_before.monitoring_active
            },
            'after_state': {
                'status': status_after.status,
                'total_attacks': status_after.total_attacks,
                'monitoring_active': status_after.monitoring_active
            },
            'attack_details': {
                'attack_id': detected_attack.attack_id if detected_attack else None,
                'timestamp': detected_attack.timestamp if detected_attack else None,
                'event_type': detected_attack.event_type if detected_attack else None,
                'filename': detected_attack.filename if detected_attack else target_filename,
                'file_path': detected_attack.file_path if detected_attack else target_file,
                'process_name': detected_attack.process_name if detected_attack else 'python',
                'username': detected_attack.username if detected_attack else 'simulator'
            }
        }
        
        return jsonify(simulation_result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Simulation failed: {str(e)}',
            'simulation_steps': simulation_steps if 'simulation_steps' in locals() else []
        }), 500


@app.route('/api/reset', methods=['POST'])
def reset_system():
    """
    API endpoint to reset the system to clean state
    
    Returns:
        JSON response with reset results
    """
    try:
        # Reset the audit logger (clears logs and status)
        reset_success = audit_logger.reset_system()
        
        if reset_success:
            # Recreate honey-tokens to ensure they're in original state
            honey_token_manager.create_honey_tokens()
            
            return jsonify({
                'success': True,
                'message': 'System reset to clean state successfully',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to reset system'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Reset failed: {str(e)}'
        }), 500


@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """
    API endpoint to start the monitoring service
    
    Returns:
        JSON response with start results
    """
    try:
        global monitoring_thread
        
        if monitor_service.is_running():
            return jsonify({
                'success': True,
                'message': 'Monitoring is already active'
            })
        
        # Start monitoring service
        success = monitor_service.start_monitoring()
        
        if success:
            # Update audit logger monitoring status
            audit_logger.set_monitoring_status(True)
            
            return jsonify({
                'success': True,
                'message': 'Monitoring service started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start monitoring service'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start monitoring: {str(e)}'
        }), 500


@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """
    API endpoint to stop the monitoring service
    
    Returns:
        JSON response with stop results
    """
    try:
        if not monitor_service.is_running():
            return jsonify({
                'success': True,
                'message': 'Monitoring is not currently active'
            })
        
        # Stop monitoring service
        success = monitor_service.stop_monitoring()
        
        if success:
            # Update audit logger monitoring status
            audit_logger.set_monitoring_status(False)
            
            return jsonify({
                'success': True,
                'message': 'Monitoring service stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to stop monitoring service'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to stop monitoring: {str(e)}'
        }), 500


@app.route('/api/honey-tokens')
def get_honey_tokens():
    """
    API endpoint to get available honey-token files for simulation
    
    Returns:
        JSON response with list of honey-token files
    """
    try:
        # Get honey-token paths
        token_paths = honey_token_manager.get_token_paths()
        
        # Convert to file information
        honey_tokens = []
        for path in token_paths:
            file_path = Path(path)
            if file_path.exists():
                honey_tokens.append({
                    'filename': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() + 'Z'
                })
        
        return jsonify({
            'honey_tokens': honey_tokens,
            'total_count': len(honey_tokens)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/statistics')
def get_statistics():
    """
    API endpoint to get attack statistics and analytics
    
    Returns:
        JSON response with system statistics
    """
    try:
        # Get attack statistics
        stats = audit_logger.get_attack_statistics()
        
        # Get system status for additional info
        system_status = audit_logger.get_system_status()
        monitor_status = monitor_service.get_status()
        
        # Combine statistics
        response_data = {
            'attack_statistics': stats,
            'system_info': {
                'total_attacks': system_status.total_attacks,
                'current_status': system_status.status,
                'uptime_seconds': system_status.uptime_seconds,
                'monitoring_active': monitor_status['is_running'],
                'monitored_files': monitor_status['monitored_files']
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def initialize_system():
    """Initialize the honey-token system on startup"""
    try:
        print("🍯 Initializing Honey-Token Dashboard System")
        print("=" * 50)
        
        # Create honey-tokens
        print("Creating honey-tokens...")
        honey_token_manager.create_honey_tokens()
        
        # Verify tokens
        print("Verifying honey-tokens...")
        verification_results = honey_token_manager.verify_tokens()
        
        for filename, exists in verification_results.items():
            status = "✓" if exists else "✗"
            print(f"  {status} {filename}")
        
        # Initialize audit logger
        print("Initializing audit logger...")
        audit_logger.set_monitoring_status(False)  # Initially not monitoring
        
        print("System initialization completed!")
        print(f"Dashboard will be available at: http://localhost:5000")
        
    except Exception as e:
        print(f"Error during system initialization: {e}")


if __name__ == '__main__':
    # Initialize system components
    initialize_system()
    
    # Run Flask application
    import platform
    # Use 127.0.0.1 on Windows, 0.0.0.0 on Linux/Mac
    host = '127.0.0.1' if platform.system() == 'Windows' else '0.0.0.0'
    app.run(
        host=host,
        port=5000,
        debug=True,
        threaded=True
    )