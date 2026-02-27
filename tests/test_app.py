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

        # 200 means page loaded unsuccessfully
        self.assertEqual(response.status_code, 200)

        # Check for 'Login'
        self.assertIn(b'Login', response.data)


if __name__ == '__main__':
    unittest.main()

