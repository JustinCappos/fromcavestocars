#!/usr/bin/env python3
"""
Unit tests for pronoun replacement functionality
"""

import unittest
import sys
import os

# Add parent directory to path to import fromcavestocars
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fromcavestocars import apply_pronoun_preference


class PronounReplacementTests(unittest.TestCase):
    """Test cases for pronoun replacement functionality"""

    def test_neutral_preference_no_change(self):
        """Test that neutral preference doesn't change text"""
        text = "They walked to the river and saw him fishing."
        result = apply_pronoun_preference(text, "neutral")
        self.assertEqual(result, text)

    def test_he_preference_replaces_they(self):
        """Test that 'he' preference replaces 'they' with 'he'"""
        text = "They walked to the river."
        result = apply_pronoun_preference(text, "he")
        self.assertEqual(result, "he walked to the river.")

    def test_he_preference_replaces_them(self):
        """Test that 'he' preference replaces 'them' with 'him'"""
        text = "The tool helps them complete the task."
        result = apply_pronoun_preference(text, "he")
        self.assertEqual(result, "The tool helps him complete the task.")

    def test_he_preference_replaces_their(self):
        """Test that 'he' preference replaces 'their' with 'his'"""
        text = "They use their hands to shape the clay."
        result = apply_pronoun_preference(text, "he")
        self.assertEqual(result, "he use his hands to shape the clay.")

    def test_she_preference_replaces_he(self):
        """Test that 'she' preference replaces 'he' with 'she'"""
        text = "He walked to the river."
        result = apply_pronoun_preference(text, "she")
        self.assertEqual(result, "she walked to the river.")

    def test_she_preference_replaces_him(self):
        """Test that 'she' preference replaces 'him' with 'her'"""
        text = "The tool helps him complete the task."
        result = apply_pronoun_preference(text, "she")
        self.assertEqual(result, "The tool helps her complete the task.")

    def test_she_preference_replaces_his(self):
        """Test that 'she' preference replaces 'his' with 'her'"""
        text = "He uses his hands to shape the clay."
        result = apply_pronoun_preference(text, "she")
        self.assertEqual(result, "she uses her hands to shape the clay.")

    def test_they_preference_replaces_he(self):
        """Test that 'they' preference replaces 'he' with 'they'"""
        text = "He walked to the river."
        result = apply_pronoun_preference(text, "they")
        self.assertEqual(result, "they walked to the river.")

    def test_they_preference_replaces_him(self):
        """Test that 'they' preference replaces 'him' with 'them'"""
        text = "The tool helps him complete the task."
        result = apply_pronoun_preference(text, "they")
        self.assertEqual(result, "The tool helps them complete the task.")

    def test_they_preference_replaces_his(self):
        """Test that 'they' preference replaces 'his' with 'their'"""
        text = "He uses his hands to shape the clay."
        result = apply_pronoun_preference(text, "they")
        self.assertEqual(result, "they uses their hands to shape the clay.")

    def test_capitalized_pronouns(self):
        """Test that capitalized pronouns are handled correctly"""
        text = "He walked. They ran. She jumped."
        result = apply_pronoun_preference(text, "he")
        self.assertEqual(result, "He walked. he ran. he jumped.")

    def test_reflexive_pronouns_he(self):
        """Test that reflexive pronouns are replaced correctly for 'he'"""
        text = "They hurt themselves."
        result = apply_pronoun_preference(text, "he")
        self.assertEqual(result, "he hurt himself.")

    def test_reflexive_pronouns_she(self):
        """Test that reflexive pronouns are replaced correctly for 'she'"""
        text = "He hurt himself."
        result = apply_pronoun_preference(text, "she")
        self.assertEqual(result, "she hurt herself.")

    def test_reflexive_pronouns_they(self):
        """Test that reflexive pronouns are replaced correctly for 'they'"""
        text = "He hurt himself."
        result = apply_pronoun_preference(text, "they")
        self.assertEqual(result, "they hurt themselves.")

    def test_complex_sentence(self):
        """Test pronoun replacement in a complex sentence"""
        text = "The primitive human uses their hands to gather materials. They shape them carefully, ensuring his work is precise."
        result = apply_pronoun_preference(text, "she")
        # Note: "his" should become "her", "their" should become "her", "They" should become "she" (lowercase), "them" should become "her"
        self.assertIn("her hands", result)
        self.assertIn("she shape", result)
        self.assertIn("her work", result)

    def test_empty_text(self):
        """Test that empty text is handled correctly"""
        result = apply_pronoun_preference("", "he")
        self.assertEqual(result, "")

    def test_none_text(self):
        """Test that None text is handled correctly"""
        result = apply_pronoun_preference(None, "he")
        self.assertIsNone(result)

    def test_text_without_pronouns(self):
        """Test that text without pronouns is unchanged"""
        text = "The rock is hard and smooth."
        result = apply_pronoun_preference(text, "she")
        self.assertEqual(result, text)

    def test_possessive_pronouns(self):
        """Test possessive pronouns are replaced correctly"""
        text = "His tools are better than hers."
        result = apply_pronoun_preference(text, "they")
        self.assertEqual(result, "their tools are better than theirs.")


if __name__ == '__main__':
    unittest.main()
