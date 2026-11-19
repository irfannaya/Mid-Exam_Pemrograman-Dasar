"""Skenario debugging: versi AWAL rekap harian (bug) dan versi PERBAIKAN."""

def rekap_harian_buggy(transaksi):
    per_hari = {}
    for t in transaksi:
        per_hari[t["tanggal"]]["omzet"] += t["nilai"]     # BUG: kunci tanggal belum ada
    return per_hari

def rekap_harian_fixed(transaksi):
    per_hari = {}
    for t in transaksi:
        hari = per_hari.setdefault(t["tanggal"], {"omzet": 0})   # FIX: buat entri awal dulu
        hari["omzet"] += t["nilai"]
    return per_hari

if __name__ == "__main__":
    data = [{"tanggal": "2026-10-01", "nilai": 65000}, {"tanggal": "2026-10-01", "nilai": 17000}]
    print("FIXED :", rekap_harian_fixed(data))
    print("BUGGY :", end=" ")
    rekap_harian_buggy(data)
