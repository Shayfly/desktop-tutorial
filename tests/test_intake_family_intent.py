"""Explicit product intent must survive incidental feature keywords."""
import unittest

from omni_prod.intake.families import classify_family, executable


class ProductIntentTests(unittest.TestCase):
    def test_explicit_product_wins_over_features(self):
        cases = [
            ('Build a website with video and a chatbot', 'website'),
            ('Build a responsive website with video and a chatbot', 'website'),
            ('Create a new web app with video uploads', 'web_app'),
            ('Do not build a website; create a mobile app', 'mobile_app'),
            ('I do not want a website; build a game with video cutscenes', 'game'),
            ("I don't want a game and I want a website with video", 'website'),
            ('Do not create a game and build a website with video', 'website'),
            ('Create a landing page for a game studio', 'website'),
            ('I want a website for automation consultants', 'website'),
            ('Create a web app with video uploads and a webhook', 'web_app'),
            ('Build a mobile app with a chatbot and videos', 'mobile_app'),
            ('Create an Android app with a game catalogue', 'mobile_app'),
            ('Build an AI agent that calls a webhook', 'ai_agent'),
            ('Create an automation that calls an API', 'automation'),
            ('Create an API integration for a game catalogue', 'api_integration'),
            ('Create a video about a game', 'media'),
            ('Create a 3D scene for a game studio', '3d_experience'),
            ('Build a game with video cutscenes', 'game'),
            ('אני רוצה לבנות אתר לחברת נסיעות בשם Test Travel', 'website'),
            ('בנה אתר עם סרטון וסוכן AI', 'website'),
            ('צור סוכן AI עם webhook', 'ai_agent'),
            ('בנה אפליקציה לנייד עם סרטונים', 'mobile_app'),
            ('צור אוטומציה עם API', 'automation'),
            ('צור סרטון על משחק', 'media'),
        ]
        for prompt, family in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(classify_family(prompt), family)

    def test_recognition_does_not_enable_unsupported_engines(self):
        for family in ('mobile_app', 'game', 'ai_agent', 'automation',
                       'api_integration', 'media', '3d_experience'):
            with self.subTest(family=family):
                self.assertFalse(executable(family))


if __name__ == '__main__':
    unittest.main()
