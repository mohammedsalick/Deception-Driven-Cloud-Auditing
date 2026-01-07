# Design Document

## Overview

The Deception-Driven Cloud Auditing Framework is a Python-based security monitoring system that uses honey-tokens (fake sensitive files) to detect unauthorized access. The system runs on AWS EC2 and provides real-time monitoring with a web dashboard for status visualization and attack demonstration.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS EC2 Instance                        │
│                                                             │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │   Honey-Tokens  │    │     File System Monitor     │   │
│  │                 │    │                              │   │
│  │ • passwords.txt │◄───┤ • Python Watchdog Service   │   │
│  │ • api_keys.json │    │ • Real-time Event Detection │   │
│  │ • database.sql  │    │ • Attack Recording           │   │
│  └─────────────────┘    └──────────────────────────────┘   │
│                                     │                       │
│                                     ▼                       │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │   Audit Logs    │◄───┤      Web Dashboard          │   │
│  │                 │    │                              │   │
│  │ • attack_log.json    │ • Flask Web Server           │   │
│  │ • system_status.json │ • Real-time Status Display   │   │
│  │                 │    │ • Attack Simulation          │   │
│  └─────────────────┘    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

The system consists of four main components:

1. **Honey-Token Manager**: Creates and maintains fake sensitive files
2. **File Monitor Service**: Watches honey-tokens using Python Watchdog
3. **Audit Logger**: Records attack events and system status
4. **Web Dashboard**: Provides visual interface and demo capabilities

## Components and Interfaces

### 1. Environment Configuration

**File**: `.env`
```
# AWS EC2 Connection Details
AWS_EC2_SSH_COMMAND=ssh -i /path/to/your-key.pem ubuntu@your-ec2-public-ip
AWS_EC2_PUBLIC_IP=your-ec2-public-ip
AWS_EC2_USER=ubuntu
AWS_EC2_KEY_PATH=/path/to/your-key.pem

# Application Settings
FLASK_PORT=5000
MONITOR_INTERVAL=1
LOG_LEVEL=INFO
```

### 2. Honey-Token Manager

**Purpose**: Creates and manages fake sensitive files

**Key Methods**:
- `create_honey_tokens()`: Creates fake files with realistic content
- `verify_tokens()`: Checks if honey-tokens exist and recreates if missing
- `get_token_paths()`: Returns list of all honey-token file paths

**Honey-Token Files**:
```python
HONEY_TOKENS = {
    'passwords.txt': 'admin:P@ssw0rd123\nroot:SecretKey456\napi_user:Token789',
    'api_keys.json': '{"aws_key": "AKIA1234567890", "db_password": "MySecret123"}',
    'database_backup.sql': 'CREATE TABLE users (id INT, password VARCHAR(255));',
    'config.env': 'DATABASE_URL=postgresql://user:pass@localhost/db'
}
```

### 3. File Monitor Service

**Purpose**: Continuously monitors honey-token files for access

**Technology**: Python Watchdog library

**Key Classes**:
```python
class HoneyTokenHandler(FileSystemEventHandler):
    def on_accessed(self, event)
    def on_modified(self, event)
    def on_deleted(self, event)
    def on_moved(self, event)

class MonitorService:
    def start_monitoring()
    def stop_monitoring()
    def is_running()
```

**Event Detection**:
- File access (read operations)
- File modification (write operations)
- File deletion
- File movement/renaming

### 4. Audit Logger

**Purpose**: Records attack events and maintains system status

**Data Models**:
```python
# Attack Event Structure
{
    "timestamp": "2024-01-07T10:30:45Z",
    "event_type": "file_accessed",
    "file_path": "/home/ubuntu/passwords.txt",
    "username": "ubuntu",
    "process_name": "cat",
    "ip_address": "192.168.1.100",
    "attack_id": "ATK_001"
}

# System Status Structure
{
    "status": "SAFE|UNDER_ATTACK",
    "last_attack": "2024-01-07T10:30:45Z",
    "total_attacks": 5,
    "monitoring_active": true,
    "uptime_seconds": 3600
}
```

**Key Methods**:
- `log_attack_event()`: Records new attack with details
- `update_system_status()`: Updates overall security status
- `get_recent_attacks()`: Returns list of recent attack events
- `reset_system()`: Clears logs and resets to safe state

