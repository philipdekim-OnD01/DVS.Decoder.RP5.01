#!/usr/bin/env python3
"""Local, sequential DVSRAW01 viewer. Python 3.9+, standard library only."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

FILE_HEADER = struct.Struct('<8s6I')
RECORD_HEADER = struct.Struct('<QQ4I')
PAYLOAD = 175680


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare(path, metadata=None):
    expected = metadata.get('raw_sha256') if metadata else None
    if path.suffix != '.gz':
        if expected and sha256(path) != expected:
            raise ValueError('RAW SHA-256 mismatch')
        return path, bool(expected)
    target = path.with_suffix('')
    if target.exists():
        if expected and sha256(target) == expected:
            return target, True
        raise ValueError(f'Existing decompressed file cannot be verified: {target}. Supply the matching JSON or choose another directory.')
    required = metadata.get('raw_file_bytes', 0) if metadata else 0
    if required and shutil.disk_usage(path.parent).free < required + 64 * 1024 * 1024:
        raise ValueError('Not enough disk space to decompress RAW')
    print('Decompressing losslessly; original gzip remains unchanged...', flush=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.dvs-inflate-', delete=False) as dst:
            temp = Path(dst.name)
            h = hashlib.sha256()
            with gzip.open(path, 'rb') as src:
                for block in iter(lambda: src.read(4 * 1024 * 1024), b''):
                    h.update(block)
                    dst.write(block)
        if expected and h.hexdigest() != expected:
            raise ValueError('Decompressed RAW SHA-256 mismatch')
        with Recording(temp):
            pass
        # Never replace an existing raw file, including one created concurrently.
        os.link(temp, target)
        return target, bool(expected)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


class Recording:
    def __init__(self, path):
        self.path = Path(path)
        self.fd = os.open(self.path, os.O_RDONLY)
        try:
            header = os.pread(self.fd, 32, 0)
            if len(header) != 32:
                raise ValueError('Truncated file header')
            magic, w, h, payload, rh, count, window = FILE_HEADER.unpack(header)
            if (magic, w, h, payload, rh) != (b'DVSRAW01', 960, 720, PAYLOAD, 32) or count == 0:
                raise ValueError('Unsupported DVSRAW01 header')
            self.count = count
            self.stride = 32 + payload
            if os.fstat(self.fd).st_size != 32 + count * self.stride:
                raise ValueError('File length does not match record count')
            first = last = None
            gaps = regressions = duplicates = errors = 0
            prev = None
            for i in range(count):
                rec = RECORD_HEADER.unpack(os.pread(self.fd, 32, 32 + i * self.stride))
                if rec[-1] != PAYLOAD or rec[-2] < PAYLOAD:
                    raise ValueError(f'Invalid record length at {i}')
                if first is None:
                    first = rec
                if prev:
                    delta = (rec[2] - prev[2]) & 0xffffffff
                    if delta == 0: duplicates += 1
                    elif delta < 0x80000000: gaps += delta - 1
                    else: regressions += 1
                errors += bool(rec[3] & 0x40)
                prev = last = rec
            elapsed = (last[1] - first[1]) / 1e9
            self.info = dict(name=self.path.name, count=count, width=w, height=h,
                             window_ms=window, elapsed=elapsed, first_ns=str(first[1]),
                             received_fps=(count-1)/elapsed if elapsed > 0 else 0,
                             host_sequence_gaps=gaps, host_sequence_regressions=regressions,
                             host_sequence_duplicates=duplicates, host_error_frames=errors)
        except BaseException:
            os.close(self.fd)
            raise

    def record(self, index):
        if not 0 <= index < self.count:
            raise IndexError('Frame index out of range')
        b = os.pread(self.fd, self.stride, 32 + index * self.stride)
        if len(b) != self.stride:
            raise ValueError('Truncated record')
        return b

    def close(self):
        os.close(self.fd)

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('file', type=Path)
    p.add_argument('--metadata', type=Path, help='Matching capture JSON containing raw_sha256')
    p.add_argument('--port', type=int, default=0, help='Default: choose a free localhost port')
    p.add_argument('--no-browser', action='store_true')
    p.add_argument('--check', action='store_true', help='Validate without opening a player')
    args = p.parse_args()
    source = args.file.resolve()
    candidate = args.metadata or (source.with_suffix('').with_suffix('.json') if source.suffix == '.gz' else source.with_suffix('.json'))
    metadata = json.loads(candidate.read_text()) if candidate.is_file() else None
    path, verified = prepare(source, metadata)
    with Recording(path) as recording:
        recording.info['sha256_verified'] = verified
        if args.check:
            print(json.dumps(recording.info, indent=2)); return
        assets = Path(__file__).parent

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                route = urlparse(self.path)
                try:
                    if route.path == '/info':
                        body, mime = json.dumps(recording.info).encode(), 'application/json'
                    elif route.path == '/frame':
                        index = int(parse_qs(route.query)['i'][0])
                        body, mime = recording.record(index), 'application/octet-stream'
                    elif route.path in ('/', '/decoder.js', '/player.js'):
                        name = 'index.html' if route.path == '/' else route.path[1:]
                        body = (assets / name).read_bytes()
                        mime = 'text/html; charset=utf-8' if name.endswith('.html') else 'text/javascript'
                    else:
                        self.send_error(404); return
                    self.send_response(200)
                    self.send_header('Content-Type', mime)
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.end_headers(); self.wfile.write(body)
                except (ValueError, KeyError, IndexError) as exc:
                    self.send_error(400, str(exc))
                except (BrokenPipeError, ConnectionResetError):
                    pass
            def log_message(self, *args): pass

        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
        url = f'http://127.0.0.1:{server.server_port}/'
        print('Open:', url, '\nCtrl+C stops the player.', flush=True)
        if not args.no_browser:
            threading.Timer(.3, lambda: webbrowser.open(url)).start()
        try: server.serve_forever()
        except KeyboardInterrupt: pass
        finally: server.server_close()


if __name__ == '__main__':
    main()
