# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`pyvms` is a Python client library for Logic Elements' Vibration Monitoring System (VMS-1201) hardware. It implements the VMS wire protocol (TCP config/telemetry sockets, UDP discovery), plus a MySQL-backed test-and-monitoring layer used to watch deployed VMS installations and report health metrics to Zabbix.

The package lives under `src/pyvms` (src-layout) and is published to PyPI as `pyvms`.

## Commands

Install for local development (editable):
```
pip install -e .
pip install -e .[extra]   # adds matplotlib, needed for tests/TestCommon.py plotting
```

Run tests (unittest-based, not pytest):
```
python -m unittest tests.TestCommunication
python -m unittest tests.TestCommunication.TestCommunication.test001_get_fe_cards   # single test
```
Note: `tests/` requires a real VMS device on the network (the test process opens listening TCP sockets on ports 30000/30001 and waits for the device to connect — see "Testing" below) and an internal `lecore` package that is not declared in `pyproject.toml`. These tests cannot run standalone/headless.

Build and publish package (see `how_to_build.md`, `build.bat`):
```
py -m build                 # produces dist/*.whl and dist/*.tar.gz
py -m twine upload dist/*   # publish to PyPI
```
`build.bat` wraps this: it deletes `dist/` and `Log/`, builds, then uploads.

## Architecture

The codebase has two mostly-independent halves living in the same package: the **VMS communication protocol** (the published library's main purpose) and a **Zabbix monitoring agent** (an in-progress Windows service, not yet wired into `pyvms/__init__.py` or `pyproject.toml` dependencies).

### VMS communication protocol (`Protocol.py`, `ConfigSocket.py`, `TimeSocket.py`, `Regs.py`, `TimeStats.py`, `Discovery.py`, `Crc32.py`)

The device exposes two independent TCP connections plus a UDP discovery protocol, all defined by the same custom binary framing in `Protocol.py`: a 6-byte `"LEBVMS"` header, a 4-byte serial number, a 1-byte packet-type ID, a 1-byte sequence ID, a 4-byte length, then payload. `Protocol` is a shared, stateful helper (not a socket itself) used by both socket classes to build outgoing packets and parse incoming ones.

- **ConfigSocket** (default port 50001): request/response style. The device connects to us (`listen()` blocks until it does); every call sends a packet and blocks on `_request_response` until a full reply is parsed. Used for reading/writing registers on three distinct targets — MCU (`Mcu`/`VmsRegsMcu`), Master FPGA (`Master`/`VmsRegsMaster`), and per-channel Frontend FPGA cards (`Fe`/`VmsRegsFe`, addressed 1–16) — and for firmware updates (`update_firmware`: `Protocol.load_firmware` validates a magic header per target and bit-reverses FPGA images, then `start_flash`/`flash_page` streams the file in 1KB pages, CRC-checked via `Crc32.calc_from_byte`).
- **TimeSocket** (default port 50000): continuous streaming, not request/response. `receive_loop()` runs for a fixed duration, reassembling packets from a rolling buffer and handing each to `Protocol.parse_timestamp`, which routes to either per-revolution timestamp data or raw logger (waveform) data and forwards it into a `TimeStats` accumulator.
- **TimeStats** accumulates phase-marker/blade-count statistics from timestamp packets, and separately assembles streamed logger samples into a 2D numpy buffer (`image`/`buffer`) that visualization code (see `tests/TestCommon.py`) renders as a live image via matplotlib.
- **Regs.py** is purely address maps (`VmsRegsMcu`, `VmsRegsMaster`, `VmsRegsFe`) — these constants are the `address` arguments passed into `ConfigSocket.read_*`/`write_*`; there's no logic here, just the register layout contract with the firmware.
- **Discovery.py** is a separate, self-contained UDP broadcast protocol (distinct from the TCP protocol above — different packet format, default port 4455) for finding VMS devices on the local network and reconfiguring their server IP / socket ports before the TCP protocol can be used. It also exposes a CLI (`discovery_main`, uses `argparse`) for standalone use.

### Zabbix monitoring agent (`ZabAgent.py`, `ZabConfig.py`, `ZabSender.py`, `DbMySql.py`)

This is a separate subsystem that watches a MySQL database (`BVMS`) which VMS server software writes into, and forwards derived health metrics to Zabbix. It is unfinished/experimental relative to the rest of the package:
- It uses plain module-level imports (`from DbMySql import *`, `import ZabConfig as Cfg`) rather than the relative imports (`from .Protocol import Protocol`) used everywhere else, so `ZabAgent.py` is meant to be run as a script from inside `src/pyvms/`, not imported through the `pyvms` package.
- Its dependencies — `pywin32` (`win32serviceutil`, `win32service`, `servicemanager`), `jsonpickle`, `zabbix_utils` — are not declared in `pyproject.toml`.
- `ZabAgent.ZabAgentFrame` is a `pywin32` Windows Service (name `ZabAgent`) wrapping `ZabAgent` (the actual polling loop); running the file directly with no args runs the same loop as a plain foreground script instead of installing/starting the service.
- Flow: `ZabConfig.Config` (a plain object graph of MySQL/Zabbix connection info plus a list of monitored `Generator`s, each pinned to a `system_id` and pair of buffer table names) round-trips to JSON via `jsonpickle` at `src/pyvms/data/config_default.json`. On each poll cycle, `DbMysql` (wraps `mysql.connector`) reads the `info_le` row and `buffer_le*` table row-counts/update-times for each configured generator, `ZabSender.ZabItems` packages the derived metrics (speed, buffer/config/timestamp ages, buffer bulk sizes), and `ZabSender.send()` pushes them to Zabbix as trapper items (`vms.speed`, `vms.buf_rows_1`, etc.) via `zabbix_utils.Sender`.
- `DbMysql` also has standalone test-harness methods unrelated to the agent (`speed_check`, `plot_events`) used for closed-loop VMS testing by reading back what the VMS server wrote to `buffer_le`.

## Testing notes

- Tests use `unittest`, with shared fixtures via multiple inheritance rather than `unittest.TestCase` subclassing alone: `class TestCommunication(unittest.TestCase, TestCommon)`, where `TestCommon` supplies `class_setup`/`common_setup`/etc. and helper methods (`measure_time`, `get_logger`) built on `ConfigSocket`/`TimeSocket`/`TimeStats`.
- Tests are hardware-in-the-loop: `TestCommon.class_setup` opens `ConfigSocket`/`TimeSocket` listeners and blocks waiting for a physical VMS device to dial in; there is no mock/simulated device.
- `tests/TestCommunication.py` depends on `lecore.TestFrame`, an internal Logic Elements package not published alongside `pyvms`.
