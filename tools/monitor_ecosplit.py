"""Mostra ao vivo os valores do barramento do Carrier Ecosplit, sem nunca transmitir.

Usa o mapa do protocolo em docs/modelos.md. A porta é aberta com o RTS e o DTR
desligados, como no captura_rs485.py, e o script nunca escreve nela.

Uso:
    python monitor_ecosplit.py COM6
    python monitor_ecosplit.py COM6 --csv leituras.csv   # também grava uma linha por ciclo

Ctrl+C encerra.
"""

import argparse
import csv
import datetime
import os
import sys
import time

from captura_rs485 import open_port

HEADER = b"\x9A\x56"
MODES = {1: "frio", 2: "aquecer", 3: "ventilar"}
TEMP_OFFSET = 55

# (key, label, unit, confirmed, byte of the unit frame shown raw for hypotheses).
FIELDS = [
    ("ligado", "Ligado", "", True, None),
    ("modo", "Modo", "", True, None),
    ("desejada", "Temperatura desejada", "°C", True, None),
    ("ambiente", "Temperatura ambiente", "°C", True, None),
    ("externa", "Externa", "°C", True, None),
    ("condensador", "Condensador", "°C", True, None),
    ("succao", "Sucção", "°C", True, None),
    ("descarga1", "Descarga 1", "°C", True, None),
    ("descarga2", "Descarga 2", "°C", True, None),
    ("corrente1", "Corrente 1", "A", True, None),
    ("corrente2", "Corrente 2", "A", True, None),
    ("dissipador", "Dissipador", "°C", True, None),
    ("barramento_dc", "Barramento DC", "V", True, None),
    ("frequencia", "Frequência do inverter", "Hz", True, None),
    ("corrente_inverter", "Corrente do inverter", "A", True, None),
    ("byte13", "Byte 13 (configuração?)", "", False, 13),
    ("byte21", "Byte 21 (vent. externo?)", "", False, 21),
    ("byte22", "Byte 22", "", False, 22),
    ("byte23", "Byte 23 (inverter?)", "", False, 23),
    ("byte26", "Byte 26 (contador?)", "", False, 26),
    ("estado", "Estado", "", False, 17),
]

# Bits of byte 17 seen so far, in the order they turned on before the compressor started:
# 08 when the unit turns on, 04 just before the byte 21 ramp, then 01, then 02 with current 2.
STATE_BITS = [
    (0x08, "ventilador"),
    (0x04, "bit 04"),
    (0x01, "bit 01"),
    (0x02, "bit 02"),
]


def checksum_ok(frame):
    xor = 0
    for b in frame[:-2]:
        xor ^= b
    return frame[-2] == xor and frame[-1] == sum(frame[:-1]) & 0xFF


class FrameParser:
    """Find `9A 56 ... len ... xor sum` frames in a byte stream and drop bad ones."""

    def __init__(self):
        self.buffer = bytearray()
        self.invalid = 0

    def feed(self, data):
        self.buffer += data
        frames = []
        while True:
            start = self.buffer.find(HEADER)
            if start < 0:
                del self.buffer[:-1]
                return frames
            if start:
                del self.buffer[:start]
                self.invalid += 1
            if len(self.buffer) < 5:
                return frames
            size = self.buffer[4]
            if size < 7:
                del self.buffer[:1]
                self.invalid += 1
                continue
            if len(self.buffer) < size:
                return frames
            frame = bytes(self.buffer[:size])
            if checksum_ok(frame):
                frames.append(frame)
                del self.buffer[:size]
            else:
                del self.buffer[:1]
                self.invalid += 1


def decode_controller(f):
    return {
        "ligado": "sim" if f[5] & 0x80 else "não",
        "desejada": f[5] & 0x7F,
        "ambiente": ((f[6] << 8) | f[7]) / 10,
        "modo": MODES.get(f[10], f"desconhecido ({f[10]:02X})"),
    }


def decode_unit(f):
    return {
        "externa": f[7] - TEMP_OFFSET,
        "condensador": f[8] - TEMP_OFFSET,
        "succao": f[9] - TEMP_OFFSET,
        "descarga1": f[10] - TEMP_OFFSET,
        "descarga2": f[11] - TEMP_OFFSET,
        "dissipador": f[12] - TEMP_OFFSET,
        "corrente1": f[14] * 0.25,
        "corrente2": f[15] * 0.25,
        "estado": describe_state(f[17]),
        "barramento_dc": f[20] * 4,
        "frequencia": f[18],
        "corrente_inverter": f[19] * 0.25,
        "byte13": f[13],
        "byte21": f[21],
        "byte22": f[22],
        "byte23": f[23],
        "byte26": f[26],
    }


def describe_state(byte):
    names = [name for bit, name in STATE_BITS if byte & bit]
    unknown = byte & ~sum(bit for bit, _ in STATE_BITS) & 0xFF
    if unknown:
        names.append(f"outros bits {unknown:02X}")
    return f"{byte:02X}: " + (", ".join(names) if names else "nenhum")


