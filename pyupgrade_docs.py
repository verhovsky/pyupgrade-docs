import argparse
import contextlib
import re
import textwrap
import tempfile
from typing import Generator
from typing import List
from typing import Match
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Tuple

import pyupgrade


MD_RE = re.compile(
    r"(?P<before>^(?P<indent> *)```python\n)"
    r"(?P<code>.*?)"
    r"(?P<after>^(?P=indent)```\s*$)",
    re.DOTALL | re.MULTILINE,
)
PY_LANGS = "(python|py|sage|python3|py3|numpy)"
RST_RE = re.compile(
    rf"(?P<before>"
    rf"^(?P<indent> *)\.\. (code|code-block|sourcecode|ipython):: {PY_LANGS}\n"
    rf"((?P=indent) +:.*\n)*"
    rf"\n*"
    rf")"
    rf"(?P<code>(^((?P=indent) +.*)?\n)+)",
    re.MULTILINE,
)
INDENT_RE = re.compile("^ +(?=[^ ])", re.MULTILINE)
TRAILING_NL_RE = re.compile(r"\n+\Z", re.MULTILINE)


class CodeBlockError(NamedTuple):
    offset: int
    exc: Exception


def _format_str(contents_text, args):  # type: (str, argparse.Namespace) -> int
    contents_text = pyupgrade._fix_py2_compatible(contents_text)
    contents_text = pyupgrade._fix_tokens(contents_text, args.py3_plus)
    if not args.keep_percent_format:
        contents_text = pyupgrade._fix_percent_format(contents_text)
    if args.py3_plus:
        contents_text = pyupgrade._fix_py3_plus(contents_text)
    if args.py36_plus:
        contents_text = pyupgrade._fix_fstrings(contents_text)

    return contents_text


def format_str(
    src: str, args: argparse.Namespace
) -> Tuple[str, Sequence[CodeBlockError]]:
    errors: List[CodeBlockError] = []

    @contextlib.contextmanager
    def _collect_error(match: Match[str]) -> Generator[None, None, None]:
        try:
            yield
        except Exception as e:
            errors.append(CodeBlockError(match.start(), e))

    def _md_match(match: Match[str]) -> str:
        code = textwrap.dedent(match["code"])
        with _collect_error(match):
            code = _format_str(code, args=args)
        code = textwrap.indent(code, match["indent"])
        return f'{match["before"]}{code}{match["after"]}'

    def _rst_match(match: Match[str]) -> str:
        min_indent = min(INDENT_RE.findall(match["code"]))
        trailing_ws_match = TRAILING_NL_RE.search(match["code"])
        assert trailing_ws_match
        trailing_ws = trailing_ws_match.group()
        code = textwrap.dedent(match["code"])
        with _collect_error(match):
            code = _format_str(code, args=args)
        code = textwrap.indent(code, min_indent)
        return f'{match["before"]}{code.rstrip()}{trailing_ws}'

    src = MD_RE.sub(_md_match, src)
    src = RST_RE.sub(_rst_match, src)
    return src, errors


def format_file(filename: str, args: argparse.Namespace, skip_errors: bool) -> int:
    with open(filename, encoding="UTF-8") as f:
        contents = f.read()
    new_contents, errors = format_str(contents, args)
    for error in errors:
        lineno = contents[: error.offset].count("\n") + 1
        print(f"{filename}:{lineno}: code block parse error {error.exc}")
    if errors and not skip_errors:
        return 1
    if contents != new_contents:
        print(f"{filename}: Rewriting...")
        with open(filename, "w", encoding="UTF-8") as f:
            f.write(new_contents)
        return 1
    else:
        return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")

    # parser.add_argument('--exit-zero-even-if-changed', action='store_true')
    parser.add_argument("--keep-percent-format", action="store_true")
    parser.add_argument("--py3-plus", "--py3-only", action="store_true")
    parser.add_argument("--py36-plus", action="store_true")

    parser.add_argument("-E", "--skip-errors", action="store_true")
    args = parser.parse_args(argv)

    if args.py36_plus:
        args.py3_plus = True

    retv = 0
    for filename in args.filenames:
        retv |= format_file(filename, args, skip_errors=args.skip_errors)
    return retv


if __name__ == "__main__":
    exit(main())
