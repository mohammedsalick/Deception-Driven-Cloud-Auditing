# Requirements Document

## Introduction

The Deception-Driven Cloud Auditing Framework is a simple security monitoring system that catches hackers using "honey-tokens" - fake files that look important but are actually traps. When someone tries to access these fake files, the system immediately knows something suspicious is happening and creates an alert. This helps detect attacks early instead of waiting for damage to occur.

The system runs on AWS EC2 and includes:
- Fake sensitive files (honey-tokens) placed as traps
- A monitoring service that watches these files 24/7
- A web dashboard showing if the system is "Safe" or "Under Attack"
- A demo feature that simulates attacks to show how the system works

## Requirements

### Requirement 1: Create Fake Files (Honey-Tokens)

**User Story:** As a security admin, I want to create fake sensitive files that look real, so that hackers will try to access them and get caught.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL create fake files like "passwords.txt", "database_backup.sql", "api_keys.json"
2. WHEN creating fake files THEN they SHALL contain realistic but fake data (dummy passwords, fake API keys)
3. WHEN the system runs THEN it SHALL place these files in common locations where attackers might look
4. IF a fake file gets deleted THEN the system SHALL recreate it automatically

### Requirement 2: Watch the Fake Files 24/7

**User Story:** As a security admin, I want the system to constantly monitor the fake files, so that any access is immediately detected.

#### Acceptance Criteria

1. WHEN someone opens a fake file THEN the system SHALL detect it instantly
2. WHEN someone tries to copy, move, or delete a fake file THEN the system SHALL catch that too
3. WHEN the monitoring starts THEN it SHALL run continuously without stopping
4. IF the monitoring crashes THEN it SHALL restart automatically

### Requirement 3: Record Attack Details

**User Story:** As a security admin, I want detailed information about who accessed the fake files, so that I can investigate the attack.

#### Acceptance Criteria

1. WHEN a fake file is accessed THEN the system SHALL record who did it, when, and what they did
2. WHEN an attack happens THEN the system SHALL save the attacker's username and IP address
3. WHEN recording attack info THEN it SHALL be saved in a simple format (like JSON or CSV)
4. WHEN an attack is detected THEN the system status SHALL change to "UNDER ATTACK"

### Requirement 4: Simple Web Dashboard

**User Story:** As a security admin, I want a simple web page that shows if the system is safe or under attack, so that I can quickly check the status.

#### Acceptance Criteria

1. WHEN I open the dashboard THEN it SHALL show "SAFE" (green) or "UNDER ATTACK" (red)
2. WHEN an attack happens THEN the dashboard SHALL update automatically without refreshing
3. WHEN there are attacks THEN the dashboard SHALL show a list of recent attacks with timestamps
4. WHEN the system is safe THEN it SHALL show how long it's been running without attacks

### Requirement 5: Sample Attack Demonstration

**User Story:** As a project demonstrator, I want to simulate attacks on the system, so that I can show how the honey-token detection works in real-time.

#### Acceptance Criteria

1. WHEN I click "Simulate Attack" THEN the system SHALL automatically access a honey-token file
2. WHEN the demo attack runs THEN it SHALL show the complete attack detection process step-by-step
3. WHEN demonstrating THEN the system SHALL show before (Safe) and after (Under Attack) states
4. WHEN the demo completes THEN it SHALL display the captured attack details (timestamp, file accessed, etc.)
5. WHEN running multiple demos THEN each SHALL create separate attack records for analysis

### Requirement 6: Easy Setup and Installation

**User Story:** As a student, I want the system to be easy to install and run on AWS EC2, so that I can quickly set up my project.

#### Acceptance Criteria

1. WHEN installing THEN the system SHALL work with basic Python and pip install commands
2. WHEN setting up THEN it SHALL automatically create all needed folders and files
3. WHEN starting THEN it SHALL check if all required libraries are installed
4. IF something is missing THEN it SHALL show clear error messages with fix instructions

### Requirement 7: System Reset and Management

**User Story:** As a project demonstrator, I want to reset the system to clean state, so that I can run fresh demonstrations.

#### Acceptance Criteria

1. WHEN I click "Reset System" THEN it SHALL clear all attack logs and return to "SAFE" status
2. WHEN resetting THEN it SHALL recreate all honey-token files in their original state
3. WHEN the system resets THEN the dashboard SHALL immediately show the clean state
4. WHEN managing the system THEN I SHALL be able to start/stop monitoring from the dashboard