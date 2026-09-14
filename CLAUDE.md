# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`pyvms` is a Python client library for Logic Elements' Vibration Monitoring System (VMS-1201) hardware. It implements the VMS wire protocol (TCP config/telemetry sockets, UDP discovery), plus a MySQL read-back helper (`DbMySql.py`) used for closed-loop testing and as the database layer for the separate [`vms-zabbix-agent`](https://github.com/LogicElements/py-vms-zabbix) monitoring package.

The package lives under `src/pyvms` (src-layout) and is published to PyPI as `pyvms`.

## Commands

Install for local development (editable):
```
pip uninstall -y mysql-connector   # the obsolete package, it shares the mysql.connector namespace
pip install -e .
pip install -e .[extra]   # adds matplotlib, needed for tests/TestCommon.py plotting
```
The MySQL driver is `mysql-connector-python` (Oracle's maintained package). The abandoned
`mysql-connector` installs into the same `mysql/connector` directory, so having both in one
environment yields a broken mix — uninstall it before installing this package.

Run tests (unittest-based, not pytest):
```
python -m unittest discover -s tests -t . -p "Test*.py"   # everything
python -m unittest tests.TestDbMySql                      # just the standalone ones
python -m unittest tests.TestCommunication.TestCommunication.test001_get_fe_cards   # single test
```
The whole suite runs anywhere: `tests.TestDbMySql` fakes the MySQL driver, and
`tests.TestCommunication` discovers the VMS device in `setUpClass` and skips itself when none
answers, instead of waiting for a connection that never comes. Point it at another network with
`VMS_BROADCAST` (default `10.0.0.255`). The hardware tests still need the internal `lecore`
package, which is deliberately not declared in `pyproject.toml`.

Check a real database by hand after changing the MySQL driver (needs a reachable server):
```
python tests/SmokeDbMySql.py --host 10.0.0.1 --user VMS --password *** --system-id 101
```

Build and publish package (see `how_to_build.md`, `build.bat`):
```
py -m build                 # produces dist/*.whl and dist/*.tar.gz
py -m twine upload dist/*   # publish to PyPI
```
`build.bat` wraps this: it deletes `dist/` and `Log/`, builds, then uploads.

## Architecture

### VMS communication protocol (`Protocol.py`, `ConfigSocket.py`, `TimeSocket.py`, `Regs.py`, `TimeStats.py`, `Discovery.py`, `Crc32.py`)

The device exposes two independent TCP connections plus a UDP discovery protocol, all defined by the same custom binary framing in `Protocol.py`: a 6-byte `"LEBVMS"` header, a 4-byte serial number, a 1-byte packet-type ID, a 1-byte sequence ID, a 4-byte length, then payload. `Protocol` is a shared, stateful helper (not a socket itself) used by both socket classes to build outgoing packets and parse incoming ones.

- **ConfigSocket** (default port 50001): request/response style. The device connects to us (`listen()` blocks until it does); every call sends a packet and blocks on `_request_response` until a full reply is parsed. Used for reading/writing registers on three distinct targets — MCU (`Mcu`/`VmsRegsMcu`), Master FPGA (`Master`/`VmsRegsMaster`), and per-channel Frontend FPGA cards (`Fe`/`VmsRegsFe`, addressed 1–16) — and for firmware updates (`update_firmware`: `Protocol.load_firmware` validates a magic header per target and bit-reverses FPGA images, then `start_flash`/`flash_page` streams the file in 1KB pages, CRC-checked via `Crc32.calc_from_byte`).
- **TimeSocket** (default port 50000): continuous streaming, not request/response. `receive_loop()` runs for a fixed duration, reassembling packets from a rolling buffer and handing each to `Protocol.parse_timestamp`, which routes to either per-revolution timestamp data or raw logger (waveform) data and forwards it into a `TimeStats` accumulator.
- **TimeStats** accumulates phase-marker/blade-count statistics from timestamp packets, and separately assembles streamed logger samples into a 2D numpy buffer (`image`/`buffer`) that visualization code (see `tests/TestCommon.py`) renders as a live image via matplotlib.
- **Regs.py** is purely address maps (`VmsRegsMcu`, `VmsRegsMaster`, `VmsRegsFe`) — these constants are the `address` arguments passed into `ConfigSocket.read_*`/`write_*`; there's no logic here, just the register layout contract with the firmware.
- **Discovery.py** is a separate, self-contained UDP broadcast protocol (distinct from the TCP protocol above — different packet format, default port 4455) for finding VMS devices on the local network and reconfiguring their server IP / socket ports before the TCP protocol can be used. It also exposes a CLI (`discovery_main`, uses `argparse`) for standalone use.

### Database read-back (`DbMySql.py`)

`DbMysql` wraps `mysql.connector` to read back data that VMS server software writes into a MySQL database (`BVMS`) — the `info_le` row and `buffer_le*` table row-counts/update-times. `get_info` returns `None` for a system that has no row (a missing row is not an error, the caller decides what it means) and with `as_dict=True` returns the row keyed by column name instead of by position. It is not exported from `pyvms/__init__.py` (import it directly as `pyvms.DbMySql.DbMysql`), and has two unrelated uses:
- Standalone test-harness methods (`speed_check`, `plot_events`) used for closed-loop VMS testing.
- The database layer for the separate [`vms-zabbix-agent`](https://github.com/LogicElements/py-vms-zabbix) package (`ZabAgent`/`ZabConfig`/`ZabSender`, formerly `src/pyvms/ZabAgent.py` etc. in this repo), which depends on `pyvms` and polls this class to report VMS health metrics to Zabbix. That package's `ZabAgent.ZabAgentFrame` is a `pywin32` Windows Service; see its own README for details.

## Testing notes

- Tests use `unittest`, with shared fixtures via multiple inheritance rather than `unittest.TestCase` subclassing alone: `class TestCommunication(unittest.TestCase, TestCommon)`, where `TestCommon` supplies `class_setup`/`common_setup`/etc. and helper methods (`measure_time`, `get_logger`) built on `ConfigSocket`/`TimeSocket`/`TimeStats`.
- Tests are hardware-in-the-loop: `TestCommon.class_setup` opens `ConfigSocket`/`TimeSocket` listeners and blocks waiting for a physical VMS device to dial in; there is no mock/simulated device.
- `tests/TestCommunication.py` depends on `lecore.TestFrame`, an internal Logic Elements package not published alongside `pyvms`.
- Development happens in `.venv` at the repository root, built from **64-bit** Python 3.14 (`py -3.14 -m venv .venv`). Keeping it 64-bit is not optional: 32-bit interpreters time out waiting for the VMS device to connect (`ConfigSocket.listen()` never completes `accept()`) even though the device sends TCP SYNs correctly and Windows Firewall rules are fine — a 32-bit (WOW64) process's inbound TCP appears to be silently blocked here, likely by the SentinelOne endpoint agent. Verified by connecting successfully only from a 64-bit interpreter. When switching interpreters, make sure `pyvms` is installed editable there (`pip install -e .`) so it points at this repo instead of a stale published version.
