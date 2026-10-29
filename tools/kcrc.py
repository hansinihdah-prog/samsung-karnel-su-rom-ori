#!/usr/bin/env python3
"""Ekstrak tabel ekspor simbol (nama -> CRC) dari Image arm64 kernel 6.6 (ksymtab prel32).
Pakai: kcrc.py Image keluaran.json
Nama dicek harus berbentuk identifier C, supaya entri palsu di awal tabel (yang menggeser
pasangan nama dan CRC) tidak ikut terbaca. Entri asli yang namanya tidak terbaca diberi nama '?<indeks>'."""
import sys, struct, array, json, re

IDENT = re.compile(rb'^[A-Za-z_][A-Za-z0-9_.]*$')

def extract(path):
    d = open(path, 'rb').read(); N = len(d)
    a = array.array('i'); a.frombytes(d[:N - N % 4]); n = len(a)

    def name_at(i):
        # entri ksymtab: tiga int32 (value_off, name_off, ns_off); nama = alamat field ke-2 + name_off
        t = (i + 1) * 4 + a[i + 1]
        if not (1 < t < N - 2) or d[t - 1] != 0: return None
        nm = d[t:d.index(b'\0', t)]
        return nm if IDENT.match(nm) else None

    runs = []; i = 0
    while i < n - 3:
        if name_at(i) and name_at(i + 3) and name_at(i + 6) and name_at(i + 9):
            s = i
            while i < n - 3 and name_at(i): i += 3
            if (i - s) // 3 > 500: runs.append((s, i))
        else:
            i += 1
    if not runs: raise SystemExit("ksymtab tidak ditemukan")
    runs.sort(); merged = [list(runs[0])]
    for s, e in runs[1:]:                       # gabungkan ksymtab + ksymtab_gpl
        if s - merged[-1][1] <= 8: merged[-1][1] = e
        else: merged.append([s, e])
    s, e = max(merged, key=lambda r: r[1] - r[0])
    cnt = (e - s) // 3
    names = [(name_at(s + 3 * k) or b"?%d" % k).decode() for k in range(cnt)]
    crcs = struct.unpack_from('<%dI' % cnt, d, e * 4)   # __kcrctab mulai tepat setelah ksymtab_gpl
    return dict(zip(names, crcs)), cnt

if __name__ == '__main__':
    tab, cnt = extract(sys.argv[1])
    print("entri ekspor:", cnt)
    json.dump({k: hex(v) for k, v in tab.items() if not k.startswith('?')}, open(sys.argv[2], 'w'), separators=(',', ':'))
