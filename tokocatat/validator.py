"""Validasi dan normalisasi satu baris data (single responsibility: validasi)."""

from datetime import datetime

from .errors import DataFormatError

KOLOM_BARANG = ("kode", "nama", "kategori", "harga_beli",
                "harga_jual", "stok", "stok_minimum")
KOLOM_TRANSAKSI = ("id", "tanggal", "kode_barang", "jenis", "jumlah")
JENIS_VALID = {"JUAL", "BELI"}
FORMAT_TANGGAL = "%Y-%m-%d"


def ambil_teks(row, kolom, sumber, no):
    """Ambil nilai kolom sebagai teks bersih.

    Args:
        row (dict): data mentah satu baris.
        kolom (str): nama kolom.
        sumber (str): label file (untuk pesan error).
        no (int): nomor baris.
    Returns:
        str: teks tanpa spasi di tepi.
    Raises:
        DataFormatError: bila kolom kosong.
    """
    nilai = row.get(kolom)
    teks = "" if nilai is None else str(nilai).strip()
    if not teks:
        raise DataFormatError(sumber, no, f"kolom '{kolom}' kosong")
    return teks


def ambil_int(row, kolom, minimum, sumber, no):
    """Ambil kolom sebagai bilangan bulat >= minimum.

    Raises:
        DataFormatError: bila bukan angka bulat atau kurang dari minimum.
    """
    teks = ambil_teks(row, kolom, sumber, no)
    try:
        angka = int(teks)
    except ValueError:
        raise DataFormatError(sumber, no, f"'{kolom}' harus angka bulat, bukan '{teks}'") from None
    if angka < minimum:
        raise DataFormatError(sumber, no, f"'{kolom}' minimal {minimum}, bukan {angka}")
    return angka


def validasi_tanggal(teks, sumber, no):
    """Pastikan tanggal berformat YYYY-MM-DD dan benar-benar ada di kalender."""
    try:
        datetime.strptime(teks, FORMAT_TANGGAL)
    except ValueError:
        raise DataFormatError(sumber, no, f"tanggal tidak valid: '{teks}'") from None
    return teks


def parse_barang(row, no, sumber="barang.csv"):
    """Validasi satu baris master barang.

    Returns:
        dict: barang bersih (harga & stok bertipe int).
    Raises:
        DataFormatError: bila ada nilai tidak valid atau harga jual < harga beli.
    """
    barang = {
        "kode": ambil_teks(row, "kode", sumber, no).upper(),
        "nama": ambil_teks(row, "nama", sumber, no),
        "kategori": ambil_teks(row, "kategori", sumber, no),
        "harga_beli": ambil_int(row, "harga_beli", 1, sumber, no),
        "harga_jual": ambil_int(row, "harga_jual", 1, sumber, no),
        "stok": ambil_int(row, "stok", 0, sumber, no),
        "stok_minimum": ambil_int(row, "stok_minimum", 0, sumber, no),
    }
    if barang["harga_jual"] < barang["harga_beli"]:
        raise DataFormatError(sumber, no, "harga jual lebih kecil dari harga beli")
    return barang


def parse_transaksi(row, no, sumber="transaksi.csv"):
    """Validasi satu baris transaksi.

    Returns:
        dict: transaksi bersih (jenis huruf besar, jumlah int > 0).
    Raises:
        DataFormatError: bila tanggal/jenis/jumlah tidak valid.
    """
    jenis = ambil_teks(row, "jenis", sumber, no).upper()
    if jenis not in JENIS_VALID:
        raise DataFormatError(
            sumber, no, f"jenis '{jenis}' tidak dikenal (valid: {', '.join(sorted(JENIS_VALID))})")
    return {
        "id": ambil_teks(row, "id", sumber, no).upper(),
        "tanggal": validasi_tanggal(ambil_teks(row, "tanggal", sumber, no), sumber, no),
        "kode_barang": ambil_teks(row, "kode_barang", sumber, no).upper(),
        "jenis": jenis,
        "jumlah": ambil_int(row, "jumlah", 1, sumber, no),
    }
