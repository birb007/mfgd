import re

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from mfgd_app.models import UserProfile


class TestProfileCase(TestCase):
    FIELDS_REGEX = (
        r"""<div class="form_label">Username</div>"""
        r"""\s*<div class="form_control">"""
            r"""\s*<input type="text" name="username" value="(?P<name>\S*)" maxlength="150" required id="id_username">"""
        r"""\s*</div>"""
        r"""\s*<div class="form_label">Email address</div>"""
        r"""\s*<div class="form_control">"""
            r"""\s*<input type="email" name="email" value="(?P<email>\S*)" maxlength="254" required id="id_email">"""
        r"""\s*</div>"""
    )

    def setUp(self):
        passwd = make_password("p4ssw0rd1")
        user = User.objects.create(username="user", email="user@example.com", password=passwd)
        UserProfile.objects.create(user=user)
        self.client = Client()

    def tearDown(self):
        User.objects.all().delete()
        UserProfile.objects.all().delete()

    def _get_content(self, endpoint):
        response = self.client.get(endpoint, follow=True)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _get_csrf_token(self, content):
        CSRF_REGEX = r"""<input type="hidden" name="csrfmiddlewaretoken" value="(?P<token>[A-z0-9]*)">"""
        match = re.search(CSRF_REGEX, content)
        self.assertTrue(match)
        token, *_ = match.groups()
        return token

    def test_present_profile_fields(self):
        ENDPOINT = "/profile/"
        self.client.login(username="user", password="p4ssw0rd1")
        content = self._get_content(ENDPOINT)

        user = User.objects.get(username="user")

        match = re.search(self.FIELDS_REGEX, content)
        self.assertTrue(match)
        username, email = match.groups()
        self.assertEqual(user.username, username)
        self.assertEqual(user.email, email)

    def test_update_profile_fields(self):
        ENDPOINT = "/profile/"
        self.client.login(username="user", password="p4ssw0rd1")
        content = self._get_content(ENDPOINT)

        match = re.search(self.FIELDS_REGEX, content)
        self.assertTrue(match)
        old_username, old_email = match.groups()

        token = self._get_csrf_token(content)

        response = self.client.post(ENDPOINT, {
            "profile_change": "",
            "username": "new_user",
            "email": "new_user@example.com",
            "csrfmiddlewaretoken": token
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="new_user").exists())
        new_user = User.objects.get(username="new_user")
        self.assertNotEqual(new_user.username, old_username)
        self.assertNotEqual(new_user.email, old_email)

    def test_profile_requires_auth(self):
        ENDPOINT = "/profile/"
        self.client.logout()
        response = self.client.get(ENDPOINT)
        self.assertEqual(response.url, "/login/?next=/profile/")

    def test_profile_change_password(self):
        ENDPOINT = "/profile/"
        self.client.login(username="user", password="p4ssw0rd1")
        content = self._get_content(ENDPOINT)

        match = re.search(self.FIELDS_REGEX, content)
        self.assertTrue(match)
        old_username, old_email = match.groups()

        token = self._get_csrf_token(content)

        response = self.client.post(ENDPOINT, {
            "password_change": "",
            "old_password": "p4ssw0rd1",
            "new_password1": "p4ssw0rd1_new",
            "new_password2": "p4ssw0rd1_new",
            "csrfmiddlewaretoken": token
        })
        self.assertEqual(response.status_code, 200)
        User.objects.update(username="user", password=make_password("p4ssw0rd1"))
