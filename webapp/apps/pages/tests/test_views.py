from django.test import TestCase


class PageViewsTests(TestCase):
    def test_about(self):
        resp = self.client.get('/about/')
        self.assertEqual(resp.status_code, 200)

    def test_home(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_news(self):
        resp = self.client.get('/news/')
        self.assertEqual(resp.status_code, 302)

    def test_subscribed(self):
        resp = self.client.get('/subscribed/')
        self.assertEqual(resp.status_code, 200)