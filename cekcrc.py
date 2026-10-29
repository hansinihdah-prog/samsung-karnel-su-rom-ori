#!/usr/bin/env python3
"""Bandingkan CRC ekspor Image hasil build dengan CRC yang diminta modul vendor stok.
Pakai: cekcrc.py Image stock_modver.json  -> exit 0 kalau semua cocok, 1 kalau ada beda."""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kcrc import extract
tab, cnt = extract(sys.argv[1])
need = json.load(open(sys.argv[2]))
bad = [(k, v, hex(tab[k])) for k, v in need.items() if k in tab and int(v, 16) != tab[k]]
miss = [k for k in need if k not in tab]
print(f"ekspor di Image: {cnt} | dibutuhkan modul: {len(need)}")
print(f"CRC beda: {len(bad)} | simbol hilang: {len(miss)}")
for k, v, o in bad[:15]: print("  beda", k, "modul minta", v, "kernel punya", o)
for k in miss[:15]: print("  hilang", k)
sys.exit(1 if bad else 0)  # simbol "hilang" = diekspor modul lain, wajar
