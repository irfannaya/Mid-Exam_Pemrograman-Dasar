"""Logika bisnis toko (single responsibility: pengolahan data murni, tanpa I/O).

Struktur data yang dipakai:
    list : daftar transaksi (urutan waktu penting, mudah diurutkan/di-slice)
    dict : master barang {kode: data}, stok {kode: jumlah}, rekap per hari/kategori
    set  : kumpulan ID transaksi yang sudah dilihat (deteksi duplikat O(1))
"""

import re

from .errors import DataFormatError
from .validator import JENIS_VALID, validasi_tanggal


def hapus_duplikat_id(transaksi):
    """Buang transaksi dengan ID yang sama (yang pertama dipertahankan).

    Returns:
        tuple[list[dict], int]: (transaksi unik, jumlah duplikat dibuang).
    """
    terlihat = set()                    # SET: ID yang sudah muncul
    unik = []                           # LIST: hasil, urutan terjaga
    for t in transaksi:
        if t["id"] not in terlihat:
            terlihat.add(t["id"])
            unik.append(t)
    return unik, len(transaksi) - len(unik)


def proses_transaksi(barang, transaksi):
    """Putar ulang transaksi berurutan waktu untuk menghitung stok akhir.

    JUAL mengurangi stok (nilai = omzet, modal = HPP); BELI menambah stok
    (nilai = modal = pengeluaran belanja). Transaksi yang melanggar aturan
    ditolak dan dicatat alasannya, bukan menghentikan program.

    Args:
        barang (dict): {kode: data barang}.
        transaksi (list[dict]): transaksi bersih.
    Returns:
        tuple: (stok_akhir dict, transaksi_sah list, ditolak list[str]).
    """
    stok = {kode: b["stok"] for kode, b in barang.items()}   # DICT COMPREHENSION
    sah, ditolak = [], []
    for t in sorted(transaksi, key=lambda x: (x["tanggal"], x["id"])):
        kode = t["kode_barang"]
        if kode not in barang:
            ditolak.append(f"{t['id']}: kode barang '{kode}' tidak terdaftar")
            continue
        if t["jenis"] == "JUAL":
            if t["jumlah"] > stok[kode]:
                ditolak.append(f"{t['id']}: stok {kode} tidak cukup "
                               f"(tersedia {stok[kode]}, diminta {t['jumlah']})")
                continue
            stok[kode] -= t["jumlah"]
            nilai = t["jumlah"] * barang[kode]["harga_jual"]
            modal = t["jumlah"] * barang[kode]["harga_beli"]
        else:  # BELI
            stok[kode] += t["jumlah"]
            nilai = modal = t["jumlah"] * barang[kode]["harga_beli"]
        sah.append({**t, "nilai": nilai, "modal": modal})
    return stok, sah, ditolak


def hitung_keuangan(sah, barang):
    """Hitung ringkasan keuangan dari transaksi sah.

    Returns:
        dict: omzet, hpp, laba_kotor, belanja, margin (%), per_hari, per_kategori.
    """
    penjualan = [t for t in sah if t["jenis"] == "JUAL"]
    omzet = sum(t["nilai"] for t in penjualan)
    hpp = sum(t["modal"] for t in penjualan)
    belanja = sum(t["nilai"] for t in sah if t["jenis"] == "BELI")

    per_hari, per_kategori = {}, {}
    for t in sah:
        hari = per_hari.setdefault(t["tanggal"], {"omzet": 0, "laba": 0, "belanja": 0})
        if t["jenis"] == "JUAL":
            hari["omzet"] += t["nilai"]
            hari["laba"] += t["nilai"] - t["modal"]
            kat = barang[t["kode_barang"]]["kategori"]
            per_kategori[kat] = per_kategori.get(kat, 0) + t["nilai"]
        else:
            hari["belanja"] += t["nilai"]

    return {
        "omzet": omzet, "hpp": hpp, "laba_kotor": omzet - hpp, "belanja": belanja,
        "margin": round((omzet - hpp) / omzet * 100, 1) if omzet else 0.0,   # hindari bagi nol
        "per_hari": dict(sorted(per_hari.items())),
        "per_kategori": per_kategori,
    }


