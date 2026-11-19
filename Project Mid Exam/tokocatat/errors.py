"""Exception khusus agar penanganan error spesifik dan mudah dibaca."""


class TokoError(Exception):
    """Kelas dasar semua error aplikasi."""


class DataFileError(TokoError):
    """File tidak ditemukan, tidak terbaca, kosong, atau kolom wajib hilang."""


class DataFormatError(TokoError):
    """Satu baris data tidak valid. Menyimpan sumber dan nomor baris."""

    def __init__(self, sumber, line_no, message):
        self.sumber = sumber
        self.line_no = line_no
        self.message = message
        super().__init__(f"{sumber} baris {line_no}: {message}")
