import re
from functools import reduce
from datetime import datetime as dt

from mpygit import mpygit, gitutil

from django.test import TestCase, Client

from mfgd_app.models import UserProfile, CanAccess, Repository


class ChainTestCase(TestCase):
    REGEX_CHAIN_ENTS = (
        r"""<tr>\s*"""
        r"""<td class="commit-id">"""
            r"""<a href="/linear/info/(?P<big_hash>[A-z0-9]*)/?">"""
                r"""(?P<short_hash>[A-z0-9]*)"""
            r"""</a>"""
        r"""</td>"""
        r"""\s*<td class="commit-msg">(?P<commit_msg>.*)</td>"""
        r"""\s*<td>(?P<author>.*)</td>"""
        r"""\s*<td class="commit-date">"""
            r"""\s*<time datetime="[0-9-]*">(?P<date>[0-9-]*)</time>"""
        r"""\s*</td>"""
        r"""\s*</tr>"""
    )

    def setUp(self):
        Repository.objects.create(name="simple", path="tests/repo/simple", isPublic=True)
        Repository.objects.create(name="linear", path="tests/repo/linear", isPublic=True)
        Repository.objects.create(name="n_merge", path="tests/repo/n_merge", isPublic=True)

        self.client = Client()

    def _get_chain(self, repo_name):
        db_repo = Repository.objects.get(name=repo_name)
        repo = mpygit.Repository(db_repo.path)

        response = self.client.get(f"/{repo_name}/chain/", follow=True)
        self.assertEquals(response.status_code, 200)
        return response.content.decode()

    def test_displays_commits(self):
        content = self._get_chain("linear")
        repo = mpygit.Repository(Repository.objects.get(name="linear").path)
        repo_walker = gitutil.walk(repo, repo.HEAD, 5)
        for fs_ent, match in zip(repo_walker, re.finditer(self.REGEX_CHAIN_ENTS, content)):
            oid, short_oid, msg, committer, timestamp = match.groups()
            self.assertEqual(fs_ent.oid, oid)
            self.assertEqual(fs_ent.short_oid, short_oid)
            self.assertEqual(fs_ent.message, msg)
            self.assertEqual(fs_ent.committer.name, committer)

            fs_timestamp = dt.utcfromtimestamp(fs_ent.committer.timestamp).strftime("%Y-%m-%d")
            self.assertEqual(fs_timestamp, timestamp)

    def test_correct_ordering(self):
        content = self._get_chain("linear")
        # you can't stop me
        is_sorted, _ = reduce(
            lambda acc, v: (acc[0] and acc[1] >= v, v),
            map(lambda x: x.group(5), re.finditer(self.REGEX_CHAIN_ENTS, content)),
            (True, "9999-99-99"))
        self.assertTrue(is_sorted)

    def test_n_way_merge_flattened(self):
        content = self._get_chain("n_merge")
        order = (5, 6, 4, 3, 2, 1)
        for n, match in zip(order, re.finditer(self.REGEX_CHAIN_ENTS, content)):
            self.assertEqual(f"commit #{n}", match.group(3))

    def test_entries_link_to_info(self):
        # this is ensured by displays_commits because it must match the regex which
        # then checks to see whether the long oid in the anchor tag is associated with
        # the short oid
        pass

    def test_empty_chain(self):
        db_repo = Repository.objects.get(name="simple")
        repo = mpygit.Repository(db_repo.path)

        response = self.client.get("/simple/chain/", follow=True)
        self.assertEquals(response.status_code, 200)
        content = response.content.decode()
        self.assertFalse(re.search(self.REGEX_CHAIN_ENTS, content))

