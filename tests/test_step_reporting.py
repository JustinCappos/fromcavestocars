#!/usr/bin/env python3
"""
Test step name reporting functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import fromcavestocars
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fromcavestocars

class StepReportingTests(unittest.TestCase):
    """Test cases for step name reporting functionality"""
    
    def setUp(self):
        """Set up test client and mock data"""
        fromcavestocars.app.config['TESTING'] = True
        fromcavestocars.app.config['WTF_CSRF_ENABLED'] = False
        self.client = fromcavestocars.app.test_client()
        
        # Mock ITEMDB with test data
        self.mock_itemdb = MagicMock()
        self.mock_itemdb.items = {
            'test_item': MagicMock()
        }
        self.mock_itemdb.items['test_item'].steps = [
            {
                'step': 'Test Step 1',
                'description': 'This is a test step description.',
                'tools': [],
                'raw_materials': []
            },
            {
                'step': 'Test Step 2', 
                'description': 'This is another test step description.',
                'tools': [],
                'raw_materials': []
            }
        ]
        
        # Patch the ITEMDB
        fromcavestocars.ITEMDB = self.mock_itemdb
        
        # Initialize the database for tests
        with fromcavestocars.app.app_context():
            fromcavestocars.USERDB.create_all()
    
    def test_problem_route_with_step_name(self):
        """Test that the problem route accepts step_name parameter"""
        response = self.client.get('/problem?step_name=Test%20Step%201&referrer=/')
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains the step name
        self.assertIn(b'Test Step 1', response.data)
        self.assertIn(b'This is a test step description', response.data)
    
    def test_problem_route_with_item_name(self):
        """Test that the problem route still works with item_name parameter"""
        # Mock item with image data
        self.mock_itemdb.items['test_item'].description = 'Test item description'
        self.mock_itemdb.items['test_item'].image = [
            {'link': 'http://example.com/image1.jpg'},
            {'link': 'http://example.com/image2.jpg'}
        ]
        
        response = self.client.get('/problem?item_name=test_item&referrer=/')
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains item data
        self.assertIn(b'test_item', response.data)
        self.assertIn(b'Test item description', response.data)
    
    @patch('fromcavestocars.do_log')
    def test_problem_form_submission_with_step_name(self, mock_log):
        """Test form submission for step name evaluation"""
        form_data = {
            'step_name': 'Test Step 1',
            'description_accurate': 'no',
            'correct_item': 'no',
            'referrer': '/'
        }
        
        response = self.client.post('/problem', data=form_data, follow_redirects=False)
        self.assertEqual(response.status_code, 302)  # Redirect after form submission
        
        # Check that appropriate logging was called
        mock_log.assert_any_call('STEP_DESC_INACCURATE: Test Step 1')
        mock_log.assert_any_call('STEP_INACCURATE: Test Step 1')
    
    @patch('fromcavestocars.do_log')
    def test_problem_form_submission_with_item_name(self, mock_log):
        """Test form submission for item evaluation still works"""
        # Mock item with image data
        self.mock_itemdb.items['test_item'].image = [
            {'link': 'http://example.com/image1.jpg'},
            {'link': 'http://example.com/image2.jpg'}
        ]
        
        form_data = {
            'item_name': 'test_item',
            'selected_image_id': '0',
            'description_accurate': 'no', 
            'correct_item': 'yes',
            'good_image': 'no',
            'referrer': '/'
        }
        
        response = self.client.post('/problem', data=form_data, follow_redirects=False)
        self.assertEqual(response.status_code, 302)  # Redirect after form submission
        
        # Check that appropriate logging was called
        mock_log.assert_any_call('DESC_INACCURATE: test_item')
        mock_log.assert_any_call('ALL_IMAGES_INACCURATE: test_item')
    
    def test_step_name_not_found(self):
        """Test behavior when step name is not found in database"""
        response = self.client.get('/problem?step_name=Nonexistent%20Step&referrer=/')
        self.assertEqual(response.status_code, 200)
        
        # Should still render page but with default description
        self.assertIn(b'Nonexistent Step', response.data)
        self.assertIn(b'No description available', response.data)
    
    def test_game_template_contains_step_dragging_functionality(self):
        """Test that the game template includes step dragging functionality"""
        # This test checks that our template modifications are present
        with fromcavestocars.app.app_context():
            from flask import render_template_string
            
            # Mock template context data
            template_context = {
                'box_groups': [
                    {
                        'label': 'Test Step',
                        'description': 'Test step description',
                        'boxes': []
                    }
                ],
                'settings': {'skip_intro': True, 'skip_make_text': True},
                'box_fills': {},
                'images': [],
                'header_title': 'Test Item',
                'header_tags': [],
                'header_image_url': '/static/images/default.png',
                'completion_image_url': '/static/images/default.png',
                'page_description': 'Test description',
                'item_name': 'test_item',
                'exploration_path': 'test_item',
                'completion_url': '/',
                'new_items': []
            }
            
            # Read the actual game template
            with open('templates/game.html', 'r') as f:
                template_content = f.read()
            
            # Check that our modifications are present
            self.assertIn('data-step-name="{{ group.label }}"', template_content)
            self.assertIn('draggable="true"', template_content)
            self.assertIn('step-name', template_content)
            self.assertIn('stepLabels.forEach', template_content)


if __name__ == '__main__':
    unittest.main()