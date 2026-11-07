"""Reproduce the exact slice set used in this study.

The archive on Zenodo is 2.5 GB and Zenodo throttles to ~130 KB/s per connection,
so the study does not download it whole.  The slices used are fetched by HTTP
range requests against the archive's central directory: the byte span covering a
run of members is pulled in one request and parsed locally.  That is exactly what
this script does, so the data can be reproduced byte for byte.

Usage
-----
    python fetch.py --group GD --start 150 --count 212 --dest data/vol_gd
    python fetch.py --verify --dest data/vol_gd          # check sha256 manifest

The record is CC BY 4.0; see data/README.md for the citation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import urllib.request
import zipfile
import zlib

RECORD = "17602110"
URL = (f"https://zenodo.org/api/records/{RECORD}/files/"
       "Tomographic%20image%20stacks.zip/content")
BLOCK = 2 * 1024 * 1024


class HttpFile:
    """Minimal seekable file over HTTP range requests, with a block cache."""

    def __init__(self, url: str, block: int = BLOCK):
        self.url, self.block = url, block
        self._cache: dict[int, bytes] = {}
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            self.size = int(r.headers["Content-Length"])
        self.pos = 0

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (
            self.pos + offset if whence == 1 else self.size + offset)
        return self.pos

    def _block(self, i):
        if i not in self._cache:
            start = i * self.block
            end = min(start + self.block, self.size) - 1
            req = urllib.request.Request(
                self.url, headers={"Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                self._cache[i] = r.read()
        return self._cache[i]

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        out = bytearray()
        while n > 0:
            i = self.pos // self.block
            off = self.pos % self.block
            blk = self._block(i)
            take = min(n, len(blk) - off)
            if take <= 0:
                break
            out += blk[off:off + take]
            self.pos += take
            n -= take
        return bytes(out)


def _local_header(buf: bytes, off: int) -> dict:
    (sig, _v, flags, method, _t, _d, _crc, comp, uncomp,
     nlen, elen) = struct.unpack_from("<IHHHHHIIIHH", buf, off)
    if sig != 0x04034B50:
        raise ValueError(f"no local header at {off}")
    name = buf[off + 30:off + 30 + nlen].decode("utf-8", "replace")
    return {"name": name, "method": method, "comp": comp,
            "data": off + 30 + nlen + elen}


def fetch(group: str, start: int, count: int, dest: pathlib.Path,
          batch: int = 6, names: list[str] | None = None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    hf = HttpFile(URL)
    with zipfile.ZipFile(hf) as zf:
        infos = [i for i in zf.infolist()
                 if i.filename.startswith(f"Tomographic image stacks/{group}/")
                 and i.filename.lower().endswith(".dcm")]
    infos.sort(key=lambda i: i.filename)
    if names is not None:
        wanted = set(names)
        sel = [i for i in infos if pathlib.Path(i.filename).name in wanted]
        missing = wanted - {pathlib.Path(i.filename).name for i in sel}
        if missing:
            raise SystemExit(f"{len(missing)} manifest entries not in archive")
    else:
        sel = infos[start:start + count]
    print(f"{len(sel)} slices, {sum(i.compress_size for i in sel)/1e6:.1f} MB "
          f"compressed")
    for k in range(0, len(sel), batch):
        chunk = sel[k:k + batch]
        lo = min(i.header_offset for i in chunk)
        hi = max(i.header_offset + 30 + len(i.filename) + i.compress_size + 256
                 for i in chunk)
        tmp = dest / "_span.bin"
        subprocess.run(["curl.exe", "-L", "-s", "--retry", "5",
                        "-r", f"{lo}-{hi - 1}", "-o", str(tmp), URL], check=True)
        buf = tmp.read_bytes()
        for info in chunk:
            h = _local_header(buf, info.header_offset - lo)
            n = h["comp"] or info.compress_size
            raw = buf[h["data"]:h["data"] + n]
            data = raw if h["method"] == 0 else zlib.decompress(raw, -15)
            (dest / pathlib.Path(h["name"]).name).write_bytes(data)
        tmp.unlink()
        print(f"  {min(k + batch, len(sel))}/{len(sel)}")


def verify(dest: pathlib.Path, manifest_path: pathlib.Path) -> int:
    man = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad = 0
    for rec in man["files"]:
        f = dest / rec["name"]
        if not f.exists():
            print(f"missing  {rec['name']}")
            bad += 1
            continue
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        if h != rec["sha256"]:
            print(f"MISMATCH {rec['name']}")
            bad += 1
    print(f"{len(man['files'])} files checked, {bad} problems")
    return 1 if bad else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="GD")
    ap.add_argument("--start", type=int, default=150)
    ap.add_argument("--count", type=int, default=212)
    ap.add_argument("--dest", default="data/vol_gd")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--from-manifest", default=None,
                    help="fetch exactly the slices listed in this manifest")
    ap.add_argument("--manifest", default="data/manifest.json")
    a = ap.parse_args()
    dest = pathlib.Path(a.dest)
    if a.verify:
        sys.exit(verify(dest, pathlib.Path(a.manifest)))
    names = None
    if a.from_manifest:
        man = json.loads(pathlib.Path(a.from_manifest).read_text(encoding="utf-8"))
        names = [f["name"] for f in man["files"]]
    fetch(a.group, a.start, a.count, dest, names=names)


if __name__ == "__main__":
    main()
