#!/usr/bin/python3
"""
Tests for production database error scenarios and database connection issues.
These tests verify that the application handles database errors gracefully.
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
from fromcavestocars import app, USERDB, User, check_database_connection


class ProductionErrorHandlingTests(unittest.TestCase):
    """Tests for production database error scenarios."""

    def setUp(self):
        """Set up test environment."""
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory database
        
        self.app = app.test_client()
        
        # Create application context and database tables
        with app.app_context():
            USERDB.create_all()

    def tearDown(self):
        """Clean up after tests."""
        with app.app_context():
            USERDB.drop_all()

    def test_registration_with_database_error(self):
        """Test user registration gracefully handles database errors."""
        # Mock database session to raise an exception
        with unittest.mock.patch.object(USERDB.session, 'commit') as mock_commit:
            mock_commit.side_effect = Exception("Database connection failed")
            
            # Try to register a user
            response = self.app.post('/register', data={
                'username': 'testuser',
                'password': 'testpass'
            })
            
            # Should return error message, not crash
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Registration service temporarily unavailable', response.data)

    def test_login_with_database_error(self):
        """Test user login gracefully handles database errors."""
        with app.app_context():
            # Mock database query to raise an exception
            with unittest.mock.patch('fromcavestocars.User.query') as mock_query:
                mock_query.filter_by.side_effect = Exception("Database connection failed")
                
                # Try to login
                response = self.app.post('/login', data={
                    'username': 'testuser',
                    'password': 'testpass'
                })
                
                # Should return error message, not crash
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Login service temporarily unavailable', response.data)

    def test_game_page_with_database_error(self):
        """Test game page gracefully handles database errors."""
        # First register and login a test user
        with app.app_context():
            user = User(username='testuser')
            user.set_password('testpass')
            USERDB.session.add(user)
            USERDB.session.commit()
        
        # Login the user
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        
        # Mock the item database loading to fail
        with unittest.mock.patch('fromcavestocars.init_stats_if_needed') as mock_init:
            mock_init.side_effect = Exception("Item database failed to load")
            
            # Try to access game page
            response = self.app.get('/game')
            
            # Should return error page, not crash
            self.assertEqual(response.status_code, 500)
            self.assertIn(b'Game service temporarily unavailable', response.data)

    def test_database_connection_check_failure(self):
        """Test that database connection check failures are handled gracefully."""
        with app.app_context():
            # Mock the database engine to fail
            with unittest.mock.patch.object(USERDB.engine, 'connect') as mock_connect:
                mock_connect.side_effect = Exception("Connection failed")
                
                # Check database connection
                result = check_database_connection()
                
                # Should return False, not crash
                self.assertFalse(result)

    def test_item_creation_with_database_error(self):
        """Test item creation gracefully handles database errors."""
        # First register and login a test user
        with app.app_context():
            user = User(username='testuser')
            user.set_password('testpass')
            USERDB.session.add(user)
            USERDB.session.commit()
        
        # Login the user
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        
        # Mock the init_stats_if_needed and _get_page_data to work properly
        with unittest.mock.patch('fromcavestocars.init_stats_if_needed'), \
             unittest.mock.patch('fromcavestocars._get_page_data') as mock_get_page_data, \
             unittest.mock.patch('fromcavestocars.POSSIBLEITEMSTATS', {'wood': {'name': 'wood'}}):
            
            # Setup mock return values
            mock_get_page_data.return_value = {
                'box_groups': [],
                'boxes': [],
                'header_image_url': '/static/images/default.png',
                'header_title': 'Test Item',
                'completion_image_url': '/static/images/default.png',
                'page_description': 'Test description',
                'base_items': [{'name': 'wood', 'description': 'Basic wood material'}]
            }
            
            # Try to access game page (which should work with mocked data)
            response = self.app.get('/game?item_name=wood')
            
            # The page should load successfully
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()