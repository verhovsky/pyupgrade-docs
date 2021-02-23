import argparse
import pyupgrade_docs
import pytest


@pytest.fixture
def args():
    return argparse.Namespace(
        filenames="",
        # exit_zero_even_if_changed = False,
        keep_percent_format=False,
        min_version=(3, 7),
        skip_errors=True,
    )


def test_format_src_markdown_simple(tmp_path):
    before = "```python\nclass MyClass(object):\n    pass\n```\n"
    temp_file = tmp_path / "some_file.md"
    print(repr(temp_file))
    with open(temp_file, "w") as f:
        f.write(before)
    return_code = pyupgrade_docs.main(["--py37-plus", str(temp_file)])
    with open(temp_file) as f:
        after = f.read()
    # assert return_code == 0
    assert after == "```python\nclass MyClass:\n    pass\n```\n"
