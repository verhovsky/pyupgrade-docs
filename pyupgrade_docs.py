import argparse
import contextlib
import io
import re
import textwrap
import tempfile
from contextlib import redirect_stderr
from copy import deepcopy
from pathlib import Path
from typing import Generator
from typing import List
from typing import Match
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Tuple

import pyupgrade._main


MD_RE = re.compile(
    r'(?P<before>^(?P<indent> *)```\s*python\n)'
    r'(?P<code>.*?)'
    r'(?P<after>^(?P=indent)```\s*$)',
    re.DOTALL | re.MULTILINE,
)
PY_LANGS = '(python|py|sage|python3|py3|numpy)'
BLOCK_TYPES = '(code|code-block|sourcecode|ipython)'
RST_RE = re.compile(
    rf'(?P<before>'
    rf'^(?P<indent> *)\.\. (jupyter-execute::|{BLOCK_TYPES}:: {PY_LANGS})\n'
    rf'((?P=indent) +:.*\n)*'
    rf'\n*'
    rf')'
    rf'(?P<code>(^((?P=indent) +.*)?\n)+)',
    re.MULTILINE,
)
RST_PYCON_RE = re.compile(
    r'(?P<before>'
    r'(?P<indent> *)\.\. (code|code-block):: pycon\n'
    r'((?P=indent) +:.*\n)*'
    r'\n*'
    r')'
    r'(?P<code>(^((?P=indent) +.*)?(\n|$))+)',
    re.MULTILINE,
)
PYCON_PREFIX = '>>> '
PYCON_CONTINUATION_PREFIX = '...'
PYCON_CONTINUATION_RE = re.compile(
    rf'^{re.escape(PYCON_CONTINUATION_PREFIX)}( |$)',
)
LATEX_RE = re.compile(
    r'(?P<before>^(?P<indent> *)\\begin{minted}{python}\n)'
    r'(?P<code>.*?)'
    r'(?P<after>^(?P=indent)\\end{minted}\s*$)',
    re.DOTALL | re.MULTILINE,
)
PYTHONTEX_LANG = r'(?P<lang>pyblock|pycode|pyconsole|pyverbatim)'
PYTHONTEX_RE = re.compile(
    rf'(?P<before>^(?P<indent> *)\\begin{{{PYTHONTEX_LANG}}}\n)'
    rf'(?P<code>.*?)'
    rf'(?P<after>^(?P=indent)\\end{{(?P=lang)}}\s*$)',
    re.DOTALL | re.MULTILINE,
)
INDENT_RE = re.compile('^ +(?=[^ ])', re.MULTILINE)
TRAILING_NL_RE = re.compile(r'\n+\Z', re.MULTILINE)


class CodeBlockError(NamedTuple):
    offset: int
    exc: Exception


