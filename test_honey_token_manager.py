"""
Unit tests for HoneyTokenManager class
"""
import unittest
import tempfile
import shutil
import json
from pathlib import Path
from honey_token_manager import HoneyTokenManager


class TestHoneyTokenManager(unittest.TestCase):
    """Test cases for HoneyTokenManager functionality"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.manager = HoneyTokenManager(base_directory=self.test_dir)
    
    def tearDown(self):
        """Clean up test environment after each test"""
        # Remove temporary directory and all contents
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test HoneyTokenManager initialization"""
        # Test default initialization
        default_manager = HoneyTokenManager()
        self.assertEqual(str(default_manager.base_directory), "honey_tokens")
        
        # Test custom directory initialization
        custom_manager = HoneyTokenManager("custom_dir")
        self.assertEqual(str(custom_manager.base_directory), "custom_dir")
        
        # Test that honey_tokens dictionary is populated
        self.assertGreater(len(self.manager.honey_tokens), 0)
        self.assertIn('passwords.txt', self.manager.honey_tokens)
        self.assertIn('api_keys.json', self.manager.honey_tokens)
    
    def test_create_honey_tokens_success(self):
        """Test successful creation of honey-token files"""
        # Create honey-tokens
        result = self.manager.create_honey_tokens()
        
        # Verify creation was successful
        self.assertTrue(result)
        
        # Verify directory was created
        self.assertTrue(Path(self.test_dir).exists())
        
        # Verify all files were created
        for filename in self.manager.honey_tokens.keys():
            file_path = Path(self.test_dir) / filename
            self.assertTrue(file_path.exists(), f"File {filename} was not created")
            
            # Verify file has content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertGreater(len(content), 0, f"File {filename} is empty")
    
    def test_create_honey_tokens_content_validation(self):
        """Test that created files contain expected realistic content"""
        self.manager.create_honey_tokens()
        
        # Test passwords.txt content
        passwords_path = Path(self.test_dir) / 'passwords.txt'
        with open(passwords_path, 'r') as f:
            passwords_content = f.read()
            self.assertIn('admin:', passwords_content)
            self.assertIn('root:', passwords_content)
            self.assertIn('P@ssw0rd123', passwords_content)
        
        # Test api_keys.json content and format
        api_keys_path = Path(self.test_dir) / 'api_keys.json'
        with open(api_keys_path, 'r') as f:
            api_content = f.read()
            # Verify it's valid JSON
            api_data = json.loads(api_content)
            self.assertIn('aws_access_key', api_data)
            self.assertIn('database_password', api_data)
        
        # Test database_backup.sql content
        db_path = Path(self.test_dir) / 'database_backup.sql'
        with open(db_path, 'r') as f:
            db_content = f.read()
            self.assertIn('CREATE TABLE', db_content)
            self.assertIn('users', db_content)
            self.assertIn('INSERT INTO', db_content)
        
        # Test config.env content
        config_path = Path(self.test_dir) / 'config.env'
        with open(config_path, 'r') as f:
            config_content = f.read()
            self.assertIn('DATABASE_URL=', config_content)
            self.assertIn('API_SECRET_KEY=', config_content)
        
        # Test ssh_keys.txt content
        ssh_path = Path(self.test_dir) / 'ssh_keys.txt'
        with open(ssh_path, 'r') as f:
            ssh_content = f.read()
            self.assertIn('BEGIN RSA PRIVATE KEY', ssh_content)
            self.assertIn('Host prod-server', ssh_content)
    
    def test_verify_tokens_all_exist(self):
        """Test verify_tokens when all files exist"""
        # Create tokens first
        self.manager.create_honey_tokens()
        
        # Verify tokens
        results = self.manager.verify_tokens()
        
        # All tokens should exist
        for filename, exists in results.items():
            self.assertTrue(exists, f"Token {filename} should exist")
        
        # Should have results for all expected tokens
        expected_tokens = set(self.manager.honey_tokens.keys())
        actual_tokens = set(results.keys())
        self.assertEqual(expected_tokens, actual_tokens)
    
    def test_verify_tokens_missing_files(self):
        """Test verify_tokens when some files are missing"""
        # Create tokens first
        self.manager.create_honey_tokens()
        
        # Remove one file manually
        test_file = Path(self.test_dir) / 'passwords.txt'
        test_file.unlink()
        
        # Verify tokens (should recreate missing file)
        results = self.manager.verify_tokens()
        
        # All tokens should exist after verification
        for filename, exists in results.items():
            self.assertTrue(exists, f"Token {filename} should exist after verification")
        
        # Verify the file was actually recreated
        self.assertTrue(test_file.exists(), "Missing file should have been recreated")
    
    def test_verify_tokens_no_directory(self):
        """Test verify_tokens when directory doesn't exist"""
        # Don't create tokens first
        
        # Verify tokens (should create directory and all files)
        results = self.manager.verify_tokens()
        
        # All tokens should exist after verification
        for filename, exists in results.items():
            self.assertTrue(exists, f"Token {filename} should exist after verification")
        
        # Directory should have been created
        self.assertTrue(Path(self.test_dir).exists())
    
    def test_get_token_paths(self):
        """Test get_token_paths method"""
        # Create tokens first
        self.manager.create_honey_tokens()
        
        # Get token paths
        paths = self.manager.get_token_paths()
        
        # Should have correct number of paths
        self.assertEqual(len(paths), len(self.manager.honey_tokens))
        
        # All paths should be absolute and exist
        for path in paths:
            self.assertTrue(Path(path).is_absolute(), f"Path {path} should be absolute")
            self.assertTrue(Path(path).exists(), f"Path {path} should exist")
        
        # Should contain expected filenames
        path_filenames = [Path(p).name for p in paths]
        expected_filenames = list(self.manager.honey_tokens.keys())
        self.assertEqual(set(path_filenames), set(expected_filenames))
    
    def test_get_token_count(self):
        """Test get_token_count method"""
        count = self.manager.get_token_count()
        
        # Should match the number of defined honey tokens
        expected_count = len(self.manager.honey_tokens)
        self.assertEqual(count, expected_count)
        self.assertGreater(count, 0, "Should have at least one honey token")
    
    def test_cleanup_tokens(self):
        """Test cleanup_tokens method"""
        # Create tokens first
        self.manager.create_honey_tokens()
        
        # Verify files exist
        for filename in self.manager.honey_tokens.keys():
            file_path = Path(self.test_dir) / filename
            self.assertTrue(file_path.exists(), f"File {filename} should exist before cleanup")
        
        # Cleanup tokens
        result = self.manager.cleanup_tokens()
        
        # Cleanup should be successful
        self.assertTrue(result)
        
        # Verify files are removed
        for filename in self.manager.honey_tokens.keys():
            file_path = Path(self.test_dir) / filename
            self.assertFalse(file_path.exists(), f"File {filename} should not exist after cleanup")
    
    def test_cleanup_tokens_no_files(self):
        """Test cleanup_tokens when no files exist"""
        # Don't create tokens first
        
        # Cleanup should still succeed
        result = self.manager.cleanup_tokens()
        self.assertTrue(result)
    
    def test_recreate_missing_tokens_partial(self):
        """Test _recreate_missing_tokens with specific files"""
        # Create tokens first
        self.manager.create_honey_tokens()
        
        # Remove specific files
        files_to_remove = ['passwords.txt', 'api_keys.json']
        for filename in files_to_remove:
            file_path = Path(self.test_dir) / filename
            file_path.unlink()
        
        # Recreate missing tokens
        self.manager._recreate_missing_tokens(files_to_remove)
        
        # Verify recreated files exist
        for filename in files_to_remove:
            file_path = Path(self.test_dir) / filename
            self.assertTrue(file_path.exists(), f"File {filename} should be recreated")
        
        # Verify other files still exist
        other_files = set(self.manager.honey_tokens.keys()) - set(files_to_remove)
        for filename in other_files:
            file_path = Path(self.test_dir) / filename
            self.assertTrue(file_path.exists(), f"File {filename} should still exist")
    
    def test_file_permissions(self):
        """Test that created files have correct permissions"""
        self.manager.create_honey_tokens()
        
        # Check file permissions (should be readable)
        for filename in self.manager.honey_tokens.keys():
            file_path = Path(self.test_dir) / filename
            
            # File should be readable
            self.assertTrue(file_path.is_file())
            
            # Should be able to read the file
            with open(file_path, 'r') as f:
                content = f.read()
                self.assertIsInstance(content, str)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)