def decode(frame):
    """Return (source name, values) for a known frame, or None."""
    src, dst, size = frame[2], frame[3], frame[4]
    if (src, dst, size) == (0xC1, 0xFE, 13):
        return "controlador", decode_controller(frame)
    if (src, dst, size) == (0x01, 0xFE, 31):
        return "evaporadora", decode_unit(frame)
    return None


def format_value(value, unit):
    if isinstance(value, float):
        text = f"{value:.2f}" if unit == "A" else f"{value:.1f}"
    else:
        text = str(value)
    return f"{text} {unit}".rstrip()


def csv_value(value):
    return f"{value:g}".replace(".", ",") if isinstance(value, float) else value


def highlight(frame, baseline):
    """Hex dump with the bytes that differ from the first frame seen in yellow."""
    parts = []
    for i, b in enumerate(frame):
        changed = baseline is not None and i < len(baseline) and baseline[i] != b and i < len(frame) - 2
        parts.append(f"\x1b[33m{b:02X}\x1b[0m" if changed else f"{b:02X}")
    return " ".join(parts)


def render(port, values, raw, baseline, counts, parser, last_rx):
    now = time.monotonic()
    age = now - last_rx if last_rx else None
    status = "sem dados ainda" if age is None else (f"último quadro há {age:.1f} s" if age < 3 else
                                                    f"\x1b[31mSEM DADOS há {age:.0f} s\x1b[0m")
    lines = [
        f"Carrier Ecosplit em {port}, 9600 8N1, só escutando    {datetime.datetime.now():%H:%M:%S}",
        f"{sum(counts.values())} quadros válidos, {parser.invalid} descartados, {status}",
        "",
    ]
    unit_frame = raw.get("evaporadora")
    lines.append("Confirmados")
    for key, label, unit, confirmed, _ in FIELDS:
        if confirmed:
            value = format_value(values[key], unit) if key in values else "—"
            lines.append(f"  {label:<26} {value:>10}")
    lines.append("")
    lines.append("Hipóteses (valor convertido e byte bruto do quadro da evaporadora)")
    for key, label, unit, confirmed, index in FIELDS:
        if confirmed:
            continue
        value = format_value(values[key], unit) if key in values else "—"
        byte = f"byte {index:>2} = {unit_frame[index]:02X} ({unit_frame[index]:>3})" if unit_frame else ""
        if key == "estado":
            lines.append(f"  {label:<26} {byte}  {value}")
        else:
            lines.append(f"  {label:<26} {value:>10}   {byte}")
    lines.append("")
    lines.append("Quadros brutos (em amarelo, os bytes que mudaram desde o início):")
    for name in ("controlador", "evaporadora"):
        if name in raw:
            lines.append(f"  {name:<12} {highlight(raw[name], baseline.get(name))}")
    others = {k: v for k, v in counts.items() if k not in ("controlador", "evaporadora")}
    if others:
        lines.append("  outros: " + ", ".join(f"{k} {v}x" for k, v in others.items()))
    lines.append("")
    lines.append("Ctrl+C encerra.")
    sys.stdout.write("\x1b[H" + "\x1b[K\n".join(lines) + "\x1b[K\n\x1b[J")
    sys.stdout.flush()


def main(argv=None):
    parser_args = argparse.ArgumentParser(description="Mostra ao vivo os valores do Carrier Ecosplit.")
    parser_args.add_argument("porta", help="porta serial, como COM6 ou /dev/ttyUSB0")
    parser_args.add_argument("--csv", help="grava uma linha por ciclo neste arquivo CSV")
    args = parser_args.parse_args(argv)

    if os.name == "nt":
        os.system("")  # turns on ANSI escape codes in the Windows console

    ser = open_port(args.porta, 9600)
    parser = FrameParser()
    values, raw, baseline, counts = {}, {}, {}, {}
    last_rx = None
    last_draw = 0.0

    csv_file = writer = None
    if args.csv:
        new = not os.path.exists(args.csv)
        csv_file = open(args.csv, "a", newline="", encoding="utf-8")
        # Semicolons and decimal commas, so Excel in Portuguese opens it in columns.
        writer = csv.writer(csv_file, delimiter=";")
        if new:
            writer.writerow(["hora"] + [key for key, *_ in FIELDS])

    sys.stdout.write("\x1b[2J")
    try:
        while True:
            data = ser.read(ser.in_waiting or 1)
            for frame in parser.feed(data):
                last_rx = time.monotonic()
                decoded = decode(frame)
                name = decoded[0] if decoded else f"{frame[2]:02X}->{frame[3]:02X}"
                counts[name] = counts.get(name, 0) + 1
                if not decoded:
                    continue
                values.update(decoded[1])
                raw[name] = frame
                baseline.setdefault(name, frame)
                # One CSV row per cycle, when the unit frame closes it.
                if writer and name == "evaporadora" and "ligado" in values:
                    writer.writerow([datetime.datetime.now().isoformat(timespec="seconds")] +
                                    [csv_value(values.get(key, "")) for key, *_ in FIELDS])
                    csv_file.flush()
            if time.monotonic() - last_draw > 0.5:
                render(args.porta, values, raw, baseline, counts, parser, last_rx)
                last_draw = time.monotonic()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        if csv_file:
            csv_file.close()
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
