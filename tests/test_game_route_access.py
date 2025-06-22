#!/usr/bin/python3
"""
Tests for /game route access with both authenticated and non-authenticated users.
This test specifically validates the issue described in #51.
"""

import os
import sys
import unittest
import unittest.mock
import tempfile

# Add parent directory to path so we can import application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
import fromcavestocars
from fromcavestocars import app, USERDB, User


class GameRouteAccessTests(unittest.TestCase):
    """Tests for /game route access in various scenarios."""

    def setUp(self):
        """Set up test environment."""
        # Store original environment variables
        self.original_env = {}
        for var in ['DB_USER', 'DB_PASSWORD', 'DB_NAME', 'DB_CONNECTION_NAME']:
            self.original_env[var] = os.environ.get(var)
        
        # Clear environment variables for clean test
        for var in ['DB_USER', 'DB_PASSWORD', 'DB_NAME', 'DB_CONNECTION_NAME']:
            if var in os.environ:
                del os.environ[var]

    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

    def test_game_route_access_for_non_authenticated_user(self):
        """Test that non-authenticated users can access /game route (guest access)."""
        with app.app_context():
            app.config['TESTING'] = True
            app.config['WTF_CSRF_ENABLED'] = False
            
            # Ensure database tables exist
            USERDB.create_all()
            
            test_client = app.test_client()
            
            # Mock the functions that require external data to prevent API calls
            with unittest.mock.patch('fromcavestocars.init_stats_if_needed') as mock_init_stats, \
                 unittest.mock.patch('fromcavestocars._get_page_data') as mock_get_page_data, \
                 unittest.mock.patch('fromcavestocars.get_known_items') as mock_get_known_items, \
                 unittest.mock.patch('fromcavestocars.choice') as mock_choice:
                
                # Setup mock return values
                mock_choice.return_value = 'wheel'
                mock_get_page_data.return_value = {
                    'box_groups': [{'label': 'Step 1', 'description': 'First step', 'boxes': []}],
                    'boxes': [],
                    'header_image_url': '/static/images/default.png',
                    'header_title': 'Test Item',
                    'completion_image_url': '/static/images/default.png',
                    'page_description': 'Description of test item',
                    'base_items': [{'name': 'wood', 'description': 'Basic wood material'}]
                }
                mock_get_known_items.return_value = ['wood', 'stone']
                
                # Test game page access for non-authenticated user
                response = test_client.get('/game')
                
                # The custom login_required decorator allows access for all users
                self.assertEqual(response.status_code, 200, 
                               "Non-authenticated users should be able to access /game route")
                self.assertIn(b'game', response.data.lower(), 
                            "Response should contain game content")

    def test_game_route_access_for_authenticated_user(self):
        """Test that authenticated users can access /game route."""
        with app.app_context():
            app.config['TESTING'] = True
            app.config['WTF_CSRF_ENABLED'] = False
            
            # Ensure database tables exist
            USERDB.create_all()
            
            test_client = app.test_client()
            
            # Create and login a test user
            test_username = "testuser_auth"
            test_password = "testpassword123"
            
            # Register the user
            reg_response = test_client.post('/register', data={
                'username': test_username,
                'password': test_password
            }, follow_redirects=True)
            self.assertEqual(reg_response.status_code, 200)
            
            # Login the user
            login_response = test_client.post('/login', data={
                'username': test_username,
                'password': test_password
            }, follow_redirects=True)
            self.assertEqual(login_response.status_code, 200)
            
            # Mock the functions that require external data to prevent API calls
            with unittest.mock.patch('fromcavestocars.init_stats_if_needed') as mock_init_stats, \
                 unittest.mock.patch('fromcavestocars._get_page_data') as mock_get_page_data, \
                 unittest.mock.patch('fromcavestocars.get_known_items') as mock_get_known_items, \
                 unittest.mock.patch('fromcavestocars.choice') as mock_choice:
                
                # Setup mock return values
                mock_choice.return_value = 'wheel'
                mock_get_page_data.return_value = {
                    'box_groups': [{'label': 'Step 1', 'description': 'First step', 'boxes': []}],
                    'boxes': [],
                    'header_image_url': '/static/images/default.png',
                    'header_title': 'Test Item',
                    'completion_image_url': '/static/images/default.png',
                    'page_description': 'Description of test item',
                    'base_items': [{'name': 'wood', 'description': 'Basic wood material'}]
                }
                mock_get_known_items.return_value = ['wood', 'stone']
                
                # Test game page access for authenticated user
                response = test_client.get('/game')
                
                self.assertEqual(response.status_code, 200, 
                               "Authenticated users should be able to access /game route")
                self.assertIn(b'game', response.data.lower(), 
                            "Response should contain game content")
            
            # Clean up: delete the test user
            with app.app_context():
                test_user = User.query.filter_by(username=test_username).first()
                if test_user:
                    for item in test_user.known_items:
                        USERDB.session.delete(item)
                    USERDB.session.delete(test_user)
                    USERDB.session.commit()

    def test_game_route_with_production_database_failure(self):
        """Test /game route access when production database fails."""
        # Set up production environment variables that will fail
        os.environ['DB_USER'] = 'test_user'
        os.environ['DB_PASSWORD'] = 'test_password'
        os.environ['DB_NAME'] = 'test_db'
        os.environ['DB_CONNECTION_NAME'] = 'test-project:test-region:test-instance'
        
        with app.app_context():
            app.config['TESTING'] = False  # Simulate production
            
            # Manually set the database URI to PostgreSQL for this test
            original_uri = app.config['SQLALCHEMY_DATABASE_URI']
            postgres_uri = fromcavestocars.get_database_uri()
            app.config['SQLALCHEMY_DATABASE_URI'] = postgres_uri
            
            self.assertIn('postgresql', postgres_uri, "Should use PostgreSQL with environment variables set")
            
            # Check database connection (should fail)
            connection_success = fromcavestocars.check_database_connection()
            self.assertFalse(connection_success, "PostgreSQL connection should fail with fake credentials")
            
            # Test that application continues to function even with database failure
            test_client = app.test_client()
            
            # Mock the functions that require external data
            with unittest.mock.patch('fromcavestocars.init_stats_if_needed') as mock_init_stats, \
                 unittest.mock.patch('fromcavestocars._get_page_data') as mock_get_page_data, \
                 unittest.mock.patch('fromcavestocars.get_known_items') as mock_get_known_items, \
                 unittest.mock.patch('fromcavestocars.choice') as mock_choice:
                
                # Setup mock return values
                mock_choice.return_value = 'wheel'
                mock_get_page_data.return_value = {
                    'box_groups': [{'label': 'Step 1', 'description': 'First step', 'boxes': []}],
                    'boxes': [],
                    'header_image_url': '/static/images/default.png',
                    'header_title': 'Test Item',
                    'completion_image_url': '/static/images/default.png',
                    'page_description': 'Description of test item',
                    'base_items': [{'name': 'wood', 'description': 'Basic wood material'}]
                }
                mock_get_known_items.return_value = ['wood', 'stone']
                
                # The /game route should still be accessible even with database issues
                # because the custom login_required decorator doesn't enforce authentication
                response = test_client.get('/game')
                
                # Should get a response (not a 500 error)
                self.assertIn(response.status_code, [200, 302], 
                            "Game route should be accessible even with database issues")
            
            # Restore original URI
            app.config['SQLALCHEMY_DATABASE_URI'] = original_uri

    def test_database_fallback_mechanism(self):
        """Test that the database fallback mechanism works correctly."""
        # Set up production environment variables that will fail
        os.environ['DB_USER'] = 'test_user'
        os.environ['DB_PASSWORD'] = 'test_password'
        os.environ['DB_NAME'] = 'test_db'
        os.environ['DB_CONNECTION_NAME'] = 'test-project:test-region:test-instance'
        
        # Clear any existing fallback database
        fallback_db_path = 'fctc_fallback.db'
        if os.path.exists(fallback_db_path):
            os.remove(fallback_db_path)
        
        # Test the fallback URI function
        fallback_uri = fromcavestocars.get_fallback_database_uri()
        self.assertIn('sqlite', fallback_uri, "Fallback should use SQLite")
        
        # Test the connection test with fallback
        with app.app_context():
            app.config['TESTING'] = False  # Simulate production
            
            # This should detect PostgreSQL failure and fall back to SQLite
            tested_uri = fromcavestocars.get_database_uri_with_fallback()
            self.assertIn('sqlite', tested_uri, "Should fall back to SQLite when PostgreSQL fails")
        
        # Clean up
        if os.path.exists(fallback_db_path):
            os.remove(fallback_db_path)


if __name__ == '__main__':
    unittest.main()