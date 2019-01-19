import unittest
import pytest

from sphinx_testing import with_app


class PyTestAndDocs(unittest.TestCase):
    def test_pytest(self):
        self.assertEqual(main(), 0)

    @with_app(buildername='html', srcdir='docs', warningiserror=True)
    def test_sphinx_build(self, app, status, warning):
        app.build()


def main():
    return pytest.main([
        "-v", "--pylint", "--pylint-error-types=EF", "--mypy",
        "--doctest-modules", "--doctest-continue-on-failure",
        "--doctest-plus", "--doctest-rst"])
