# Build [note to myself]

Everything runs from the virtual environment in `.venv`; `build.bat` refuses to run without it.

## Set up the virtual environment

Allow activating a venv (once per machine):

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Create it and install the package with the build and test tooling:

```
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e . build twine lecore
```

`lecore` is only needed by the hardware tests and is deliberately not in `pyproject.toml`.

## Run the tests

```
.venv\Scripts\python -m unittest tests.TestDbMySql        # standalone, no device or database
.venv\Scripts\python -m unittest tests.TestCommunication  # needs a real VMS device
```

## Build and publish

```
build.bat
```

It wipes `dist/` and `Log/`, builds the sdist and wheel with the interpreter from `.venv`, and
then uploads to PyPI. The upload is the last step and is **not** confirmed, so running the
script publishes the version in `pyproject.toml`. A failed build aborts before the upload.

To build without publishing, or to publish something already built:

```
.venv\Scripts\python -m build
.venv\Scripts\python -m twine upload dist/*
```

Twine asks for credentials unless an API token is stored in `%USERPROFILE%\.pypirc`.
