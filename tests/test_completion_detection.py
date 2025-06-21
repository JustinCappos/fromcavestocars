#!/usr/bin/python3
"""
Tests for the JavaScript completion detection functionality.
"""

import os
import sys
import unittest
import re

# Add parent directory to path so we can import application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class CompletionDetectionTests(unittest.TestCase):
    """Tests for the completion detection functionality."""

    def test_game_template_contains_completion_detection_javascript(self):
        """Test that the game template contains the necessary JavaScript for completion detection."""
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'game.html')
        
        with open(template_path, 'r') as f:
            html_content = f.read()
            
        # Verify the completion detection JavaScript functions are present
        self.assertIn('function checkGroupCompleted(group)', html_content)
        self.assertIn('function markGroupCompleted(group)', html_content)
        self.assertIn('function checkAllGroupsCompleted()', html_content)
        self.assertIn('function showCompletionOverlay()', html_content)
        self.assertIn('function checkAndHandleCompletion()', html_content)
        
        # Verify the automatic completion check is called after drops
        self.assertIn('checkAndHandleCompletion();', html_content)
        
        # Verify the completion overlay element exists
        self.assertIn('id="completion-overlay"', html_content)

    def test_javascript_completion_logic_structure(self):
        """Test that the JavaScript completion logic is properly structured."""
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'game.html')
        
        with open(template_path, 'r') as f:
            html_content = f.read()
            
        # Check that the completion functions follow the right logic pattern
        
        # checkGroupCompleted should check if all boxes in a group have correct-drop class and children
        check_group_pattern = r'function checkGroupCompleted\(group\).*?boxes\.length === 0.*?correct-drop.*?children\.length > 0'
        self.assertTrue(re.search(check_group_pattern, html_content, re.DOTALL))
        
        # markGroupCompleted should add completed class to label and group
        mark_group_pattern = r'function markGroupCompleted\(group\).*?classList\.add\(\'completed\'\)'
        self.assertTrue(re.search(mark_group_pattern, html_content, re.DOTALL))
        
        # checkAndHandleCompletion should check all groups and show overlay if all completed
        check_handle_pattern = r'function checkAndHandleCompletion\(\).*?groups\.forEach.*?checkAllGroupsCompleted.*?showCompletionOverlay'
        self.assertTrue(re.search(check_handle_pattern, html_content, re.DOTALL))

    def test_drop_handler_calls_completion_check(self):
        """Test that the drop event handler calls the completion check function."""
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'game.html')
        
        with open(template_path, 'r') as f:
            html_content = f.read()
            
        # Verify that checkAndHandleCompletion is called in the drop handler success block
        # The call should be after a successful drop (result.status === 'locked')
        drop_success_pattern = r'result\.status === \'locked\'.*?correct-drop.*?checkAndHandleCompletion\(\);'
        self.assertTrue(re.search(drop_success_pattern, html_content, re.DOTALL))

if __name__ == '__main__':
    unittest.main()