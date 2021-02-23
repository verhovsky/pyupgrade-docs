pyupgrade-docs
============

Run `pyupgrade` on python code blocks in documentation files.

## install

`pip install pyupgrade-docs`

## usage

`pyupgrade-docs` provides a single executable (`pyupgrade-docs`) which will modify
`.rst` / `.md` / `.tex` files in place.

It currently supports the following [`pyupgrade`](https://github.com/asottile/pyupgrade)
options:


The following additional parameters can be used:

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

(rst `pycon`)
```rst
    .. code-block:: pycon

        >>> def hello():
        ...     print("hello world")
        ...
```

(latex)
```latex
\begin{minted}{python}
def hello():
    print("hello world")
\end{minted}
```

(latex with pythontex)
```latex
\begin{pycode}
def hello():
    print("hello world")
\end{pycode}
```

(markdown/rst in python docstrings)
```python
def f():
    """docstring here

    .. code-block:: python

        print("hello world")

    ```python
    print("hello world")
    ```
    """
```

## usage with pre-commit

See [pre-commit](https://pre-commit.com) for instructions

Sample `.pre-commit-config.yaml`:


```yaml
-   repo: https://github.com/verhovsky/pyupgrade-docs
    rev: v0.2.0
    hooks:
        additional_dependencies: [pyupgrade==...]
    -   id: pyupgrade-docs
```

Since `pyupgrade` is currently a moving target, it is suggested to pin `pyupgrade`
to a specific version using `additional_dependencies`.
