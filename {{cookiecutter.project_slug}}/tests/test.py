import {{cookiecutter.package_name}}


# -- Unittest style tests -----------------------------------------------------

# from unittest import TestCase

# class ExampleTests(TestCase):
#     """Example unit tests."""

#     def test_placeholder(self):
#         """Replace with real tests."""
#         self.assertTrue(True)

# -- Pytest functional style tests --------------------------------------------


def test_example():
    """Example pytest functional test."""
    assert {{cookiecutter.package_name}}.__title__ == "{{cookiecutter.project_slug}}"
