from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings


class FrontendRoutingTests(SimpleTestCase):
    def test_dashboard_routes_serve_the_built_entry_point(self):
        with TemporaryDirectory() as directory:
            dist = Path(directory)
            (dist / 'index.html').write_text('<app-root></app-root>', encoding='utf-8')

            with override_settings(FRONTEND_DIST_DIR=dist):
                for path in ('/', '/lineups-summary', '/lineups-summary-api'):
                    with self.subTest(path=path):
                        response = self.client.get(path)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response['Content-Type'], 'text/html')
                        self.assertEqual(response['Cache-Control'], 'no-cache')
                        self.assertEqual(b''.join(response.streaming_content), b'<app-root></app-root>')
                        response.close()

    def test_missing_frontend_returns_404(self):
        with TemporaryDirectory() as directory:
            with override_settings(FRONTEND_DIST_DIR=Path(directory)):
                self.assertEqual(self.client.get('/').status_code, 404)

    def test_unknown_api_route_is_not_replaced_by_html(self):
        self.assertEqual(self.client.get('/api/v1/missing').status_code, 404)
