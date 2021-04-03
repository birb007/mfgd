import json
import uuid
import re

from mpygit import mpygit

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from mfgd_app.models import UserProfile, CanAccess, Repository


class PermissionTestCase(TestCase):
    def setUp(self):
        passwd = make_password("")
        # create users
        admin = User.objects.create(username="admin", password=passwd)
        manager = User.objects.create(username="manager", password=passwd)
        viewer = User.objects.create(username="viewer", password=passwd)
        regular = User.objects.create(username="regular", password=passwd)

        # create repository object
        linear = Repository.objects.create(name="linear", path="tests/repo/linear", isPublic=False)

        # create profiles
        UserProfile.objects.create(user=admin, isAdmin=True)
        UserProfile.objects.create(user=manager)
        UserProfile.objects.create(user=viewer)
        UserProfile.objects.create(user=regular)

        # setup permissions
        CanAccess.objects.create(user=manager.userprofile, repo=linear, canManage=True)
        CanAccess.objects.create(user=viewer.userprofile, repo=linear)

        # create django test client
        self.client = Client()

    def tearDown(self):
        # flush database entries
        User.objects.all().delete()
        UserProfile.objects.all().delete()
        CanAccess.objects.all().delete()
        Repository.objects.all().delete()

    def test_permitted_users_can_manage_repo(self):
        ENDPOINT = "/linear/manage/"

        users = [
            ("admin", 200), ("manager", 200),
            ("viewer", 404), ("regular", 404),
        ]

        for username, status in users:
            self.client.login(username=username, password="")
            response = self.client.get(ENDPOINT, follow=True)
            self.assertEqual(response.status_code, status,
                f"user \"{username}\" had unexpected management access")

        self.client.logout()
        response = self.client.get(ENDPOINT, follow=True)
        self.assertEqual(response.status_code, 404,
                f"user \"{username}\" had unexpected management access")

    def test_permitted_users_can_view_repo(self):
        ENDPOINT = "/linear/view/"

        users = [
            ("admin", 200), ("manager", 200),
            ("viewer", 200), ("regular", 404),
        ]

        for username, status in users:
            self.client.login(username=username, password="")
            response = self.client.get(ENDPOINT, follow=True)
            self.assertEqual(response.status_code, status,
                f"user \"{username}\" had unexpected viewing access")

        self.client.logout()
        response = self.client.get(ENDPOINT, follow=True)
        self.assertEqual(response.status_code, 404,
                "anonymous user had unexpected viewing access")

    def test_dashboard_indexes_visible_repo(self):
        ENDPOINT = "/"
        REPO_LINK = r"""<a href="/linear/view/\w*">linear</a>"""

        users = [
            ("admin", True), ("manager", True),
            ("viewer", True), ("regular", False),
        ]

        for username, present in users:
            self.client.login(username=username, password="")
            response = self.client.get(ENDPOINT)
            self.assertEqual(bool(re.search(REPO_LINK, response.content.decode())), present)

        self.client.logout()
        response = self.client.get(ENDPOINT)
        self.assertEqual(bool(re.search(REPO_LINK, response.content.decode())), False)

    def test_cannot_modify_admin_perms(self):
        ENDPOINT = "/linear/manage/"

        self.client.login(username="manager", password="")
        admin = UserProfile.objects.get(user__username="admin")

        payload = {"action": "update_perm", "id": f"{admin.id}", "visible": True, "manage": False}
        response = self.client.post(ENDPOINT, json.dumps(payload),
                content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_cannot_modify_own_perms(self):
        ENDPOINT = "/linear/manage/"

        self.client.login(username="manager", password="")
        manager = UserProfile.objects.get(user__username="manager")

        payload = {"action": "update_perm", "id": f"{manager.id}", "visible": True, "manage": False}
        response = self.client.post(ENDPOINT, json.dumps(payload),
                content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_can_modify_perms(self):
        ENDPOINT = "/linear/manage/"

        self.client.login(username="manager", password="")
        regular = UserProfile.objects.get(user__username="regular")

        payload = {"action": "update_perm", "id": f"{regular.id}", "visible": True, "manage": False}
        response = self.client.post(ENDPOINT, json.dumps(payload),
                content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CanAccess.objects.filter(user=regular).exists())

    def test_can_inspect(self):
        users = [
            ("admin", 200), ("manager", 200),
            ("viewer", 200), ("regular", 404),
        ]

        linear = mpygit.Repository(Repository.objects.get(name="linear").path)
        ENDPOINT = f"/linear/info/{linear.HEAD}/file"

        for username, status in users:
            self.client.login(username=username, password="")
            response = self.client.get(ENDPOINT)
            self.assertEqual(response.status_code, status,
                f"user \"{username}\" has unexpected commit visibility")

        self.client.logout()
        response = self.client.get(ENDPOINT)
        self.assertEqual(response.status_code, 404)

    def test_can_view_commits(self):
        users = [
            ("admin", 200), ("manager", 200),
            ("viewer", 200), ("regular", 404),
        ]

        ENDPOINT = f"/linear/chain/"

        for username, status in users:
            self.client.login(username=username, password="")
            response = self.client.get(ENDPOINT, follow=True)
            self.assertEqual(response.status_code, status,
                f"user \"{username}\" has unexpected chain visibility")

        self.client.logout()
        response = self.client.get(ENDPOINT, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_superadmin_management_panel(self):
        ENDPOINT = "/manage"

        for user in User.objects.all():
            self.client.login(username=user.username, password="")
            response = self.client.get(ENDPOINT, follow=True)
            self.assertEqual(response.request["PATH_INFO"], "/")

        self.client.logout()
        response = self.client.get(ENDPOINT, follow=True)
        self.assertEqual(response.request["PATH_INFO"], "/")

