import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.core.exceptions import ValidationError
from geoip2.errors import AddressNotFoundError
from maxminddb.errors import InvalidDatabaseError

from .models import CounterSettings, Hit, Page
from .services import client_ip, location_for


def configure(**fields):
    config = CounterSettings.load()
    for name, value in fields.items():
        setattr(config, name, value)
    config.full_clean()
    config.save()
    return config


class HitCounterTests(TestCase):
    def setUp(self):
        self.page = Page.objects.create(code='github-home', name='GitHub home')
        self.client = Client(enforce_csrf_checks=True)
        self.origin = {'HTTP_ORIGIN': 'https://9trees.github.io'}

    def log(self, code='github-home', **headers):
        return self.client.post(
            '/api/hits/', data=json.dumps({'page': code}),
            content_type='application/json', **headers,
        )

    def test_log_stores_hit_and_returns_counts_without_personal_data(self):
        response = self.log(**self.origin)
        self.assertEqual(response.status_code, 201)
        hit = Hit.objects.get()
        self.assertEqual(hit.page, self.page)
        self.assertEqual(hit.ip_address, '127.0.0.1')
        self.assertIsNotNone(hit.created_at.tzinfo)
        self.assertEqual(hit.location_status, Hit.LocationStatus.NOT_CONFIGURED)
        self.assertEqual(response.json()['location_status'], 'not_configured')
        self.assertEqual(response.json()['logged_at'], hit.created_at.isoformat())
        self.assertEqual(response.json()['total_hits'], 1)
        self.assertEqual(response.json()['today_hits'], 1)
        self.assertNotIn('ip_address', response.json())
        self.assertNotIn('city', response.json())
        self.assertEqual(response['Access-Control-Allow-Origin'], self.origin['HTTP_ORIGIN'])
        self.assertNotIn('Access-Control-Allow-Credentials', response)

    def test_repeated_requests_each_count_as_a_hit(self):
        self.log()
        response = self.log()
        self.assertEqual(response.json()['total_hits'], 2)

    def test_empty_counts_have_documented_shape_and_do_not_write(self):
        response = self.client.get('/api/hits/github-home/', **self.origin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'page': 'github-home', 'total_hits': 0, 'today_hits': 0,
            'date': datetime.now(timezone.utc).date().isoformat(), 'timezone': 'UTC',
        })
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertIn('Origin', response['Vary'])
        self.assertEqual(Hit.objects.count(), 0)

    @patch('hit_counter.services.timezone.now')
    def test_counts_use_half_open_utc_day_and_keep_pages_separate(self, now):
        now.return_value = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        other = Page.objects.create(code='other', name='Other')
        for timestamp in (
            datetime(2026, 10, 19, 23, 59, 59, tzinfo=timezone.utc),
            datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 10, 20, 23, 59, 59, tzinfo=timezone.utc),
            datetime(2026, 10, 21, 0, 0, tzinfo=timezone.utc),
        ):
            Hit.objects.create(
                page=self.page, created_at=timestamp, ip_address='192.0.2.1',
                location_status=Hit.LocationStatus.NOT_CONFIGURED,
            )
        Hit.objects.create(
            page=other, created_at=now.return_value, ip_address='192.0.2.2',
            location_status=Hit.LocationStatus.NOT_CONFIGURED,
        )
        self.assertEqual(self.client.get('/api/hits/github-home/').json(), {
            'page': 'github-home', 'total_hits': 4, 'today_hits': 2,
            'date': '2026-10-20', 'timezone': 'UTC',
        })

    @patch('hit_counter.services.timezone.now')
    def test_configured_timezone_handles_daylight_saving_boundary(self, now):
        configure(time_zone='America/New_York')
        now.return_value = datetime(2026, 11, 1, 18, tzinfo=timezone.utc)
        # November 1 is a 25-hour local day in New York.
        for hour, day in ((3, 1), (4, 1), (4, 2), (5, 2)):
            Hit.objects.create(
                page=self.page,
                created_at=datetime(2026, 11, day, hour, tzinfo=timezone.utc),
                ip_address='192.0.2.1',
                location_status=Hit.LocationStatus.NOT_CONFIGURED,
            )
        response = self.client.get('/api/hits/github-home/').json()
        self.assertEqual(response['today_hits'], 2)
        self.assertEqual(response['date'], '2026-11-01')
        self.assertEqual(response['timezone'], 'America/New_York')

    def test_missing_and_inactive_pages_do_not_log(self):
        self.page.is_active = False
        self.page.save()
        for code in ('unknown', self.page.code):
            self.assertEqual(self.log(code).status_code, 404)
            self.assertEqual(self.client.get('/api/hits/{}/'.format(code)).status_code, 404)
        self.assertFalse(Hit.objects.exists())

    def test_unknown_origin_is_rejected_before_writing(self):
        for response in (
            self.log(HTTP_ORIGIN='https://unwanted.example'),
            self.client.get('/api/hits/github-home/', HTTP_ORIGIN='null'),
        ):
            self.assertEqual(response.status_code, 403)
            self.assertNotIn('Access-Control-Allow-Origin', response)
        self.assertFalse(Hit.objects.exists())

    def test_json_preflight_does_not_log(self):
        response = self.client.options(
            '/api/hits/', HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type', **self.origin,
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response['Access-Control-Allow-Methods'], 'POST, OPTIONS')
        self.assertFalse(Hit.objects.exists())

    def test_preflight_rejects_unsupported_methods_headers_and_origins(self):
        for headers, status in (
            ({'HTTP_ACCESS_CONTROL_REQUEST_METHOD': 'DELETE'}, 405),
            ({'HTTP_ACCESS_CONTROL_REQUEST_HEADERS': 'Authorization'}, 400),
            ({'HTTP_ORIGIN': 'https://unwanted.example'}, 403),
        ):
            request_headers = {**self.origin, **headers}
            response = self.client.options('/api/hits/', **request_headers)
            self.assertEqual(response.status_code, status)
        self.assertFalse(Hit.objects.exists())

    def test_wrong_methods_have_json_errors(self):
        for method, url in (
            ('get', '/api/hits/'), ('put', '/api/hits/'),
            ('post', '/api/hits/github-home/'), ('head', '/api/hits/github-home/'),
        ):
            response = getattr(self.client, method)(url)
            self.assertEqual(response.status_code, 405)
            self.assertEqual(response['Content-Type'], 'application/json')
            self.assertIn('Allow', response)
        self.assertFalse(Hit.objects.exists())

    def test_invalid_json_and_page_codes(self):
        for body in (
            b'{', b'\xff', b'[]', b'null', b'1', b'{}',
            b'{"page": null}', b'{"page": 7}', b'{"page": ""}',
            b'{"page": "has spaces"}', b'{"page": "../admin"}',
            json.dumps({'page': 'x' * 101}).encode(),
            b'{"page": "github-home", "ip_address": "192.0.2.1"}',
        ):
            with self.subTest(body=body):
                response = self.client.post(
                    '/api/hits/', body, content_type='application/json',
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json())
        self.assertFalse(Hit.objects.exists())

    def test_wrong_content_type_and_oversized_body(self):
        self.assertEqual(self.client.post('/api/hits/', {'page': self.page.code}).status_code, 415)
        response = self.client.post(
            '/api/hits/', b' ' * 1025, content_type='application/json',
        )
        self.assertEqual(response.status_code, 413)
        self.assertFalse(Hit.objects.exists())

    def test_untrusted_forwarded_ip_is_ignored(self):
        self.log(REMOTE_ADDR='192.0.2.1', HTTP_X_FORWARDED_FOR='198.51.100.1')
        self.assertEqual(Hit.objects.get().ip_address, '192.0.2.1')

    def test_trusted_proxy_uses_last_address_not_spoofed_first_address(self):
        configure(trusted_proxy_ips='127.0.0.1')
        self.log(HTTP_X_FORWARDED_FOR='198.51.100.1, 2001:db8::1')
        self.assertEqual(Hit.objects.get().ip_address, '2001:db8::1')

    def test_invalid_remote_address_is_rejected(self):
        self.assertEqual(self.log(REMOTE_ADDR='invalid').status_code, 400)
        self.assertFalse(Hit.objects.exists())

    def test_invalid_forwarded_address_is_rejected(self):
        configure(trusted_proxy_ips='127.0.0.1')
        self.assertEqual(self.log(HTTP_X_FORWARDED_FOR='invalid').status_code, 400)
        self.assertFalse(Hit.objects.exists())

    def test_trusted_proxy_without_forwarded_header_uses_peer(self):
        config = configure(trusted_proxy_ips='127.0.0.1')
        request = RequestFactory().get('/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(client_ip(request, config), '127.0.0.1')

    @patch('hit_counter.views.location_for')
    def test_location_is_stored_but_never_returned(self, locate):
        locate.return_value = {
            'country': 'Example country', 'region': 'Example region',
            'city': 'Example city', 'location_status': Hit.LocationStatus.FOUND,
        }
        response = self.log(REMOTE_ADDR='192.0.2.1')
        locate.assert_called_once()
        self.assertEqual(locate.call_args.args[0], '192.0.2.1')
        hit = Hit.objects.get()
        self.assertEqual(hit.city, 'Example city')
        self.assertEqual(hit.country, 'Example country')
        self.assertEqual(hit.region, 'Example region')
        self.assertEqual(response.json()['location_status'], 'found')
        self.assertNotIn('Example city', response.content.decode())

    def test_broken_geoip_database_logs_error_and_hit_still_succeeds(self):
        configure(geoip_path='missing.mmdb')
        with self.assertLogs('hit_counter.services', level='ERROR'):
            response = self.log()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['location_status'], 'lookup_failed')
        self.assertEqual(Hit.objects.get().location_status, Hit.LocationStatus.LOOKUP_FAILED)

    def test_visitor_details_require_admin_login(self):
        response = self.client.get('/admin/hit_counter/hit/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_admin_can_view_but_not_add_or_edit_hits(self):
        user = get_user_model().objects.create_superuser('owner', 'owner@example.com', 'test-password')
        self.client.force_login(user)
        self.log()
        hit = Hit.objects.get()
        self.assertEqual(self.client.get('/admin/hit_counter/hit/').status_code, 200)
        self.assertEqual(self.client.get('/admin/hit_counter/hit/add/').status_code, 403)
        response = self.client.get('/admin/hit_counter/hit/{}/change/'.format(hit.pk))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')

    def test_settings_admin_opens_single_editable_record(self):
        user = get_user_model().objects.create_superuser('owner', 'owner@example.com', 'test-password')
        self.client = Client()
        self.client.force_login(user)
        response = self.client.get('/admin/hit_counter/countersettings/')
        self.assertRedirects(response, '/admin/hit_counter/countersettings/1/change/')
        self.assertEqual(CounterSettings.objects.count(), 1)
        self.assertEqual(self.client.get('/admin/hit_counter/countersettings/add/').status_code, 403)
        self.assertEqual(
            self.client.get('/admin/hit_counter/countersettings/1/delete/').status_code, 403,
        )
        response = self.client.post('/admin/hit_counter/countersettings/1/change/', {
            'allowed_origins': 'https://9trees.github.io\r\nhttps://forms.example.com',
            'time_zone': 'Asia/Kolkata',
            'trusted_proxy_ips': '10.0.0.1',
            'geoip_path': '',
        })
        self.assertEqual(response.status_code, 302)
        config = CounterSettings.load()
        self.assertEqual(config.origin_list, ['https://9trees.github.io', 'https://forms.example.com'])
        self.assertEqual(config.time_zone, 'Asia/Kolkata')

    def test_admin_changes_apply_to_api_without_restart(self):
        configure(allowed_origins='https://forms.example.com')
        self.assertEqual(self.log(**self.origin).status_code, 403)
        response = self.log(HTTP_ORIGIN='https://forms.example.com')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'https://forms.example.com')

    def test_defaults_apply_before_settings_are_saved(self):
        self.assertFalse(CounterSettings.objects.exists())
        config = CounterSettings.load()
        self.assertEqual(config.origin_list, ['https://9trees.github.io'])
        self.assertEqual(config.time_zone, 'UTC')
        self.assertEqual(config.proxy_ip_list, [])
        self.assertEqual(config.geoip_path, '')


