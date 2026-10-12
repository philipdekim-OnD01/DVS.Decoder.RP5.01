#!/usr/bin/env python3
"""
Minimal Samsung S5KRC1S DVS bring-up helper for Raspberry Pi 5 CAM0.

Default mode is non-destructive probe:
  python3 s5krc1s_probe_init.py --bus 13

Reset + probe:
  python3 s5krc1s_probe_init.py --bus 13 --reset-gpio 35

Write a minimal experimental init sequence:
  python3 s5krc1s_probe_init.py --bus 13 --addr 0x20 --reset-gpio 35 --init

Notes:
- Raspberry Pi 5 CAM0 pin 18 maps to CD0_IO1 / GPIO35 on the tested board.
- S5KRC1S must ACK on I2C before register init can work.
- This script intentionally uses only a small register subset already identified
  during bring-up. A real driver still needs the vendor-recommended full sequence.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from smbus2 import SMBus, i2c_msg


I2C_SLAVE = 0x0703


@dataclass(frozen=True)
class RegWrite:
    reg: int
    value: int
    note: str


PROBE_REGS = [
    0x0000,
    0x0001,
    0x0100,  # common mode select candidate
    0x3024,  # CCI address control, reset value seen in datasheet text
    0x3901,  # CSI-2 data identifier
    0x3902,  # CSI-2 word count low
    0x3903,  # CSI-2 word count high
    0x3910,  # MIPI timeout / endian control
    0x3915,  # MIPI clock / lane mode
]


# No hand-written experimental init sequence is kept here. Use the vendor setfile
# only after the sensor address has been verified by reading 0x3024 / 0x3000.
INIT_SEQUENCE: list[RegWrite] = []


def run_pinctrl(gpio: int, state: str) -> None:
    subprocess.run(["pinctrl", "set", str(gpio), "op", state], check=False)


def reset_sensor(gpio: int, delay_s: float = 0.5) -> None:
    print(f"Reset via GPIO{gpio}: low -> high")
    run_pinctrl(gpio, "dl")
    time.sleep(0.1)
    run_pinctrl(gpio, "dh")
    time.sleep(delay_s)
    subprocess.run(["pinctrl", "get", str(gpio)], check=False)


class I2C16:
    def __init__(self, bus: int, addr: int):
        self.bus_number = bus
        self.path = f"/dev/i2c-{bus}"
        self.addr = addr

    def _open(self):
        fd = os.open(self.path, os.O_RDWR)
        try:
            fcntl.ioctl(fd, I2C_SLAVE, self.addr)
            return fd
        except Exception:
            os.close(fd)
            raise

    def read8(self, reg: int) -> int:
        register_address = [(reg >> 8) & 0xFF, reg & 0xFF]
        write_msg = i2c_msg.write(self.addr, register_address)
        read_msg = i2c_msg.read(self.addr, 1)
        with SMBus(self.bus_number) as bus:
            bus.i2c_rdwr(write_msg, read_msg)
        return list(read_msg)[0]

    def write8(self, reg: int, value: int) -> None:
        payload = [(reg >> 8) & 0xFF, reg & 0xFF, value & 0xFF]
        write_msg = i2c_msg.write(self.addr, payload)
        with SMBus(self.bus_number) as bus:
            bus.i2c_rdwr(write_msg)

    def fd_ok(self) -> bool:
        try:
            fd = self._open()
            os.close(fd)
            return True
        except Exception:
            return False


def probe(bus: int, addrs: list[int]) -> list[int]:
    found: list[int] = []
    for addr in addrs:
        dev = I2C16(bus, addr)
        readable = []
        ok = False
        for reg in PROBE_REGS:
            try:
                value = dev.read8(reg)
                readable.append(f"{reg:04x}={value:02x}")
                ok = True
            except Exception:
                readable.append(f"{reg:04x}=ERR")
        if ok:
            print(f"0x{addr:02x}: " + ", ".join(readable))
            found.append(addr)
    return found


def init_sensor(bus: int, addr: int) -> None:
    if not INIT_SEQUENCE:
        raise SystemExit(
            "--init is disabled. Verify the sensor with 0x3024/0x3000 first, "
            "then apply the vendor setfile with --setfile."
        )

    dev = I2C16(bus, addr)
    try:
        dev.read8(PROBE_REGS[0])
    except Exception as exc:
        raise SystemExit(
            f"address 0x{addr:02x} did not respond to 16-bit register read "
            f"on /dev/i2c-{bus}: {exc}"
        )

    print(f"Writing experimental init sequence to bus {bus}, addr 0x{addr:02x}")
    for item in INIT_SEQUENCE:
        print(f"  {item.reg:04x} <- {item.value:02x}  # {item.note}")
        dev.write8(item.reg, item.value)
        time.sleep(0.01)

    print("Readback:")
    for reg in PROBE_REGS:
        try:
            print(f"  {reg:04x}={dev.read8(reg):02x}")
        except Exception:
            print(f"  {reg:04x}=ERR")


SETFILE_RE = re.compile(
    r"^\s*([0-9a-fA-F]+)\s*:\s*([0-9a-fA-F]+)\s*=\s*([0-9a-fA-F]+)"
)


def parse_setfile(path: Path) -> list[RegWrite]:
    writes: list[RegWrite] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        m = SETFILE_RE.match(line)
        if not m:
            continue
        slave, reg, value = (int(x, 16) for x in m.groups())
        comment = ""
        if "//" in line:
            comment = line.split("//", 1)[1].strip()
        writes.append(RegWrite(reg, value, f"line {lineno}, slave 0x{slave:02x}" + (f", {comment}" if comment else "")))
    return writes


def write_setfile(bus: int, addr: int, path: Path, stream_on: bool = False) -> None:
    writes = parse_setfile(path)
    if not writes:
        raise SystemExit(f"no register writes parsed from {path}")

    dev = I2C16(bus, addr)
    print(f"Writing {len(writes)} setfile entries to /dev/i2c-{bus}, addr 0x{addr:02x}")
    for idx, item in enumerate(writes, 1):
        value = item.value
        try:
            dev.write8(item.reg, value)
        except Exception as exc:
            raise SystemExit(
                f"write failed at #{idx}: reg 0x{item.reg:04x} <- 0x{value:02x} "
                f"({item.note}): {exc}"
            )
        if idx <= 8 or item.reg in {0x0100, 0x3915, 0x3902, 0x3903, 0x3910}:
            print(f"  {idx:03d}: {item.reg:04x} <- {value:02x}  # {item.note}")
        time.sleep(0.002)

    if stream_on:
        dev.write8(0x3000, 0x02)
        print("  stream: 3000 <- 02  # SEL_MODE_r: Stream")

    print("Setfile write completed")


def parse_addr_list(raw: str | None) -> list[int]:
    if raw:
        return [int(x, 0) for x in raw.split(",")]

    # Include likely 7-bit forms and the observed non-sensor responders.
    base = [0x10, 0x20, 0x21, 0x22, 0x24, 0x30, 0x34, 0x36]
    base.extend(range(0x03, 0x78))
    seen = set()
    out = []
    for addr in base:
        if addr not in seen:
            out.append(addr)
            seen.add(addr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bus", type=int, default=13)
    ap.add_argument("--addr", type=lambda x: int(x, 0), default=None)
    ap.add_argument("--addrs", help="comma-separated address list, e.g. 0x20,0x10")
    ap.add_argument("--reset-gpio", type=int, default=None)
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--setfile", type=Path)
    ap.add_argument("--stream-on", action="store_true", help="write 0x3000=0x02 after applying a setfile")
    args = ap.parse_args()

    if args.reset_gpio is not None:
        reset_sensor(args.reset_gpio)

    if args.init:
        if args.addr is None:
            raise SystemExit("--init requires --addr")
        init_sensor(args.bus, args.addr)
        return 0

    if args.setfile:
        if args.addr is None:
            raise SystemExit("--setfile requires --addr")
        write_setfile(args.bus, args.addr, args.setfile, stream_on=args.stream_on)
        return 0

    addrs = [args.addr] if args.addr is not None else parse_addr_list(args.addrs)
    print(f"Probing /dev/i2c-{args.bus}")
    found = probe(args.bus, addrs)
    print("Found:", " ".join(f"0x{x:02x}" for x in found) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
