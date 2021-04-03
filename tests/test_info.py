import re
from datetime import datetime as dt

from mpygit import mpygit, gitutil

from django.test import TestCase, Client

from mfgd_app.models import Repository


class InfoTestCase(TestCase):
    def setUp(self):
        Repository.objects.create(name="linear", path="tests/repo/linear", isPublic=True)
        self.client = Client()

    def tearDown(self):
        Repository.objects.all().delete()

    def test_correct_committer_info(self):
        linear = mpygit.Repository(Repository.objects.get(name="linear").path)
        commit = next(gitutil.walk(linear, linear.HEAD, 1))

        ENDPOINT = f"/linear/info/{commit.oid}"

        response = self.client.get(ENDPOINT)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        DIFF_REGEX = (
            r"""<tr>\s*"""
                r"""<td>M</td>\s*"""
                r"""<td>\+\+1</td>\s*"""
                r"""<td>--1</td>\s*"""
                f"""<td><a href="/linear/view/{commit.oid}/file">file</a></td>"""
            r"""\s*</tr>"""
        )
        self.assertTrue(re.search(DIFF_REGEX, content))

        COMMITTER_REGEX = (
            r"""<table class="commit_info">"""
                r"""\s*<tr>"""
                    r"""\s*<td>From:</td>"""
                    r"""\s*<td>(?P<commiter_info>.*)</td>"""
                r"""\s*</tr>"""
                r"""\s*<tr>"""
                    r"""\s*<td>Date:</td>"""
                    r"""\s*<td>"""
                        r"""\s*<time [\s\S]*>(?P<date>.*)</time>"""
                    r"""\s*</td>"""
                r"""\s*</tr>"""
                r"""\s*<tr>"""
                    r"""\s*<td class="commit_msg"[\s\S]*>"""
                        r"""\s*<pre>(?P<msg>.*)</pre>"""
                    r"""\s*</td>"""
                r"""\s*</tr>"""
            r"""\s*</table>"""
        )

        match = re.search(COMMITTER_REGEX, content)
        self.assertTrue(match)

        committer_info, timestamp, msg = match.groups()
        name, email = committer_info.rsplit(" ", 1)
        email = email.removeprefix("&lt;").removesuffix("&gt;")

        self.assertEqual(commit.committer.name, name)
        self.assertEqual(commit.committer.email, email)
        self.assertEqual(commit.message, msg)
        fs_timestamp = dt.utcfromtimestamp(commit.committer.timestamp).strftime("%Y-%m-%d %H:%M")
        self.assertEqual(fs_timestamp, timestamp)

    def test_has_diff(self):
        linear = mpygit.Repository(Repository.objects.get(name="linear").path)
        commit = next(gitutil.walk(linear, linear.HEAD, 1))

        ENDPOINT = f"/linear/info/{commit.oid}"

        response = self.client.get(ENDPOINT)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # this took far longer than i'm willing to admit
        DIFF_REGEX = (
            r"""<table class="highlighttable">"""
                r"""\s*<tr>"""
                    r"""\s*<td class="linenos">"""
                        r"""[\s\S]*"""
                    r"""</td>"""
                    r"""<td class="code">"""
                        r"""\s*<div class="highlight">"""
                            r"""\s*<pre>[\s\S]*"""
                                r"""\s*<span class="gd">\-\-\- a/file</span>"""
                                r"""\s*<span class="gi">\+\+\+ b/file</span>"""
                                r"""\s*<span class="gu">@@ -1,4 \+1,4 @@</span>"""
                                r"""\s*<span class="gd">-#4</span>"""
                                r"""\s*<span class="gi">\+#5</span>"""
                                """\n multi"""
                                """\n line"""
                                """\n file"""
                                """\n"""
                            r"""</pre>"""
                        r"""\s*</div>"""
                    r"""\s*</td>"""
                r"""\s*</tr>"""
            r"""\s*</table>"""
        )
        self.assertTrue(re.search(DIFF_REGEX, content))

    def test_inspect_tree_at_commit(self):
        linear = mpygit.Repository(Repository.objects.get(name="linear").path)
        commit = next(gitutil.walk(linear, linear.HEAD, 1))

        ENDPOINT = f"/linear/info/{commit.oid}"

        response = self.client.get(ENDPOINT)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        ANCHOR_REGEX = (
            r"""<a class="commit_inspect" [\s\S]*"""
                f"""href="/linear/view/{commit.oid}/">"""
                r"""Inspect Tree"""
            r"""\s*</a>"""
        )
        self.assertTrue(re.search(ANCHOR_REGEX, content))

    def test_invalid_commit(self):
        ENDPOINT = f"/linear/info/$nva;i_d"

        response = self.client.get(ENDPOINT)
        self.assertTrue(response.status_code, 404)
