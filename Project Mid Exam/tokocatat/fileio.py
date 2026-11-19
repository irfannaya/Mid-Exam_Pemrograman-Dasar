"""Baca dan tulis file CSV / JSON (single responsibility: I/O file)."""

import csv
import json
import os

from .errors import DataFileError, DataFormatError
from .validator import KOLOM_BARANG, KOLOM_TRANSAKSI, parse_barang, parse_transaksi


def baca_csv(path, kolom_wajib):
    """Baca CSV mentah menjadi list pasangan (nomor_baris, dict).

    Raises:
        DataFileError: file tidak ada/izin ditolak/encoding salah/kosong/kolom kurang.
    """
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise DataFileError(f"File '{path}' kosong (tidak ada header).")
            hilang = [k for k in kolom_wajib if k not in reader.fieldnames]
            if hilang:
                raise DataFileError(f"Kolom wajib tidak ada di '{path}': {', '.join(hilang)}")
            # baris data pertama adalah baris ke-2 (baris 1 = header)
            return list(enumerate(reader, start=2))
    except FileNotFoundError:
        raise DataFileError(f"File tidak ditemukan: '{path}'") from None
    except PermissionError:
        raise DataFileError(f"Tidak punya izin membaca: '{path}'") from None
    except UnicodeDecodeError:
        raise DataFileError(f"Encoding '{path}' bukan UTF-8.") from None


def baca_barang(path):
    """Baca master barang.

    Returns:
        tuple[dict, list[str]]: ({kode: barang}, daftar pesan error).
        Kode ganda: baris pertama dipakai, sisanya ditolak.
    """
    sumber = os.path.basename(path)
    daftar, error = {}, []
    for no, row in baca_csv(path, KOLOM_BARANG):
        try:
            barang = parse_barang(row, no, sumber)
        except DataFormatError as exc:
            error.append(str(exc))
            continue
        if barang["kode"] in daftar:
            error.append(str(DataFormatError(sumber, no, f"kode '{barang['kode']}' ganda")))
        else:
            daftar[barang["kode"]] = barang
    return daftar, error


def baca_transaksi(path):
    """Baca transaksi. Returns: tuple[list[dict], list[str]] (valid, error)."""
    sumber = os.path.basename(path)
    valid, error = [], []
    for no, row in baca_csv(path, KOLOM_TRANSAKSI):
        try:
            valid.append(parse_transaksi(row, no, sumber))
        except DataFormatError as exc:
            error.append(str(exc))
    return valid, error


def _pastikan_folder(path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def tambah_transaksi(path, trx):
    """Tambahkan satu transaksi di akhir file CSV transaksi (append).

    Args:
        path (str): file transaksi yang sudah ada.
        trx (dict): transaksi yang sudah tervalidasi.
    """
    try:
        with open(path, "rb") as fh:                 # defensif: pastikan file berakhir baris baru
            fh.seek(0, os.SEEK_END)
            perlu_newline = fh.tell() > 0 and (fh.seek(-1, os.SEEK_END) or fh.read(1)) != b"\n"
        with open(path, "a", newline="", encoding="utf-8") as fh:
            if perlu_newline:
                fh.write("\n")
            csv.DictWriter(fh, fieldnames=KOLOM_TRANSAKSI, lineterminator="\n").writerow(
                {k: trx[k] for k in KOLOM_TRANSAKSI})
    except PermissionError:
        raise DataFileError(f"Tidak punya izin menulis: '{path}'") from None


def tulis_csv(path, baris, kolom):
    """Simpan list of dict ke CSV dengan header `kolom`."""
    _pastikan_folder(path)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=kolom, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(baris)


def tulis_json(path, data):
    """Simpan data ke JSON (UTF-8, indent 2)."""
    _pastikan_folder(path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def tulis_teks(path, teks):
    """Simpan teks ke file."""
    _pastikan_folder(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(teks)
