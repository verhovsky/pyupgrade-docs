<!-- TODO: [![Build Status](https://travis-ci.org/asottile/blacken-docs.svg?branch=master)](https://travis-ci.org/asottile/blacken-docs)
[![Coverage Status](https://coveralls.io/repos/github/asottile/blacken-docs/badge.svg?branch=master)](https://coveralls.io/github/asottile/blacken-docs?branch=master) -->

pyupgrade-docs
============

Run `pyupgrade` on python code blocks in documentation files.

## install

`pip install pyupgrade-docs`

## usage

`pyupgrade-docs` provides a single executable (`pyupgrade-docs`) which will modify
`.rst` / `.md` files in place.

It currently supports the following [`pyupgrade`](https://github.com/asottile/pyupgrade)
options:

- `--keep-percent-format`
- `--py3-plus` `--py3-only`
- `--py36-plus`

Following additional parameters can be used:

 - `-E` / `--skip-errors`

`pyupgrade-docs` will format code in the following block types:

(markdown)
```markdown
    ```python
    def hello():
        print("hello world")
    ```
```

(rst)
```rst
    .. code-block:: python

        def hello():
            print("hello world")
```

## usage with pre-commit

See [pre-commit](https://pre-commit.com) for instructions

Sample `.pre-commit-config.yaml`:


```yaml
-   repo: https://github.com/verhovsky/pyupgrade-docs
    rev: v0.1.0
    hooks:
    -   id: pyupgrade-docs
```