class CounterSettingsValidationTests(TestCase):
    def test_rejects_invalid_values(self):
        for field, value in (
            ('allowed_origins', 'https://9trees.github.io/'),
            ('allowed_origins', 'https://9trees.github.io/repo'),
            ('allowed_origins', '9trees.github.io'),
            ('allowed_origins', 'ftp://9trees.github.io'),
            ('time_zone', 'Not/AZone'),
            ('time_zone', ''),
            ('trusted_proxy_ips', '10.0.0.300'),
        ):
            with self.subTest(field=field, value=value):
                config = CounterSettings(**{field: value})
                with self.assertRaises(ValidationError) as caught:
                    config.full_clean()
                self.assertIn(field, caught.exception.message_dict)

    def test_accepts_valid_values_and_saves_as_singleton(self):
        config = CounterSettings(
            allowed_origins='https://9trees.github.io\nhttp://localhost:8000',
            time_zone='Europe/London', trusted_proxy_ips='10.0.0.1\n2001:db8::1',
        )
        config.full_clean()
        config.save()
        CounterSettings(time_zone='UTC').save()
        self.assertEqual(CounterSettings.objects.count(), 1)
        self.assertEqual(CounterSettings.load().time_zone, 'UTC')


class LocalLocationTests(TestCase):
    def setUp(self):
        self.config = CounterSettings(geoip_path='city.mmdb')
    @patch('hit_counter.services.Reader')
    def test_local_database_result(self, reader):
        reader.return_value.__enter__.return_value.city.return_value = SimpleNamespace(
            country=SimpleNamespace(name='Country'),
            subdivisions=SimpleNamespace(most_specific=SimpleNamespace(name='Region')),
            city=SimpleNamespace(name='City'),
        )
        self.assertEqual(location_for('192.0.2.1', self.config), {
            'country': 'Country', 'region': 'Region', 'city': 'City',
            'location_status': 'found',
        })
        reader.assert_called_once_with('city.mmdb')
        reader.return_value.__enter__.return_value.city.assert_called_once_with('192.0.2.1')
        reader.return_value.__exit__.assert_called_once()

    @patch('hit_counter.services.Reader')
    def test_missing_place_names_are_empty(self, reader):
        reader.return_value.__enter__.return_value.city.return_value = SimpleNamespace(
            country=SimpleNamespace(name=None),
            subdivisions=SimpleNamespace(most_specific=SimpleNamespace(name=None)),
            city=SimpleNamespace(name=None),
        )
        self.assertEqual(location_for('192.0.2.1', self.config), {
            'country': '', 'region': '', 'city': '', 'location_status': 'found',
        })

    @patch('hit_counter.services.Reader')
    def test_ip_not_found(self, reader):
        reader.return_value.__enter__.return_value.city.side_effect = AddressNotFoundError('Not found')
        self.assertEqual(location_for('192.0.2.1', self.config), {'location_status': 'not_found'})

    @patch('hit_counter.services.Reader')
    def test_invalid_database_is_explicitly_logged(self, reader):
        reader.side_effect = InvalidDatabaseError('Invalid database')
        with self.assertLogs('hit_counter.services', level='ERROR'):
            self.assertEqual(location_for('192.0.2.1', self.config), {'location_status': 'lookup_failed'})

    @patch('hit_counter.services.Reader')
    def test_unconfigured_lookup_never_opens_database(self, reader):
        self.config.geoip_path = ''
        self.assertEqual(location_for('192.0.2.1', self.config), {'location_status': 'not_configured'})
        reader.assert_not_called()
