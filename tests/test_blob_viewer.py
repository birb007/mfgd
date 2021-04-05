import re

from mpygit import mpygit, gitutil

from django.test import TestCase, Client

from mfgd_app.models import Repository
from mfgd_app.utils import resolve_path

class BlobViewerTestCase(TestCase):
    def setUp(self):
        Repository.objects.create(name="files", path="tests/repo/files", isPublic=True)
        self.client = Client()

    def tearDown(self):
        Repository.objects.all().delete()

    def _get_content(self, endpoint):
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_displays_textual_contents(self):
        ENDPOINT = "/files/view/master/multi_line_textual_file"
        content = self._get_content(ENDPOINT)

        files = mpygit.Repository(Repository.objects.get(name="files").path)
        commit = [c for c in gitutil.walk(files, files.HEAD, 2)][-1]
        fs_blob = resolve_path(files, commit.tree, "multi_line_textual_file")

        # validate contents
        HIGHLIGHT_REGEX = (
            r"""<div class="blob_box blob_code">"""
                r"""\s*<table class="highlighttable">"""
                    r"""\s*<tr>"""
                        r"""\s*<td class="linenos">"""
                            r"""\s*<div class="linenodiv">"""
                                r"""\s*<pre>"""
                                    r"""\s*<span class="normal">1</span>"""
                                    r"""\s*<span class="normal">2</span>"""
                                    r"""\s*<span class="normal">3</span>"""
                                r"""\s*</pre>"""
                            r"""\s*</div>"""
                        r"""\s*</td>"""
                        r"""\s*<td class="code">"""
                            r"""\s*<div class="highlight">"""
                                r"""\s*<pre>"""
                                    r"""\s*<span></span>multi\n"""
                                    r"""line\n"""
                                    r"""file\n"""
                                r"""\s*</pre>"""
                            r"""\s*</div>"""
                        r"""\s*</td>"""
                    r"""\s*</tr>"""
                r"""\s*</table>"""
            r"""\s*</div>"""
        )
        self.assertTrue(re.search(HIGHLIGHT_REGEX, content))

    def test_displays_commit_info(self):
        ENDPOINT = "/files/view/master/multi_line_textual_file"
        content = self._get_content(ENDPOINT)

        files = mpygit.Repository(Repository.objects.get(name="files").path)
        commit = [c for c in gitutil.walk(files, files.HEAD, 2)][-1]

        # validate author info
        # if the message and OIDs match then the author info will match similarly
        # otherwise the commit info page would fail (same backend logic)
        COMMIT_ANCHOR_REGEX = (
            r"""<table class="blob_box">"""
                r"""\s*<tr>"""
                    r"""\s*<td>"""
                        f"""{commit.message}"""
                        f"""\\s*\\[<a href="/files/info/{commit.oid}">{commit.short_oid}</a>\\]"""
                    r"""\s*</td>"""
                r"""\s*</tr>"""
            r"""[\s\S]*</table>"""
        )
        self.assertTrue(re.search(COMMIT_ANCHOR_REGEX, content))

    def test_displays_binary_contents(self):
        ENDPOINT = "/files/view/master/small_binary_file"
        content = self._get_content(ENDPOINT)

        files = mpygit.Repository(Repository.objects.get(name="files").path)
        commit = [c for c in gitutil.walk(files, files.HEAD, 2)][-2]
        fs_blob = resolve_path(files, commit.tree, "multi_line_textual_file")

        HEXDUMP_REGEX = (
            r"""<div class="blob_box">"""
                r"""\s*<table id="hex-dump">"""
                    r"""\s*<tr>"""
                        r"""\s*<td>00000000</td>"""
                        r"""\s*<td>89 50 4e 47 0d 0a 1a 0a</td>"""
                        r"""\s*<td>00 00 00 0d 49 48 44 52</td>"""
                        r"""\s*<td>.PNG........IHDR</td>"""
                    r"""\s*</tr>"""
            r"""\s*</table>"""
            r"""\s*</div>"""
        )
        self.assertTrue(re.search(HEXDUMP_REGEX, content))
