#!/usr/bin/env python3
"""
Perbarui daftar anggota di portal KIPM-UP SIGMA dari file Excel.

Cara pakai:
    pip install openpyxl cryptography
    python update_anggota.py DAFTAR_ANGGOTA.xlsx index.html

Format Excel: satu sheet per angkatan (contoh "GEN 1", "GEN 2", ...),
baris pertama berisi header: NIA | NAMA | JABATAN.

Nama dan jabatan tidak disimpan sebagai teks biasa di halaman. Setiap anggota
disimpan sebagai data terenkripsi yang hanya bisa dibuka oleh NIA miliknya,
sehingga daftar nama tidak terbaca begitu saja lewat "view source" atau
pencarian di GitHub.
"""
import base64, hashlib, json, os, re, secrets, sys
from openpyxl import load_workbook
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITER = 150000
START, END = "/*MEMBERS_START*/", "/*MEMBERS_END*/"


def baca_excel(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    out, ganda = [], set()
    for ws in wb.worksheets:
        m = re.search(r"\d+", ws.title)
        gen = m.group(0) if m else ws.title
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue
            nia, nama, jab = (tuple(row) + (None, None, None))[:3]
            if nia is None and nama is None:
                continue
            nia = re.sub(r"[\s.\-]", "", str(nia or "")).upper()
            nama = " ".join(str(nama or "").split())
            jab = " ".join(str(jab or "").split())
            if not nia or not nama:
                print("Lewati baris %d di sheet %s (NIA atau nama kosong)" % (i + 1, ws.title))
                continue
            if nia in ganda:
                print("Peringatan: NIA ganda %s (sheet %s), dipakai data terakhir" % (nia, ws.title))
            ganda.add(nia)
            out.append((nia, nama, jab, gen))
    return out


def enkripsi(anggota, salt):
    hasil = {}
    for nia, nama, jab, gen in anggota:
        id_ = hashlib.sha256((salt + ":" + nia).encode()).hexdigest()[:16]
        key = hashlib.pbkdf2_hmac("sha256", nia.encode(), salt.encode(), ITER, 32)
        iv = secrets.token_bytes(12)
        payload = json.dumps({"n": nama, "j": jab, "g": gen}, ensure_ascii=False, separators=(",", ":")).encode()
        hasil[id_] = base64.b64encode(iv + AESGCM(key).encrypt(iv, payload, None)).decode()
    return hasil


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    xlsx = sys.argv[1]
    html = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    s = open(html, encoding="utf-8").read()
    a, b = s.find(START), s.find(END)
    if a < 0 or b < 0:
        sys.exit("Penanda %s ... %s tidak ditemukan di %s" % (START, END, html))

    m = re.search(r'const MEMBER_SALT = "([^"]+)"', s[a:b])
    salt = m.group(1) if m else secrets.token_urlsafe(18)

    anggota = baca_excel(xlsx)
    enc = enkripsi(anggota, salt)
    blok = (
        START + "\n"
        "// Daftar anggota terenkripsi. Dibuat otomatis oleh update_anggota.py, jangan diubah manual.\n"
        'const MEMBER_SALT = "%s";\n'
        "const MEMBER_ITER = %d;\n"
        "const MEMBERS_ENC = %s;\n"
        % (salt, ITER, json.dumps(enc, separators=(",", ":")))
        + END
    )
    s = s[:a] + blok + s[b + len(END):]
    open(html, "w", encoding="utf-8").write(s)
    print("Selesai: %d anggota ditulis ke %s" % (len(enc), html))


if __name__ == "__main__":
    main()
