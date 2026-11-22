#!/usr/bin/env python3
"""ledger — which exact candidates a test already tried, without storing them.

A test records a concept ("zero the prime cells"); a sweep tries millions of concrete candidates. The ledger keeps,
per test, a Bloom filter (was this exact candidate tried? "no" is certain, "yes" is probable) and a HyperLogLog
(how many distinct candidates, within ~1%). Files live in cases/<case>/ledger/; writers merge on save (bits OR,
registers max), so two processes feeding the same test lose nothing.

From a case script:

    sys.path.insert(0, "holmes"); from ledger import Ledger
    with Ledger("T12", seed=7) as L:              # the seed is stored with the test: same seed, same sample
        for c in candidates:
            if not L.pick(c, 0.01) or L.seen(c):  # a reproducible 1% sample; skip what any test already tried
                continue
            ...try c...
            L.add(c)

From the shell (one candidate per line on stdin):

    python3 -I holmes/ledger.py add T12 [--seed S] < candidates.txt
    python3 -I holmes/ledger.py check "<candidate>" [-t T12]
    python3 -I holmes/ledger.py info [T12]

`holmes.py tried --candidate "<c>"` and `holmes.py show T12` read the same files.
"""
import argparse
import fcntl
import hashlib
import json
import math
import mmap
import os
import secrets
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CAPACITY, ERROR = 10_000_000, 0.001  # per Bloom segment: ~18 MB, 10 hashes, 0.1% false "probably tried"
HLL_P = 14  # 16,384 one-byte registers: ~0.8% standard error on the distinct count
MAGIC = b"HLB1"
HEAD = struct.Struct("<4sQBQQ")  # magic, bits, hashes, count, capacity


def ledger_dir(case=None):
    """case: a case name, the case's folder (a Path, as holmes.py passes it), or None for the active case."""
    if isinstance(case, Path):
        return case / "ledger"
    import holmes as H
    return H.case_dir(case or H.active_case()) / "ledger"


def _h128(x):
    d = hashlib.blake2b(x.encode() if isinstance(x, str) else x, digest_size=16).digest()
    return int.from_bytes(d[:8], "little"), int.from_bytes(d[8:], "little") | 1


def _positions(x, bits, k):
    h1, h2 = _h128(x)
    return [(h1 + i * h2) % bits for i in range(k)]