### 5. Web Dashboard

**Purpose**: Provides visual interface and demonstration capabilities

**Technology**: Flask web framework with real-time updates

**Routes**:
```python
@app.route('/')                    # Main dashboard
@app.route('/api/status')          # System status API
@app.route('/api/attacks')         # Recent attacks API
@app.route('/api/simulate')        # Simulate attack
@app.route('/api/reset')           # Reset system
```

**Dashboard Features**:
- Real-time status indicator (Safe/Under Attack)
- Attack history table with timestamps
- System statistics (uptime, total attacks)
- Demo buttons (Simulate Attack, Reset System)
- Auto-refresh every 5 seconds

## Data Models

### Attack Event Model
```python
class AttackEvent:
    def __init__(self):
        self.timestamp = datetime.utcnow()
        self.event_type = ""
        self.file_path = ""
        self.username = ""
        self.process_name = ""
        self.ip_address = ""
        self.attack_id = ""
```

### System Status Model
```python
class SystemStatus:
    def __init__(self):
        self.status = "SAFE"
        self.last_attack = None
        self.total_attacks = 0
        self.monitoring_active = False
        self.uptime_seconds = 0
        self.start_time = datetime.utcnow()
```

## Error Handling

### File System Errors
- **Missing honey-tokens**: Automatically recreate files
- **Permission errors**: Log error and continue monitoring
- **Disk space issues**: Rotate old logs automatically

### Monitoring Service Errors
- **Watchdog crashes**: Automatic restart with exponential backoff
- **High CPU usage**: Implement monitoring interval throttling
- **Memory leaks**: Periodic service restart every 24 hours

### Web Dashboard Errors
- **Flask server crashes**: Monitoring continues independently
- **Network connectivity**: Graceful degradation of real-time features
- **Browser compatibility**: Fallback to basic HTML without JavaScript

## Testing Strategy

### Unit Tests
- Honey-token creation and validation
- Attack event logging and retrieval
- System status management
- File monitoring event handling

### Integration Tests
- End-to-end attack simulation
- Dashboard API responses
- File system monitoring accuracy
- Multi-component interaction

### Demonstration Tests
- Simulate various attack scenarios
- Verify dashboard updates in real-time
- Test system reset functionality
- Validate attack detection accuracy

## Security Considerations

### System Protection
- Run monitoring service with minimal privileges
- Protect audit logs with appropriate file permissions
- Validate all user inputs to prevent injection attacks
- Use secure session management for dashboard access

### Honey-Token Security
- Ensure fake data appears realistic but contains no real secrets
- Place tokens in discoverable but not obvious locations
- Regularly rotate token content to maintain deception
- Monitor for attempts to modify the monitoring system itself

## Deployment Architecture

### AWS EC2 Setup
1. **Instance Configuration**: Ubuntu 20.04 LTS, t2.micro (Free Tier)
2. **Security Groups**: Allow SSH (22) and HTTP (5000) access
3. **File Structure**:
```
/home/ubuntu/honey-audit/
├── .env                    # Environment configuration
├── app.py                  # Main Flask application
├── monitor.py              # File monitoring service
├── honey_tokens/           # Directory containing fake files
│   ├── passwords.txt
│   ├── api_keys.json
│   └── database_backup.sql
├── logs/                   # Audit logs directory
│   ├── attacks.json
│   └── system_status.json
├── static/                 # Web dashboard assets
└── templates/              # HTML templates
```

### Installation Process
1. Connect to EC2 using SSH command from .env
2. Install Python 3 and pip
3. Install required packages: `pip install flask watchdog psutil`
4. Clone/upload project files
5. Configure .env file with EC2 details
6. Start monitoring service: `python monitor.py &`
7. Start web dashboard: `python app.py`

## Performance Considerations

### Resource Usage
- **CPU**: Minimal impact with efficient file watching
- **Memory**: < 50MB for entire system
- **Disk**: Log rotation to prevent unlimited growth
- **Network**: Lightweight dashboard with minimal bandwidth

### Scalability
- Support for multiple honey-token types
- Configurable monitoring intervals
- Extensible attack detection rules
- Modular component architecture for easy enhancement