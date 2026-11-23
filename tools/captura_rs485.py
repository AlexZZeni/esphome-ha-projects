"""Escuta um barramento RS-485 e grava os quadros, sem nunca transmitir.

O adaptador USB-RS485 CH340 liga o transmissor com o RTS ativo. Por isso a porta
é sempre aberta com o RTS e o DTR desligados, e o script nunca escreve nela.

Uso:
    python captura_rs485.py COM6 --varrer          # testa as velocidades comuns
    python captura_rs485.py COM6 --baud 4800       # captura e grava um log

Durante a captura, digite uma anotação e aperte Enter para marcá-la no log
(por exemplo, "liguei frio"). Ctrl+C encerra e mostra o resumo.
"""

import argparse
import datetime
import sys
import threading
import time
from collections import Counter

import serial

BAUD_RATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
PARITIES = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}


def open_port(port, baud, parity="N", stopbits=1):
    """Open the port with RTS and DTR off before the first byte can be sent."""
    ser = serial.serial_for_url(port, do_not_open=True)
    ser.baudrate = baud
    ser.bytesize = serial.EIGHTBITS
    ser.parity = PARITIES[parity]
    ser.stopbits = serial.STOPBITS_TWO if stopbits == 2 else serial.STOPBITS_ONE
    ser.rtscts = False
    ser.dsrdtr = False
    ser.xonxoff = False
    ser.rts = False
    ser.dtr = False
    ser.timeout = 0.005
    ser.open()
    ser.rts = False
    ser.dtr = False
    return ser


class FrameSplitter:
    """Group bytes into frames, closing a frame after `gap` seconds of silence."""

    def __init__(self, gap):
        self.gap = gap
        self.buffer = bytearray()
        self.started = None
        self.last_rx = None

    def feed(self, data, now):
        frames = self.flush(now)
        if data:
            if not self.buffer:
                self.started = now
            self.buffer += data
            self.last_rx = now
        return frames

    def flush(self, now, force=False):
        if self.buffer and (force or now - self.last_rx >= self.gap):
            frame = (self.started, bytes(self.buffer))
            self.buffer.clear()
            return [frame]
        return []


def read_frames(ser, splitter, seconds=None, stop=None):
    """Yield (time, bytes) frames until `seconds` pass or `stop` is set."""
    end = None if seconds is None else time.monotonic() + seconds
    while not (stop and stop.is_set()):
        now = time.monotonic()
        if end is not None and now >= end:
            break
        data = ser.read(ser.in_waiting or 1)
        yield from splitter.feed(data, time.monotonic())
    yield from splitter.flush(time.monotonic(), force=True)


def to_hex(data):
    return " ".join(f"{b:02X}" for b in data)


def frame_stats(frames):
    counts = Counter(data for _, data in frames)
    repeated = sum(n for n in counts.values() if n > 1)
    return {
        "bytes": sum(len(data) for _, data in frames),
        "frames": len(frames),
        "distinct": len(counts),
        "repeat": repeated / len(frames) if frames else 0.0,
        "common": counts.most_common(3),
    }


def default_gap(baud):
    # 20 ms or 4 characters, whichever is longer. USB adapters deliver bytes in
    # bursts, so a shorter gap would split frames that arrive in two reads.
    return max(0.020, 4 * 10 / baud)


def scan(args):
    print(f"Varrendo {args.porta}, {args.segundos:g} s por velocidade, 8{args.paridade}{args.stop}.")
    print("Use o controlador da parede durante a varredura para gerar tráfego.\n")
    results = []
    ser = open_port(args.porta, BAUD_RATES[0], args.paridade, args.stop)
    try:
        for baud in BAUD_RATES:
            ser.baudrate = baud
            ser.reset_input_buffer()
            gap = args.pausa / 1000 if args.pausa else default_gap(baud)
            frames = list(read_frames(ser, FrameSplitter(gap), seconds=args.segundos))
            stats = frame_stats(frames)
            results.append((baud, stats))
            print(f"{baud:>6} baud: {stats['bytes']:>6} bytes, {stats['frames']:>4} quadros, "
                  f"{stats['distinct']:>4} diferentes, {stats['repeat']:>4.0%} repetidos")
    finally:
        ser.close()

    print("\nQuadros mais comuns em cada velocidade:")
    for baud, stats in results:
        for data, n in stats["common"]:
            print(f"{baud:>6}  {n:>4}x  [{len(data):>3}] {to_hex(data[:24])}{' ...' if len(data) > 24 else ''}")

    candidates = [(s["repeat"], s["frames"], b) for b, s in results if s["frames"] >= 5]
    if not candidates:
        print("\nNenhuma velocidade recebeu quadros suficientes. Confira A, B e GND e se o barramento tem tráfego.")
        return
    repeat, _, baud = max(candidates)
    print(f"\nIndício mais forte: {baud} baud ({repeat:.0%} dos quadros se repetem). Em velocidade errada os bytes")
    print("também podem se repetir, então confira se os quadros mostrados fazem sentido antes de confiar.")