def nilai_stok(barang, stok):
    """Total nilai persediaan = jumlah stok x harga beli."""
    return sum(stok[k] * b["harga_beli"] for k, b in barang.items())


def status_stok(jumlah, minimum):
    """Kembalikan 'HABIS', 'MENIPIS', atau 'AMAN' (percabangan)."""
    if jumlah == 0:
        return "HABIS"
    elif jumlah <= minimum:
        return "MENIPIS"
    return "AMAN"


def daftar_stok(barang, stok):
    """Gabungkan master barang dan stok akhir menjadi list baris laporan."""
    return [{**b, "stok": stok[k], "status": status_stok(stok[k], b["stok_minimum"])}
            for k, b in barang.items()]                       # LIST COMPREHENSION


def stok_menipis(barang, stok):
    """Barang yang stoknya <= batas minimum, diurutkan dari paling sedikit."""
    return sorted((r for r in daftar_stok(barang, stok) if r["status"] != "AMAN"),
                  key=lambda r: (r["stok"], r["kode"]))


def hitung_terjual(sah):
    """Total unit terjual per kode barang -> dict {kode: unit}."""
    hasil = {}
    for t in sah:
        if t["jenis"] == "JUAL":
            hasil[t["kode_barang"]] = hasil.get(t["kode_barang"], 0) + t["jumlah"]
    return hasil


def terlaris(sah, n=3):
    """n barang paling banyak terjual. n <= 0 -> list kosong (edge case)."""
    if n <= 0:
        return []
    return sorted(hitung_terjual(sah).items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def cari_barang(barang, kata):
    """Cari kata kunci (kode/nama/kategori, tidak peka huruf besar-kecil)."""
    kata = kata.strip().lower()
    if not kata:
        return []
    return [b for b in barang.values()
            if any(kata in str(b[k]).lower() for k in ("kode", "nama", "kategori"))]


def filter_transaksi(sah, jenis=None, tanggal_awal=None, tanggal_akhir=None, kode=None):
    """Filter transaksi; kriteria None diabaikan.

    Raises:
        ValueError: bila jenis tidak valid atau format tanggal salah.
    """
    if jenis is not None:
        jenis = jenis.upper()
        if jenis not in JENIS_VALID:
            raise ValueError(f"jenis harus JUAL atau BELI, bukan '{jenis}'")
    for tgl in (tanggal_awal, tanggal_akhir):
        if tgl is not None:
            try:
                validasi_tanggal(tgl, "argumen", 0)
            except DataFormatError:
                raise ValueError(f"tanggal harus YYYY-MM-DD, bukan '{tgl}'") from None
    kode = kode.upper() if kode else None
    return [t for t in sah
            if (jenis is None or t["jenis"] == jenis)
            and (tanggal_awal is None or t["tanggal"] >= tanggal_awal)
            and (tanggal_akhir is None or t["tanggal"] <= tanggal_akhir)
            and (kode is None or t["kode_barang"] == kode)]


def id_baru(transaksi):
    """Buat ID transaksi berikutnya, mis. T035 -> T036."""
    angka = [int(t["id"][1:]) for t in transaksi if re.fullmatch(r"T\d+", t["id"])]
    return f"T{max(angka, default=0) + 1:03d}"


def periksa_transaksi_baru(barang, stok, kode, jenis, jumlah):
    """Defensive check sebelum mencatat transaksi baru.

    Returns:
        tuple[str, str]: (kode, jenis) yang sudah dinormalkan.
    Raises:
        ValueError: kode tidak terdaftar, jenis salah, jumlah < 1, atau stok kurang.
    """
    kode, jenis = kode.strip().upper(), jenis.strip().upper()
    if kode not in barang:
        raise ValueError(f"kode barang '{kode}' tidak terdaftar")
    if jenis not in JENIS_VALID:
        raise ValueError("jenis harus JUAL atau BELI")
    if jumlah < 1:
        raise ValueError("jumlah minimal 1")
    if jenis == "JUAL" and jumlah > stok[kode]:
        raise ValueError(f"stok {kode} tidak cukup (tersedia {stok[kode]})")
    return kode, jenis
