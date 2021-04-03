import re
from django.test import TestCase, Client
from mfgd_app.models import Repository

# \s*<a href="([\s\S]+?)">[\s\S]+?</a>\s*

REGEX_DIR_ENTS = re.compile(
r"""\s*<td class="">\s*<a href="([\s\S]+?)">[\s\S]+?</a>\s*</td>
\s*<td class="commit-msg">([\s\S]+?)</td>
\s*<td class="commit-id">\s*<a class="commit" href="\S*">\S*</a>
\s*</td>\s*<td class="commit-date">[\s\S]+?</td>""",
re.MULTILINE)

class TreeTestCase(TestCase):
    def setUp(self):
        Repository.objects.create(name="dirs", path="tests/repo/dirs", isPublic=True)
        self.client = Client()

    def _get_tree(self, repo_name):
        db_repo = Repository.objects.get(name=repo_name)

        response = self.client.get(f"/{repo_name}/view/", follow=True)
        self.assertEquals(response.status_code, 200)
        return response.content.decode()

    def test_dir_contents(self):
        content = self._get_tree("dirs")

        # Entries must appear in this order
        ENTS = ( "dir1", "dir2", "file1", "file2")

        for i, match in enumerate(REGEX_DIR_ENTS.finditer(content)):
            name, last_change = match.groups()
            name = name.rstrip("/")
            self.assertEquals(name, ENTS[i])
            self.assertEquals(last_change, f"add {ENTS[i]}")