def read_notes(queue, lock, stop):
    while not stop.is_set():
        try:
            line = sys.stdin.readline()
        except (EOFError, OSError):
            return
        if not line:
            return
        with lock:
            queue.append((time.monotonic(), line.strip()))


def capture(args):
    log_path = args.log or datetime.datetime.now().strftime("captura-%Y%m%d-%H%M%S.txt")
    gap = args.pausa / 1000 if args.pausa else default_gap(args.baud)
    ser = open_port(args.porta, args.baud, args.paridade, args.stop)

    start_mono = time.monotonic()
    start_wall = datetime.datetime.now()

    def clock(mono):
        return (start_wall + datetime.timedelta(seconds=mono - start_mono)).strftime("%H:%M:%S.%f")[:-3]

    notes, lock, stop = [], threading.Lock(), threading.Event()
    threading.Thread(target=read_notes, args=(notes, lock, stop), daemon=True).start()

    seen = Counter()
    order = []
    last_time = None

    with open(log_path, "w", encoding="utf-8") as log:
        def write(line, show=True):
            log.write(line + "\n")
            log.flush()
            if show:
                print(line)

        write(f"# captura_rs485 {args.porta} {args.baud} 8{args.paridade}{args.stop}, pausa {gap * 1000:.0f} ms, "
              f"iniciada {start_wall:%Y-%m-%d %H:%M:%S}")
        print(f"Gravando em {log_path}. Digite uma anotação e Enter para marcar. Ctrl+C encerra.")
        print("* = quadro nunca visto antes nesta captura\n")
        try:
            for when, data in read_frames(ser, FrameSplitter(gap), stop=stop):
                with lock:
                    pending, notes[:] = list(notes), []
                for note_time, text in pending:
                    if text:
                        write(f"{clock(note_time)}  # {text}")
                is_new = data not in seen
                if is_new:
                    order.append(data)
                seen[data] += 1
                delta = f"+{(when - last_time) * 1000:>6.0f} ms" if last_time is not None else " " * 10
                last_time = when
                line = f"{clock(when)}  {delta}  [{len(data):>3}] {'*' if is_new else ' '} {to_hex(data)}"
                write(line, show=is_new or not args.so_novos)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            ser.close()
            with lock:
                for note_time, text in notes:
                    if text:
                        write(f"{clock(note_time)}  # {text}")
            write("")
            write(f"# {sum(seen.values())} quadros, {len(seen)} diferentes")
            for data in order:
                write(f"# {seen[data]:>6}x  [{len(data):>3}] {to_hex(data)}")
    print(f"\nLog salvo em {log_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Escuta um barramento RS-485 sem transmitir.")
    parser.add_argument("porta", help="porta serial, como COM6 ou /dev/ttyUSB0")
    parser.add_argument("--varrer", action="store_true", help="testa as velocidades comuns")
    parser.add_argument("--baud", type=int, help="velocidade para a captura")
    parser.add_argument("--paridade", choices=PARITIES, default="N", help="N, E ou O (padrão N)")
    parser.add_argument("--stop", type=int, choices=[1, 2], default=1, help="bits de parada (padrão 1)")
    parser.add_argument("--segundos", type=float, default=15, help="tempo por velocidade na varredura (padrão 15)")
    parser.add_argument("--pausa", type=float, help="silêncio em ms que separa quadros (padrão automático)")
    parser.add_argument("--log", help="arquivo do log (padrão captura-DATA-HORA.txt)")
    parser.add_argument("--so-novos", action="store_true", help="mostra na tela só os quadros novos")
    args = parser.parse_args(argv)

    if args.varrer:
        scan(args)
    elif args.baud:
        capture(args)
    else:
        parser.error("use --varrer ou --baud")


if __name__ == "__main__":
    main()
