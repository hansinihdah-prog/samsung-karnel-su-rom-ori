#!/usr/bin/env python3
"""Bandingkan ekspor simbol Image hasil build dengan kernel stok ROM (CRC modversions).
Pakai: cekcrc.py Image stock_modver.json  -> exit 0 kalau cocok semua, 1 kalau ada yang beda atau hilang.
Modul vendor ROM dikompilasi terhadap CRC kernel stok, jadi CRC beda atau simbol hilang = modul ditolak saat boot."""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kcrc import extract
tab, cnt = extract(sys.argv[1])
need = json.load(open(sys.argv[2]))
bad = [(k, v, hex(tab[k])) for k, v in need.items() if k in tab and int(v, 16) != tab[k]]
miss = [k for k in need if k not in tab]
extra = [k for k in tab if k not in need and not k.startswith('?')]
print(f"ekspor di Image: {cnt} | ekspor di kernel stok: {len(need)}")
print(f"CRC BEDA: {len(bad)} | simbol HILANG (ada di stok, tidak ada di build): {len(miss)} | simbol tambahan di build: {len(extra)}")
for k, v, o in bad[:25]: print("  beda  ", k, "stok", v, "build", o)
for k in miss[:25]: print("  hilang", k)
for k in extra[:10]: print("  extra ", k)
sys.exit(1 if (bad or miss) else 0)
