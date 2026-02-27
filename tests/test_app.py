import unittest
from app import create_app

class RoutesTestCase(unittest.TestCase):

    def setUp(self):
        # Create the app and a test client
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_home_route(self):
        # Test home page (login) loads correctly
        response = self.client.get('/')

        # 200 means page loaded successfully
        self.assertEqual(response.status_code, 200)

        # Check for 'Login'
        self.assertIn(b'Login', response.data)

    def test_student_dashboard_access(self):
        with self.client.session_transaction() as sess:
            # manually set session data that app expects
            sess['user_email'] = 'student@example.com'
            sess['user_role'] = 'student'

        response = self.client.get('/student_dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'student_dashboard', response.data)

    def test_student_dashboard_unauthorized(self):
        # Test access is denied if not logged in
        response = self.client.get('/student_dashboard', follow_redirects=True)

        # It should redirect back to login
        self.assertIn(b'Unauthorized access.', response.data)
        self.assertIn(b'Login', response.data)


if __name__ == '__main__':
    unittest.main()

