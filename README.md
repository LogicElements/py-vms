# pyvms — Vibration Monitoring System

[![PyPI](https://img.shields.io/pypi/v/pyvms)](https://pypi.org/project/pyvms/)
[![License](https://img.shields.io/pypi/l/pyvms)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/pyvms)](https://pypi.org/project/pyvms/)

Python client library for communicating with Logic Elements **VMS-1201** Vibration Monitoring System devices: register read/write, continuous timestamp/logger data streaming, firmware update, and network discovery.

## Features

- Read/write MCU, Master FPGA and per-channel Frontend FPGA registers over TCP
- Continuous streaming and parsing of timestamp and logger (waveform) data
- Firmware update over TCP (MCU, Master FPGA, Frontend FPGA)
- UDP broadcast discovery and remote network (re)configuration of devices
- Helper conversions for Frontend analog values (temperature, thresholds, min/max)

## Installation

```bash
pip install pyvms
```

Optional extra (adds `matplotlib`, used when plotting logger data):

```bash
pip install pyvms[extra]
```

Requires Python >= 3.7.

## Quick start

The VMS device always initiates the TCP connection — `listen()` blocks until the device connects.

### Discover devices on the network

```python
from pyvms import Discovery

d = Discovery(broadcast="10.0.0.255")
devices = d.probe()
print(devices)
```

### Read/write registers over the configuration socket

```python
from pyvms import ConfigSocket, Master, Fe

conf = ConfigSocket()
conf.listen(port=50001)  # blocks until the VMS device connects

active_cards = conf.read_master(Master.CHANNEL_ON)
value = conf.read_fe(fe=1, address=Fe.MINIMUM_MAXIMUM)

conf.close()
```

### Stream timestamp / logger data

```python
from pyvms import TimeSocket, TimeStats

time_sock = TimeSocket()
time_sock.listen(port=50000)  # blocks until the VMS device connects

stats = TimeStats()
time_sock.receive_loop(time=10, stats=stats)  # collect for 10 seconds
print(stats.print())

time_sock.close()
```

### Update firmware

```python
from pyvms import ConfigSocket, Protocol

conf = ConfigSocket()
conf.listen(port=50001)
conf.update_firmware("mcu_firmware.bin", target=Protocol.FW_MCU, mask=0)

conf.close()
```

## Testing

Tests use `unittest` and require a real VMS-1201 device on the network — the test process listens on the configuration/timestamp TCP ports and waits for the device to connect, so they cannot run standalone or in CI without hardware. They also depend on an internal Logic Elements package (`lecore`) not published with `pyvms`.

```bash
python -m unittest tests.TestCommunication
```

## Development

Build and publish the package:

```bash
python -m pip install --upgrade build twine
py -m build
py -m twine upload dist/*
```

See [`how_to_build.md`](how_to_build.md) for the full setup, including creating a virtual environment.

## License

MIT © Logic Elements s.r.o. — see [LICENSE](LICENSE).

Homepage: https://github.com/LogicElements/py-vms
