#!/usr/bin/env python3
"""Verify that two audio files hold the same SOUND, so a vault copy can be removed (CR-170).

    python3 audio_verify.py <file-a> <file-b>              # one pair
    python3 audio_verify.py --dir <inbox-audio> --against <archive>   # every pair by basename
    python3 audio_verify.py --hash <file>                  # the content hash alone

Deciding that an audio file is safe to remove is a question about sound, and the
obvious tests give the wrong answer:

  - A BYTE COMPARE is wrong. Measured on 64 pairs that an archive and an inbox held in
    common: 37 existed in both and NONE was byte-identical. Each differed in 160-200
    bytes, scattered across fragment headers (`mfhd`) and the trailing `moov` atom --
    container timestamps and sequence numbers rewritten by whatever last muxed the file.
    A byte compare calls every one of them a different recording.

  - A THRESHOLD on how many bytes differ, and how near the end, is worse. It passed on
    small files and failed on large ones, because the differing tail is proportional to
    the file: the rule is most permissive exactly where the stakes are highest.

  - COMPARING THE MEDIA PAYLOAD holds. Walk the ISO-BMFF box tree, concatenate every
    `mdat` payload in order, hash that. Metadata may differ; the sound may not. On the
    same measured set: 64 of 64 identical, which is what made the removal defensible.

This script REPORTS. It never deletes, moves or rewrites anything -- a pair that does not
verify is a finding, not a prompt. `.ephemeral/` may die and audio may be archived, but
what leaves the vault is the operator's decision (CR-103, and `stale_vs_junk`).

A file that is not ISO-BMFF (a WAV, an MP3, an Ogg) has no `mdat`; the hash then covers
the whole file and the report says so, because silently hashing a different thing is how
a verification stops verifying.
"""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

CONTAINER = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"moof", b"traf", b"mvex", b"edts"}


def boxes(data: bytes, start: int = 0, end: int | None = None):
    """Yield (type, payload_start, payload_end) for the boxes at one level.

    Tolerant by design: a truncated final box is yielded with what is there rather than
    raising, because a partially synced file is exactly the case worth reporting.
    """
    end = len(data) if end is None else end
    pos = start
    while pos + 8 <= end:
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        head = 8
        if size == 1:                                   # 64-bit extended size
            if pos + 16 > end:
                return
            size = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
            head = 16
        elif size == 0:                                 # extends to the end of the file
            size = end - pos
        if size < head:
            return                                      # malformed; stop rather than loop
        yield kind, pos + head, min(pos + size, end)
        pos += size


def mdat_payloads(data: bytes):
    """Every `mdat` payload, in file order, descending into container boxes."""
    for kind, s, e in boxes(data):
        if kind == b"mdat":
            yield data[s:e]
        elif kind in CONTAINER:
            for kind2, s2, e2 in boxes(data, s, e):
                if kind2 == b"mdat":
                    yield data[s2:e2]


def content_hash(path: Path):
    """(hexdigest, basis). `basis` is 'mdat' or 'whole-file', and is part of the answer."""
    data = Path(path).read_bytes()
    h = hashlib.sha256()
    found = False
    for payload in mdat_payloads(data):
        found = True
        h.update(payload)
    if not found:
        return hashlib.sha256(data).hexdigest(), "whole-file"
    return h.hexdigest(), "mdat"


def verify(a: Path, b: Path):
    ha, basis_a = content_hash(a)
    hb, basis_b = content_hash(b)
    same = ha == hb and basis_a == basis_b
    return {"a": str(a), "b": str(b), "verified": same, "basis": basis_a,
            "basis_b": basis_b, "hash_a": ha[:16], "hash_b": hb[:16],
            "bytes_identical": Path(a).read_bytes() == Path(b).read_bytes()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", help="two files to compare")
    ap.add_argument("--dir", help="a folder of audio to verify")
    ap.add_argument("--against", help="the archive to verify it against")
    ap.add_argument("--hash", help="print one file's content hash and stop")
    a = ap.parse_args(argv)

    if a.hash:
        h, basis = content_hash(Path(a.hash))
        print(f"{h}  {basis}  {a.hash}")
        return 0

    if a.dir and a.against:
        here, there = Path(a.dir), Path(a.against)
        rows, verified, unverified, missing = [], 0, 0, 0
        for f in sorted(p for p in here.iterdir() if p.is_file() and not p.name.startswith(".")):
            counterpart = there / f.name
            if not counterpart.is_file():
                missing += 1
                rows.append(f"[NO COUNTERPART] {f.name} -- not in the archive; keep")
                continue
            r = verify(f, counterpart)
            if r["verified"]:
                verified += 1
                note = "" if r["bytes_identical"] else "  (bytes differ, sound does not)"
                rows.append(f"[VERIFIED] {f.name}  {r['basis']}{note}")
            else:
                unverified += 1
                rows.append(f"[DIFFERENT] {f.name} -- {r['hash_a']} vs {r['hash_b']} "
                            f"({r['basis']}/{r['basis_b']}); keep and look")
        print("\n".join(rows) if rows else "no files")
        print(f"\n{verified} verified, {unverified} different, {missing} without a counterpart. "
              f"Nothing was removed: this script reports (CR-170).")
        return 0

    if len(a.files) != 2:
        ap.error("give two files, or --dir with --against, or --hash")
    r = verify(Path(a.files[0]), Path(a.files[1]))
    print(f"{'VERIFIED' if r['verified'] else 'DIFFERENT'}  basis={r['basis']}  "
          f"bytes_identical={r['bytes_identical']}")
    print(f"  {r['hash_a']}  {r['a']}")
    print(f"  {r['hash_b']}  {r['b']}")
    return 0 if r["verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