def _format_str(contents_text: str, args: argparse.Namespace) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpfile = Path(tmpdir) / "pyupgrade_docs_cache"
        with open(tmpfile, "w") as f:
            f.write(contents_text)

        new_args = deepcopy(args)
        new_args.filenames = [tmpfile]  # Just to be safe
        with io.StringIO() as f:
            with redirect_stderr(f):
                pyupgrade._main._fix_file(tmpfile, new_args)

        with open(tmpfile) as f:
            return f.read()


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
        code = textwrap.dedent(match['code'])
        with _collect_error(match):
            code = _format_str(code, args=args)
        code = textwrap.indent(code, match['indent'])
        return f'{match["before"]}{code}{match["after"]}'

    def _rst_match(match: Match[str]) -> str:
        min_indent = min(INDENT_RE.findall(match['code']))
        trailing_ws_match = TRAILING_NL_RE.search(match['code'])
        assert trailing_ws_match
        trailing_ws = trailing_ws_match.group()
        code = textwrap.dedent(match['code'])
        with _collect_error(match):
            code = _format_str(code, args=args)
        code = textwrap.indent(code, min_indent)
        return f'{match["before"]}{code.rstrip()}{trailing_ws}'

    def _rst_pycon_match(match: Match[str]) -> str:
        code = ''
        fragment = None

        def finish_fragment() -> None:
            nonlocal code
            nonlocal fragment

            if fragment is not None:
                with _collect_error(match):
                    fragment = _format_str(fragment, args=args)
                fragment_lines = fragment.splitlines()
                code += f'{PYCON_PREFIX}{fragment_lines[0]}\n'
                for line in fragment_lines[1:]:
                    if line:
                        code += f'{PYCON_CONTINUATION_PREFIX} {line}\n'
                    else:
                        code += f'{PYCON_CONTINUATION_PREFIX}\n'
                fragment = None

        indentation = None
        for line in match['code'].splitlines():
            orig_line, line = line, line.lstrip()
            if indentation is None and line:
                indentation = len(orig_line) - len(line)
            continuation_match = PYCON_CONTINUATION_RE.match(line)
            if continuation_match and fragment is not None:
                fragment += line[continuation_match.end():] + '\n'
            else:
                finish_fragment()
                if line.startswith(PYCON_PREFIX):
                    fragment = line[len(PYCON_PREFIX):] + '\n'
                else:
                    code += orig_line[indentation:] + '\n'
        finish_fragment()

        min_indent = min(INDENT_RE.findall(match['code']))
        code = textwrap.indent(code, min_indent)
        return f'{match["before"]}{code}'

    def _latex_match(match: Match[str]) -> str:
        code = textwrap.dedent(match['code'])
        with _collect_error(match):
            code = _format_str(code, args=args)
        code = textwrap.indent(code, match['indent'])
        return f'{match["before"]}{code}{match["after"]}'

    src = MD_RE.sub(_md_match, src)
    src = RST_RE.sub(_rst_match, src)
    src = RST_PYCON_RE.sub(_rst_pycon_match, src)
    src = LATEX_RE.sub(_latex_match, src)
    src = PYTHONTEX_RE.sub(_latex_match, src)
    return src, errors


def format_file(
        filename: str, args: argparse.Namespace, skip_errors: bool
) -> int:
    with open(filename, encoding='UTF-8') as f:
        contents = f.read()
    new_contents, errors = format_str(contents, args)
    for error in errors:
        lineno = contents[:error.offset].count('\n') + 1
        print(f'{filename}:{lineno}: code block parse error {error.exc}')
    if errors and not skip_errors:
        return 1
    if contents != new_contents:
        print(f'{filename}: Rewriting...')
        with open(filename, 'w', encoding='UTF-8') as f:
            f.write(new_contents)
        return 1
    else:
        return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--exit-zero-even-if-changed', action='store_true')
    parser.add_argument('--keep-percent-format', action='store_true')
    parser.add_argument('--keep-mock', action='store_true')
    parser.add_argument('--keep-runtime-typing', action='store_true')
    parser.add_argument(
        '--py3-plus', '--py3-only',
        action='store_const', dest='min_version', default=(2, 7), const=(3,),
    )
    parser.add_argument(
        '--py36-plus',
        action='store_const', dest='min_version', const=(3, 6),
    )
    parser.add_argument(
        '--py37-plus',
        action='store_const', dest='min_version', const=(3, 7),
    )
    parser.add_argument(
        '--py38-plus',
        action='store_const', dest='min_version', const=(3, 8),
    )
    parser.add_argument(
        '--py39-plus',
        action='store_const', dest='min_version', const=(3, 9),
    )
    parser.add_argument(
        '--py310-plus',
        action='store_const', dest='min_version', const=(3, 10),
    )

    parser.add_argument('-E', '--skip-errors', action='store_true')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    retv = 0
    for filename in args.filenames:
        retv |= format_file(filename, args, skip_errors=args.skip_errors)
    return retv


if __name__ == '__main__':
    exit(main())