class Bloom:
    def __init__(self, capacity=CAPACITY, error=ERROR):
        self.bits = max(64, int(-capacity * math.log(error) / math.log(2) ** 2))
        self.k = max(1, round(self.bits / capacity * math.log(2)))
        self.count, self.capacity = 0, capacity
        self.data = bytearray((self.bits + 7) // 8)

    def add(self, x):
        for p in _positions(x, self.bits, self.k):
            self.data[p >> 3] |= 1 << (p & 7)
        self.count += 1

    def __contains__(self, x):
        return all(self.data[p >> 3] >> (p & 7) & 1 for p in _positions(x, self.bits, self.k))

    def dump(self):
        return HEAD.pack(MAGIC, self.bits, self.k, self.count, self.capacity) + bytes(self.data)

    @classmethod
    def load(cls, raw):
        magic, bits, k, count, capacity = HEAD.unpack_from(raw)
        if magic != MAGIC:
            raise ValueError("not a ledger Bloom segment")
        b = cls.__new__(cls)
        b.bits, b.k, b.count, b.capacity = bits, k, count, capacity
        b.data = bytearray(raw[HEAD.size:])
        return b


def contains_file(path, x):
    """Membership read from disk touching only k bytes (mmap): checking a 50-test case stays cheap."""
    with open(path, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
        magic, bits, k, _, _ = HEAD.unpack_from(m)
        return magic == MAGIC and all(m[HEAD.size + (p >> 3)] >> (p & 7) & 1 for p in _positions(x, bits, k))


class HLL:
    def __init__(self, raw=None):
        self.reg = bytearray(raw) if raw else bytearray(1 << HLL_P)

    def add(self, x):
        h = int.from_bytes(hashlib.blake2b(x.encode() if isinstance(x, str) else x, digest_size=8,
                                           person=b"hll").digest(), "little")
        i, w = h >> (64 - HLL_P), (h << HLL_P) & ((1 << 64) - 1)
        rank = min(64 - HLL_P, 64 - w.bit_length()) + 1
        if rank > self.reg[i]:
            self.reg[i] = rank

    def merge(self, other):
        self.reg = bytearray(max(a, b) for a, b in zip(self.reg, other.reg))

    def estimate(self):
        m = len(self.reg)
        e = 0.7213 / (1 + 1.079 / m) * m * m / sum(2.0 ** -r for r in self.reg)
        zeros = self.reg.count(0)
        return round(m * math.log(m / zeros)) if e <= 2.5 * m and zeros else round(e)


def _write(path, data):
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


class Ledger:
    def __init__(self, test, seed=None, case=None, capacity=CAPACITY, error=ERROR):
        self.test = test.upper()
        self.dir = ledger_dir(case)
        self.dir.mkdir(parents=True, exist_ok=True)
        meta_f = self.dir / f"{self.test}.json"
        meta = json.loads(meta_f.read_text()) if meta_f.exists() else {}
        if seed is not None and meta.get("seed") not in (None, seed):
            raise ValueError(f"{self.test} was sampled with seed {meta['seed']}; a different seed is a different test")
        self.seed = meta.get("seed", seed if seed is not None else secrets.randbits(32))
        self.capacity, self.error = meta.get("capacity", capacity), meta.get("error", error)
        _write(meta_f, json.dumps({"seed": self.seed, "capacity": self.capacity, "error": self.error}).encode())
        segs = self.segments(self.test)
        self.bloom = Bloom.load(segs[-1].read_bytes()) if segs else Bloom(self.capacity, self.error)
        self.seg = len(segs) - 1 if segs else 0
        hll_f = self.dir / f"{self.test}.hll"
        self.hll = HLL(hll_f.read_bytes() if hll_f.exists() else None)
        self.others = [p for p in self.dir.glob("*.bloom") if p not in segs[-1:]]
        self.added = 0

    def segments(self, test):
        return sorted(self.dir.glob(f"{test}.*.bloom"), key=lambda p: int(p.name.split(".")[1]))

    def pick(self, x, fraction):
        """Deterministic sample: the same seed picks the same candidates, in any order, on any machine."""
        h = int.from_bytes(hashlib.blake2b(f"{self.seed}:{x}".encode(), digest_size=8).digest(), "little")
        return h < fraction * 2 ** 64

    def seen(self, x, scope="case"):
        """True if this exact candidate was probably tried (this test, or any test of the case)."""
        if x in self.bloom:
            return True
        pool = self.others if scope == "case" else [p for p in self.others if p.name.startswith(self.test + ".")]
        return any(contains_file(p, x) for p in pool)

    def add(self, x):
        if self.bloom.count >= self.capacity:
            self.save()
            self.others.append(self.dir / f"{self.test}.{self.seg}.bloom")
            self.seg += 1
            self.bloom = Bloom(self.capacity, self.error)
        self.bloom.add(x)
        self.hll.add(x)
        self.added += 1

    def save(self):
        """Merge with what is on disk (another writer may have saved meanwhile) under a lock, then replace."""
        with open(self.dir / f"{self.test}.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            seg_f = self.dir / f"{self.test}.{self.seg}.bloom"
            if seg_f.exists():
                disk = Bloom.load(seg_f.read_bytes())
                if (disk.bits, disk.k) == (self.bloom.bits, self.bloom.k):
                    self.bloom.data = bytearray(a | b for a, b in zip(self.bloom.data, disk.data))
                    self.bloom.count = max(self.bloom.count, disk.count)  # shortcut: count is approximate under concurrency
            _write(seg_f, self.bloom.dump())
            hll_f = self.dir / f"{self.test}.hll"
            if hll_f.exists():
                self.hll.merge(HLL(hll_f.read_bytes()))
            _write(hll_f, bytes(self.hll.reg))
        self.added = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.save()


def tests_with(x, case=None):
    """Tests whose ledger probably holds this exact candidate."""
    d = ledger_dir(case)
    return sorted({p.name.split(".")[0] for p in d.glob("*.bloom") if contains_file(p, x)},
                  key=lambda t: int(t[1:]) if t[1:].isdigit() else 0) if d.is_dir() else []


def info(test=None, case=None):
    """{test: {distinct, segments, seed}} for one test or all of them."""
    d = ledger_dir(case)
    if not d.is_dir():
        return {}
    out = {}
    for hll_f in sorted(d.glob(f"{test.upper() if test else '*'}.hll")):
        t = hll_f.stem
        meta = json.loads((d / f"{t}.json").read_text()) if (d / f"{t}.json").exists() else {}
        out[t] = {"distinct": HLL(hll_f.read_bytes()).estimate(), "segments": len(list(d.glob(f"{t}.*.bloom"))),
                  "seed": meta.get("seed")}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ledger.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("test"); s.add_argument("--seed", type=int)
    s = sub.add_parser("check"); s.add_argument("candidate"); s.add_argument("-t", "--test")
    s = sub.add_parser("info"); s.add_argument("test", nargs="?")
    a = ap.parse_args(argv)
    if a.cmd == "add":
        with Ledger(a.test, a.seed) as L:
            for line in sys.stdin:
                L.add(line.rstrip("\r\n"))
            n = L.added
        print(f"{a.test.upper()}: {n} candidate(s) added; ~{info(a.test)[a.test.upper()]['distinct']} distinct in total")
    elif a.cmd == "check":
        hits = [t for t in tests_with(a.candidate) if not a.test or t == a.test.upper()]
        print(f"probably tried in {', '.join(hits)} (Bloom: {ERROR:.1%} false 'tried' at full capacity)" if hits
              else "not tried in any ledger (certain for what was recorded in a ledger)")
    else:
        rows = info(a.test)
        print("\n".join(f"{t}: ~{v['distinct']} distinct candidates, {v['segments']} segment(s), seed {v['seed']}"
                        for t, v in rows.items()) or "no ledger yet")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # ValueError, OSError, holmes.Error (no active case): one line, no traceback
        sys.exit(f"ledger: {e}")
