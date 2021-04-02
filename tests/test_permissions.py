import uuid
import json

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
        repo = Repository.objects.create(name="repo", path="tests/repo/simple", isPublic=False)

        # create profiles
        UserProfile.objects.create(user=admin, isAdmin=True)
        UserProfile.objects.create(user=manager)
        UserProfile.objects.create(user=viewer)
        UserProfile.objects.create(user=regular)

        # setup permissions
        CanAccess.objects.create(user=manager.userprofile, repo=repo, canManage=True)
        CanAccess.objects.create(user=viewer.userprofile, repo=repo)

        # create django test client
        self.client = Client()

    def tearDown(self):
        # flush database entries
        User.objects.all().delete()
        UserProfile.objects.all().delete()
        CanAccess.objects.all().delete()
        Repository.objects.all().delete()

    def test_permitted_users_can_manage_repo(self):
        users = [
            ("admin", 200), ("manager", 200),
            ("viewer", 404), ("regular", 404),
        ]

        for username, status in users:
            self.client.login(username=username, password="")
            response = self.client.get("/repo/manage", follow=True)
            self.assertEqual(response.status_code, status,
                f"user \"{username}\" had unexpected management access")

        self.client.logout()
        response = self.client.get("/repo/manage", follow=True)
        self.assertEqual(response.status_code, 404,
                f"user \"{username}\" had unexpected management access")

    def test_permitted_users_can_view_repo(self):
        users = [
            ("admin", 200), ("manager", 200),
            ("viewer", 200), ("regular", 404),
        ]

        for username, status in users:
            self.client.login(username=username, password="")
            response = self.client.get("/repo/view/main", follow=True)
            self.assertEqual(response.status_code, status,
                f"user \"{username}\" had unexpected viewing access")

        self.client.logout()
        response = self.client.get("/repo/view/main", follow=True)
        self.assertEqual(response.status_code, 404,
                "anonymous user had unexpected viewing access")

    def test_dashboard_indexes_visible_repo(self):
        URL = "<a href=\"/repo/view/main\">repo</a>"
        users = [
            ("admin", True), ("manager", True),
            ("viewer", True), ("regular", False),
        ]

        for username, present in users:
            self.client.login(username=username, password="")
            response = self.client.get("/")
            self.assertEqual(URL in response.content.decode(), present)

        self.client.logout()
        response = self.client.get("/")
        self.assertEqual(URL in response.content.decode(), False)

    def test_cannot_modify_admin_perms(self):
        self.client.login(username="manager", password="")
        admin = UserProfile.objects.get(user__username="admin")

        payload = {"action": "update_perm", "id": f"{admin.id}", "visible": True, "manage": False}
        response = self.client.post("/repo/manage/", json.dumps(payload),
                content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_cannot_modify_own_perms(self):
        self.client.login(username="manager", password="")
        manager = UserProfile.objects.get(user__username="manager")

        payload = {"action": "update_perm", "id": f"{manager.id}", "visible": True, "manage": False}
        response = self.client.post("/repo/manage/", json.dumps(payload),
                content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_can_modify_perms(self):
        self.client.login(username="manager", password="")
        regular = UserProfile.objects.get(user__username="regular")

        payload = {"action": "update_perm", "id": f"{regular.id}", "visible": True, "manage": False}
        response = self.client.post("/repo/manage/", json.dumps(payload),
                content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CanAccess.objects.filter(user=regular).exists())

