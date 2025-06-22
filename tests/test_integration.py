#!/usr/bin/python3
"""
Integration tests for the fromcavestocars Flask application.
Tests all major pages to ensure they are functioning correctly.
"""

import os
import sys
import unittest
import tempfile
import warnings
import unittest.mock

# Add parent directory to path so we can import application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
import fromcavestocars
from fromcavestocars import app, USERDB

class FromCavesToCarsIntegrationTests(unittest.TestCase):
    """Integration tests for the From Caves To Cars application."""

    def setUp(self):
        """Set up test client and test database."""
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory database
        
        self.app = app.test_client()
        
        # Create application context and database tables
        with app.app_context():
            USERDB.create_all()
            
        # Skip init_stats_if_needed because it requires an actual item database
        self.patcher = unittest.mock.patch('fromcavestocars.init_stats_if_needed')
        self.mock_init_stats = self.patcher.start()
        
        # Create a minimal mock for POSSIBLEITEMSTATS when needed
        self.stats_patcher = unittest.mock.patch('fromcavestocars.POSSIBLEITEMSTATS', {
            'wood': {'label': 'wood', 'url': '/game', 'uniqueitems': 5, 'totalitems': 10},
            'stone': {'label': 'stone', 'url': '/game', 'uniqueitems': 3, 'totalitems': 6}
        })
        self.mock_stats = self.stats_patcher.start()
    
    def tearDown(self):
        """Clean up after tests."""
        with app.app_context():
            USERDB.drop_all()
        
        # Stop the patchers
        self.patcher.stop()
        self.stats_patcher.stop()
    
    def register_test_user(self, username='testuser', password='password'):
        """Helper method to register a test user."""
        return self.app.post(
            '/register', 
            data={'username': username, 'password': password},
            follow_redirects=True
        )
    
    def login_test_user(self, username='testuser', password='password'):
        """Helper method to log in a test user."""
        return self.app.post(
            '/login', 
            data={'username': username, 'password': password},
            follow_redirects=True
        )
    
    def test_home_page(self):
        """Test that the home page loads."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Caves', response.data)
        self.assertIn(b'To', response.data)
        self.assertIn(b'Cars', response.data)
        self.assertIn(b'Make a random item', response.data)
        self.assertIn(b'Choose an item to make', response.data)

    def test_login_page(self):
        """Test that the login page loads."""
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'login', response.data.lower())
        self.assertIn(b'<input type="text" name="username"', response.data)
        self.assertIn(b'<input type="password" name="password"', response.data)

    def test_register_page(self):
        """Test that the registration page loads."""
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create Account', response.data)
        self.assertIn(b'<input type="text" name="username"', response.data)
        self.assertIn(b'<input type="password" name="password"', response.data)

    def test_registration_and_login_flow(self):
        """Test the user registration and login flow."""
        # Register a new user
        reg_response = self.register_test_user()
        self.assertEqual(reg_response.status_code, 200)
        
        # Log out the user
        self.app.get('/logout', follow_redirects=True)
        
        # Try to login with the new user
        login_response = self.login_test_user()
        self.assertEqual(login_response.status_code, 200)
        self.assertNotIn(b'Invalid username or password', login_response.data)
        
        # Check if we're redirected to the home page
        self.assertIn(b'Make a random item', login_response.data)

    def test_item_choice_page(self):
        """Test that the item choice page loads."""
        # Register and login a user first
        self.register_test_user()
        
        # Mock the POSSIBLEITEMSTATS dictionary itself since we can't mock the values() method
        items_dict = {
            'wood': {'label': 'wood', 'url': '/game?item_name=wood', 'uniqueitems': 5, 'totalitems': 10},
            'stone': {'label': 'stone', 'url': '/game?item_name=stone', 'uniqueitems': 3, 'totalitems': 6}
        }
        
        with unittest.mock.patch('fromcavestocars.POSSIBLEITEMSTATS', items_dict):
            # Access the item choice page
            response = self.app.get('/choose')
            self.assertEqual(response.status_code, 200)

    def test_game_page(self):
        """Test that the game page loads."""
        # Register and login a user first
        self.register_test_user()
        
        # Additional mocking needed for game page
        with unittest.mock.patch('fromcavestocars._get_page_data') as mock_get_page_data, \
             unittest.mock.patch('fromcavestocars.get_known_items') as mock_get_known_items:
            
            # Setup mock return values
            mock_get_page_data.return_value = {
                'box_groups': [{'label': 'Step 1', 'description': 'First step', 'boxes': []}],
                'boxes': [],
                'header_image_url': '/static/images/default.png',
                'header_title': 'Wood',
                'completion_image_url': '/static/images/default.png',
                'page_description': 'Description of wood',
                'base_items': []
            }
            mock_get_known_items.return_value = ['wood', 'stone']
            
            # Access the game page
            response = self.app.get('/game')
            self.assertEqual(response.status_code, 200)
            
            # Additional assertions about page content
            self.assertIn(b'Description of wood', response.data)

    def test_credits_page(self):
        """Test that the credits page loads and contains acknowledgment."""
        response = self.app.get('/credits')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Credits', response.data)
        self.assertIn(b'Amazon Lambda', response.data)
        self.assertIn(b'Rajath Reghunath', response.data)
        self.assertIn(b'invaluable help in getting the Amazon Lambda integration', response.data)
        # Verify GitHub repository link is present
        self.assertIn(b'https://github.com/JustinCappos/fromcavestocars', response.data)
        self.assertIn(b'source code for this project is available on', response.data)

    def test_authenticated_user_accessing_login_page(self):
        """Test that an already authenticated user can access the login page without error."""
        # Register and login a user first
        self.register_test_user()
        
        # Now try to access the login page while authenticated
        # This should not cause an internal server error
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 302)  # Should redirect to home
        
        # Follow the redirect to ensure it goes to home
        response = self.app.get('/login', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Make a random item', response.data)  # Should be on home page

if __name__ == '__main__':
    unittest.main()
