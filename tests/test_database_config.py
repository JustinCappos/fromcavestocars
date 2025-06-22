#!/usr/bin/python3
"""
Tests for database configuration functionality.
Verifies that the database configuration correctly chooses between PostgreSQL and SQLite.
"""

import os
import sys
import unittest
import unittest.mock

# Add parent directory to path so we can import application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
from fromcavestocars import get_database_uri, app


class DatabaseConfigurationTests(unittest.TestCase):
    """Tests for database configuration logic."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing environment variables
        self.original_env = {}
        for var in ['DB_USER', 'DB_PASSWORD', 'DB_NAME', 'DB_CONNECTION_NAME']:
            self.original_env[var] = os.environ.get(var)
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

    def test_sqlite_default_when_no_postgres_env_vars(self):
        """Test that SQLite is used when PostgreSQL environment variables are not set."""
        with app.app_context():
            app.config['TESTING'] = False
            uri = get_database_uri()
            self.assertEqual(uri, 'sqlite:///fctc.db')

    def test_sqlite_memory_for_testing(self):
        """Test that in-memory SQLite is used in testing mode."""
        with app.app_context():
            app.config['TESTING'] = True
            uri = get_database_uri()
            self.assertEqual(uri, 'sqlite:///:memory:')

    def test_postgresql_when_all_env_vars_present(self):
        """Test that PostgreSQL is used when all environment variables are present."""
        # Set PostgreSQL environment variables
        os.environ['DB_USER'] = 'testuser'
        os.environ['DB_PASSWORD'] = 'testpass'
        os.environ['DB_NAME'] = 'testdb'
        os.environ['DB_CONNECTION_NAME'] = 'test-project:test-region:test-instance'
        
        with app.app_context():
            app.config['TESTING'] = False
            uri = get_database_uri()
            expected = 'postgresql+psycopg2://testuser:testpass@/testdb?host=/cloudsql/test-project:test-region:test-instance'
            self.assertEqual(uri, expected)

    def test_sqlite_when_partial_postgres_env_vars(self):
        """Test that SQLite is used when only some PostgreSQL environment variables are present."""
        # Set only some PostgreSQL environment variables
        os.environ['DB_USER'] = 'testuser'
        os.environ['DB_PASSWORD'] = 'testpass'
        # Missing DB_NAME and DB_CONNECTION_NAME
        
        with app.app_context():
            app.config['TESTING'] = False
            uri = get_database_uri()
            self.assertEqual(uri, 'sqlite:///fctc.db')

    def test_testing_mode_overrides_postgres_env_vars(self):
        """Test that testing mode uses SQLite even when PostgreSQL environment variables are present."""
        # Set PostgreSQL environment variables
        os.environ['DB_USER'] = 'testuser'
        os.environ['DB_PASSWORD'] = 'testpass'
        os.environ['DB_NAME'] = 'testdb'
        os.environ['DB_CONNECTION_NAME'] = 'test-project:test-region:test-instance'
        
        with app.app_context():
            app.config['TESTING'] = True
            uri = get_database_uri()
            self.assertEqual(uri, 'sqlite:///:memory:')


if __name__ == '__main__':
    unittest.main()