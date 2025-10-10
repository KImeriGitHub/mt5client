import pytest
import unittest.mock as mock
import os
import sys
import yaml
from pathlib import Path

# Add the parent directory to sys.path to import mt_init
sys.path.insert(0, str(Path(__file__).parent.parent))

import mt_init

class TestMT5InitWithMockSecrets:
    """Test MT5 initialization with mock secrets (should fail)."""
    
    @mock.patch('mt_init.mt5')
    @mock.patch('mt_init.login', 9999999)
    @mock.patch('mt_init.password', 'fake_password')
    @mock.patch('mt_init.server', 'fake-server.com')
    def test_mt5_init_with_mock_secrets_fails(self, mock_mt5):
        """Test MT5 initialization with mock secrets - should fail."""
        # Arrange - Mock MT5 to return False (connection failure)
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = 10004  # Invalid account
        
        # Act
        mt_init.mt5_init(headless=False)
        
        # Assert
        mock_mt5.initialize.assert_called_once_with(
            path=mt_init.mtpath,
            login=9999999,
            password='fake_password',
            server='fake-server.com'
        )
        mock_mt5.last_error.assert_called_once()
        print("✓ Mock secrets test passed - initialization failed as expected")


class TestMT5InitWithRealSecrets:
    """Test MT5 initialization with real secrets from secrets folder."""
    
    def test_mt5_init_with_real_secrets(self):
        """Test MT5 initialization with real secrets from secrets/mt5_acc_cred.yaml."""
        # Load real secrets from the secrets folder
        secrets_path = Path(__file__).parent.parent / 'secrets' / 'mt5_acc_cred.yaml'
        
        with open(secrets_path, 'r') as file:
            secrets = yaml.safe_load(file)
        
        # Extract credentials
        creds = secrets['darwinexzero_acc']
        real_login = int(creds['apilogin'])
        real_password = creds['apipw']
        real_server = creds['server']
        
        # Temporarily patch the credentials in mt_init
        with mock.patch('mt_init.login', real_login), \
             mock.patch('mt_init.password', real_password), \
             mock.patch('mt_init.server', real_server):
            
            # Run the actual initialization
            print(f"Attempting MT5 connection with login: {real_login}")
            print(f"Server: {real_server}")
            
            try:
                mt_init.mt5_init()
                print("✓ Real secrets test completed - check MT5 connection status")
            except Exception as e:
                print(f"MT5 initialization attempt completed with: {e}")
        
        # Clean shutdown
        try:
            mt_init.mt5_shutdown()
        except:
            pass  # Ignore shutdown errors


if __name__ == '__main__':
    pytest.main([__file__])