# Reboot Worker Dashboard Demo

## Setup

You can run Reboot on any modern Linux or MacOS machine, or on Windows via [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).

This repository manages its Python installation with [Rye](https://github.com/astral-sh/rye). To install Rye:

```
curl -sSf https://rye.astral.sh/get | bash
```

Set up your Python virtual environment:

```sh
rye sync --no-lock
source ./.venv/bin/activate
```

## Run

In one terminal, run the backend:

```sh
rbt dev run
```

In another terminal, run the frontend:

```sh
cd web/
npm install
npm start
```

## Tests

The application comes with backend tests.

Before you run the tests, you'll need to ensure you've generated your client and server libraries:

```sh
rbt protoc
```

Now you can run the tests using `pytest`:

```sh
pytest backend/
```
