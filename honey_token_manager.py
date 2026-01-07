"""
Honey Token Manager - Creates and manages fake sensitive files for security monitoring
"""
import os
import json
from typing import Dict, List
from pathlib import Path


class HoneyTokenManager:
    """Manages creation and maintenance of honey-token files"""
    
    def __init__(self, base_directory: str = "honey_tokens"):
        """
        Initialize the HoneyTokenManager
        
        Args:
            base_directory: Directory where honey-tokens will be stored
        """
        self.base_directory = Path(base_directory)
        self.honey_tokens = {
            'passwords.txt': 'admin:P@ssw0rd123\nroot:SecretKey456\napi_user:Token789\ndatabase:MyDB_Pass2024',
            'api_keys.json': json.dumps({
                "aws_access_key": "AKIA1234567890EXAMPLE",
                "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "database_password": "MySecret123!",
                "jwt_secret": "super-secret-jwt-key-2024"
            }, indent=2),
            'database_backup.sql': '''-- Database Backup - CONFIDENTIAL
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(255),
    password_hash VARCHAR(255),
    email VARCHAR(255),
    created_at TIMESTAMP
);

INSERT INTO users VALUES (1, 'admin', 'sha256$salt$hash', 'admin@company.com', NOW());
INSERT INTO users VALUES (2, 'root', 'sha256$salt$hash', 'root@company.com', NOW());

-- Sensitive configuration
CREATE TABLE config (
    key_name VARCHAR(255),
    key_value TEXT
);

INSERT INTO config VALUES ('db_password', 'SuperSecret2024!');
INSERT INTO config VALUES ('api_endpoint', 'https://api.internal.company.com');''',
            'config.env': '''# Production Environment Configuration - DO NOT SHARE
DATABASE_URL=postgresql://admin:SecretPass123@prod-db.company.com:5432/maindb
REDIS_URL=redis://prod-redis.company.com:6379
API_SECRET_KEY=prod-secret-key-2024-do-not-leak
AWS_ACCESS_KEY_ID=AKIA1234567890PROD
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYPROD
ENCRYPTION_KEY=AES256-encryption-key-production''',
            'ssh_keys.txt': '''# SSH Private Keys - RESTRICTED ACCESS
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyz
AAAAB3NzaC1yc2EAAAADAQABAAABgQC1234567890abcdef
... (truncated for security)
-----END RSA PRIVATE KEY-----

# Production Server Access
Host prod-server
    HostName 10.0.1.100
    User root
    IdentityFile ~/.ssh/prod_key
    Port 22'''
        }
    
    def create_honey_tokens(self) -> bool:
        """
        Create all honey-token files with realistic fake data
        
        Returns:
            bool: True if all tokens were created successfully, False otherwise
        """
        try:
            # Create base directory if it doesn't exist
            self.base_directory.mkdir(parents=True, exist_ok=True)
            
            created_count = 0
            for filename, content in self.honey_tokens.items():
                file_path = self.base_directory / filename
                
                # Write the honey-token file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Set appropriate permissions (readable by owner and group)
                os.chmod(file_path, 0o644)
                created_count += 1
                
            print(f"Successfully created {created_count} honey-token files in {self.base_directory}")
            return True
            
        except Exception as e:
            print(f"Error creating honey-tokens: {e}")
            return False
    
    def verify_tokens(self) -> Dict[str, bool]:
        """
        Check if all honey-token files exist and recreate missing ones
        
        Returns:
            Dict[str, bool]: Dictionary mapping filename to existence status
        """
        verification_results = {}
        missing_tokens = []
        
        try:
            # Check each honey-token file
            for filename in self.honey_tokens.keys():
                file_path = self.base_directory / filename
                exists = file_path.exists()
                verification_results[filename] = exists
                
                if not exists:
                    missing_tokens.append(filename)
            
            # Recreate missing tokens
            if missing_tokens:
                print(f"Found {len(missing_tokens)} missing honey-tokens: {missing_tokens}")
                self._recreate_missing_tokens(missing_tokens)
                
                # Update verification results
                for filename in missing_tokens:
                    file_path = self.base_directory / filename
                    verification_results[filename] = file_path.exists()
            
            return verification_results
            
        except Exception as e:
            print(f"Error verifying honey-tokens: {e}")
            return verification_results
    
    def _recreate_missing_tokens(self, missing_tokens: List[str]) -> None:
        """
        Recreate specific missing honey-token files
        
        Args:
            missing_tokens: List of filenames to recreate
        """
        try:
            # Ensure directory exists
            self.base_directory.mkdir(parents=True, exist_ok=True)
            
            for filename in missing_tokens:
                if filename in self.honey_tokens:
                    file_path = self.base_directory / filename
                    content = self.honey_tokens[filename]
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    os.chmod(file_path, 0o644)
                    print(f"Recreated honey-token: {filename}")
                    
        except Exception as e:
            print(f"Error recreating missing tokens: {e}")
    
    def get_token_paths(self) -> List[str]:
        """
        Get list of all honey-token file paths
        
        Returns:
            List[str]: List of absolute paths to honey-token files
        """
        token_paths = []
        for filename in self.honey_tokens.keys():
            file_path = self.base_directory / filename
            token_paths.append(str(file_path.absolute()))
        
        return token_paths
    
    def get_token_count(self) -> int:
        """
        Get the total number of honey-tokens managed
        
        Returns:
            int: Number of honey-token files
        """
        return len(self.honey_tokens)
    
    def cleanup_tokens(self) -> bool:
        """
        Remove all honey-token files (for testing/cleanup purposes)
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        try:
            removed_count = 0
            for filename in self.honey_tokens.keys():
                file_path = self.base_directory / filename
                if file_path.exists():
                    file_path.unlink()
                    removed_count += 1
            
            print(f"Removed {removed_count} honey-token files")
            return True
            
        except Exception as e:
            print(f"Error cleaning up honey-tokens: {e}")
            return False


if __name__ == "__main__":
    # Demo usage
    manager = HoneyTokenManager()
    
    print("Creating honey-tokens...")
    success = manager.create_honey_tokens()
    
    if success:
        print("\nVerifying honey-tokens...")
        results = manager.verify_tokens()
        
        print("\nHoney-token status:")
        for filename, exists in results.items():
            status = "✓ EXISTS" if exists else "✗ MISSING"
            print(f"  {filename}: {status}")
        
        print(f"\nTotal honey-tokens: {manager.get_token_count()}")
        print("Honey-token paths:")
        for path in manager.get_token_paths():
            print(f"  {path}")

