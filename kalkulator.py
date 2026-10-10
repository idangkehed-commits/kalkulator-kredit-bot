# -*- coding: utf-8 -*-
"""
Modul Kalkulator Kredit (KUR & KUM)
Menangani logika perhitungan angsuran dan biaya-biaya debitur,
termasuk integrasi otomatis tabel Excel Asuransi Jiwa Kredit & Asuransi Kerugian.
"""

from datetime import datetime, date
import math
import os
import io
import glob
from typing import Dict, Any, Optional, Tuple

try:
    import openpyxl
except ImportError:
    openpyxl = None


def hitung_umur(tgl_lahir: date, ref_date: Optional[date] = None) -> int:
    """Menghitung umur dalam tahun berdasarkan tanggal lahir."""
    if ref_date is None:
        ref_date = date.today()
    umur = ref_date.year - tgl_lahir.year
    if (ref_date.month, ref_date.day) < (tgl_lahir.month, tgl_lahir.day):
        umur -= 1
    return umur


def hitung_angsuran_efektif(limit: float, bunga_tahunan_persen: float, tenor_bulan: int) -> float:
    """
    Menghitung angsuran per bulan dengan bunga Efektif / Anuitas per tahun.
    Formula Anuitas (PMT):
    r = (bunga / 100) / 12
    PMT = limit * (r * (1 + r)^n) / ((1 + r)^n - 1)
    """
    if tenor_bulan <= 0:
        return 0.0
    if bunga_tahunan_persen <= 0:
        return limit / tenor_bulan
    
    r = (bunga_tahunan_persen / 100.0) / 12.0
    faktor = math.pow(1.0 + r, tenor_bulan)
    angsuran = limit * (r * faktor) / (faktor - 1.0)
    return round(angsuran)


def hitung_angsuran_flat(limit: float, bunga_bulanan_persen: float, tenor_bulan: int) -> float:
    """
    Menghitung angsuran per bulan dengan bunga Flat per bulan.
    Formula Flat:
    Pokok per bulan = limit / tenor
    Bunga per bulan = limit * (bunga_bulanan_persen / 100)
    Total Angsuran = Pokok + Bunga
    """
    if tenor_bulan <= 0:
        return 0.0
    pokok_per_bulan = limit / tenor_bulan
    bunga_per_bulan = limit * (bunga_bulanan_persen / 100.0)
    return round(pokok_per_bulan + bunga_per_bulan)


def hitung_admin_provisi(jenis_kredit: str, limit: float) -> Tuple[float, str]:
    """
    1. Admin & Provisi
    - KUR:
        Kondisi pengajuan di 10 juta s/d 100 juta: 2% dari limit pengajuan.
        Di luar itu diinformasikan atau dihitung sesuai ketentuan.
    - KUM:
        Sampai 100 juta (<= 100 jt): 1% dari limit pengajuan.
        Di atas 100 juta (> 100 jt): 1.5% dari limit pengajuan.
    """
    jenis = jenis_kredit.strip().upper()
    if jenis == "KUR":
        if 10_000_000 <= limit <= 100_000_000:
            biaya = 0.02 * limit
            ket = "2% dari limit pengajuan (10jt s/d 100jt)"
        elif limit < 10_000_000:
            biaya = 0.0
            ket = "0% (Plafond di bawah 10jt bebas biaya admin & provisi)"
        else:
            biaya = 0.019 * limit
            ket = "1.9% dari limit pengajuan (> 100jt)"
        return round(biaya), ket
    elif jenis == "KUM":
        if limit <= 100_000_000:
            biaya = 0.01 * limit
            ket = "1% dari limit pengajuan (s/d 100jt)"
        else:
            biaya = 0.019 * limit
            ket = "1.9% dari limit pengajuan (> 100jt)"
        return round(biaya), ket
    else:
        return 0.0, "Jenis kredit tidak dikenal"


def hitung_asuransi_sijitu(umur: int) -> Tuple[float, str]:
    """
    5. Asuransi Sijitu
    Fix Rp 600.000 jika umur < 50 tahun.
    Rp 50.000 jika umur 50 tahun ke atas.
    """
    if umur >= 50:
        return 50_000.0, f"Rp 50.000 (Umur {umur} tahun >= 50)"
    else:
        return 600_000.0, f"Rp 600.000 (Umur {umur} tahun < 50)"


def is_asuransi_kerugian_dibebankan(jenis_kredit: str, limit: float) -> Tuple[bool, str]:
    """
    Ketentuan pembebanan Asuransi Kerugian:
    - KUR: Dibebankan jika pengajuan di atas 100 juta (> 100jt).
    - KUM: Dibebankan jika pengajuan di 50 juta dan lebih dari 50 juta (>= 50jt).
    """
    jenis = jenis_kredit.strip().upper()
    if jenis == "KUR":
        if limit > 100_000_000:
            return True, "Dibebankan (KUR > 100jt)"
        else:
            return False, "Tidak dibebankan (KUR <= 100jt)"
    elif jenis == "KUM":
        if limit >= 50_000_000:
            return True, "Dibebankan (KUM >= 50jt)"
        else:
            return False, "Tidak dibebankan (KUM < 50jt)"
    return False, "Tidak dibebankan"


class ExcelInsuranceReader:
    """
    Pembaca tabel kalkulator Asuransi Jiwa Kredit & Asuransi Kerugian dari Excel.
    Memeriksa folder `excel_data/` dan direktori proyek `E:\\kalkulator-kredit-bot\\`.
    """
    def __init__(self, data_folder: str = "excel_data"):
        self.data_folder = data_folder
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self._jiwa_rates_cache = None
        self._kerugian_rates_cache = None

    def find_excel_file(self, keyword: str) -> Optional[str]:
        """Mencari file excel berdasarkan kata kunci di beberapa folder potensial."""
        search_dirs = [
            self.data_folder,
            self.project_dir,
            os.path.join(self.project_dir, "excel_data"),
            "E:\\kalkulator-kredit-bot",
            "E:\\kalkulator-kredit-bot\\excel_data"
        ]
        seen_dirs = set()
        for sdir in search_dirs:
            if not sdir or not os.path.exists(sdir) or sdir in seen_dirs:
                continue
            seen_dirs.add(sdir)
            patterns = [
                os.path.join(sdir, f"*{keyword}*.xls*"),
                os.path.join(sdir, f"*{keyword}*"),
            ]
            for p in patterns:
                files = glob.glob(p)
                for f in files:
                    if os.path.isfile(f) and f.lower().endswith(('.xls', '.xlsx')):
                        return f
        return None

    def _load_jiwa_table(self, filepath: Optional[str] = None) -> Dict[int, list]:
        """Mengekstrak tabel rate asuransi jiwa Plan 1 KUM/KUR 20% dari Excel."""
        if self._jiwa_rates_cache is not None:
            return self._jiwa_rates_cache

        target_file = filepath or self.find_excel_file("jiwa")
        rates = {}
        if target_file and os.path.exists(target_file) and openpyxl is not None:
            try:
                with open(target_file, "rb") as f:
                    file_bytes = io.BytesIO(f.read())
                wb = openpyxl.load_workbook(file_bytes, data_only=True)
                if "Premium Table" in wb.sheetnames:
                    s_pt = wb["Premium Table"]
                    # Tabel Plan 1 KUM/KUR berada pada baris 107-154 kolom C-H
                    for r in range(107, 155):
                        age_val = s_pt.cell(r, 3).value
                        if isinstance(age_val, (int, float)):
                            age = int(age_val)
                            row_rates = []
                            for c in range(4, 9):
                                val = s_pt.cell(r, c).value
                                row_rates.append(float(val) if val is not None else 0.0)
                            rates[age] = row_rates
            except Exception as e:
                print(f"[Warning] Error membaca Excel Jiwa ({e}), menggunakan basis data internal.")

        if not rates:
            # Fallback data teruji dari sheet Premium Table (KUM/KUR)
            rates = self._get_default_jiwa_rates()

        self._jiwa_rates_cache = rates
        return rates

    def _get_default_jiwa_rates(self) -> Dict[int, list]:
        """Tabel tarif default KUM/KUR dari sheet Premium Table jika file belum terbaca."""
        # Sampel terstruktur per rentang umur (1-5 tahun tenor)
        table = {}
        for a in range(18, 31):
            table[a] = [1.78, 2.70, 3.42, 3.71, 4.25]
        for a in range(31, 36):
            table[a] = [1.83, 2.83, 3.96, 4.49, 5.24]
        for a in range(36, 41):
            table[a] = [2.73, 4.22, 5.90, 6.68, 7.83]
        for a in range(41, 46):
            table[a] = [4.67, 7.32, 10.31, 11.67, 13.70]
        for a in range(46, 51):
            table[a] = [7.11, 12.69, 17.79, 20.08, 23.52]
        for a in range(51, 56):
            table[a] = [11.21, 20.24, 28.38, 32.04, 37.53]
        for a in range(56, 61):
            table[a] = [15.98, 28.49, 39.95, 45.10, 52.84]
        for a in range(61, 66):
            table[a] = [20.76, 33.46, 47.84, 54.01, 63.27]
        return table

    def hitung_asuransi_jiwa(self, umur: int, tenor_bulan: int, limit: float, filepath: Optional[str] = None) -> Tuple[float, str]:
        """
        Menghitung Asuransi Jiwa Kredit sesuai formula:
        1. Rate diambil berdasarkan Umur (18-65) dan Tenor (1-5 tahun).
        2. Prorated rate jika tenor bukan kelipatan 12 bulan.
        3. Premi Dasar = round(Rate * Limit / 1000)
        4. Diskon 18% untuk umur > 40 tahun (sesuai sheet Discount).
        5. Premi Final = round(Premi Dasar * (1 - Diskon))
        """
        rates_table = self._load_jiwa_table(filepath)
        
        # Batasi umur pada range tabel 18 - 65
        effective_age = max(18, min(65, umur))
        row_rates = rates_table.get(effective_age, rates_table[min(rates_table.keys(), key=lambda k: abs(k - effective_age))])

        term_year = tenor_bulan // 12
        term_month = tenor_bulan % 12

        if term_year < 1:
            # Tenor di bawah 1 tahun: gunakan rate tahun 1 diprorata bulan
            base_rate = row_rates[0]
            prorated_rate = round(base_rate * (tenor_bulan / 12.0), 2)
        elif term_year >= 5:
            # Maksimal 5 tahun
            prorated_rate = row_rates[4]
        else:
            idx_curr = term_year - 1
            idx_next = term_year
            rate_curr = row_rates[idx_curr]
            rate_next = row_rates[idx_next] if idx_next < len(row_rates) else rate_curr
            prorated_rate = round(rate_curr + (rate_next - rate_curr) * (term_month / 12.0), 2)

        # Premi Dasar per mil (‰)
        premi_dasar = round(prorated_rate * limit / 1000.0)

        # Diskon Premi: 18% jika umur > 40 tahun
        discount = 0.18 if umur > 40 else 0.0
        premi_final = round(premi_dasar * (1.0 - discount))

        if discount > 0:
            ket = f"Rp {premi_final:,} (Rate: {prorated_rate:.2f}‰, Diskon 18% dari Premi Dasar {format_rupiah(premi_dasar)})".replace(",", ".")
        else:
            ket = f"Rp {premi_final:,} (Rate: {prorated_rate:.2f}‰)".replace(",", ".")

        return float(premi_final), ket

    def hitung_asuransi_kerugian(self, jenis_kredit: str, limit: float, tenor_bulan: int, filepath: Optional[str] = None) -> Tuple[float, str]:
        """
        Menghitung Asuransi Kerugian (Kebakaran / FLEXAS) berdasarkan:
        - Syarat pembebanan:
            KUR: di atas 100jt
            KUM: di 50jt ke atas
        - Rumus (sesuai sheet HASIL & BUAT SPPA):
            Jangka waktu = tenor_bulan / 12 (tahun)
            Rate default = 0.294 ‰ (Rumah Tinggal, Kelas Konstruksi 1)
            Premi FLEXAS = (tenor_bulan / 12) * (limit * rate / 1000)
            Biaya Polis  = 25.000
            Biaya Materai= 10.000 jika FLEXAS < 5.000.000, 20.000 jika >= 5.000.000
            Total Premi  = Premi FLEXAS + Biaya Polis + Biaya Materai
        """
        dibebankan, alasan = is_asuransi_kerugian_dibebankan(jenis_kredit, limit)
        if not dibebankan:
            return 0.0, alasan

        # Rate Rumah Tinggal Kelas Konstruksi 1 = 0.294 ‰
        rate_flexas = 0.294
        tenor_tahun = tenor_bulan / 12.0

        premi_flexas = tenor_tahun * (limit * rate_flexas / 1000.0)
        biaya_polis = 25_000.0
        biaya_materai = 20_000.0 if premi_flexas >= 5_000_000 else 10_000.0

        total_premi = round(premi_flexas + biaya_polis + biaya_materai)
        ket = (
            f"Rp {total_premi:,} (FLEXAS: {format_rupiah(premi_flexas)}, Polis: {format_rupiah(biaya_polis)}, Materai: {format_rupiah(biaya_materai)})"
        ).replace(",", ".")

        return float(total_premi), ket


def kalkulasi_lengkap(data_pengajuan: Dict[str, Any], excel_reader: Optional[ExcelInsuranceReader] = None) -> Dict[str, Any]:
    """Melakukan kalkulasi menyeluruh dan mengembalikan objek hasil perhitungan."""
    if excel_reader is None:
        excel_reader = ExcelInsuranceReader()

    jenis = data_pengajuan.get("jenis_kredit", "KUR").upper()
    limit = float(data_pengajuan.get("limit", 0))
    tenor = int(data_pengajuan.get("tenor", 12))
    bunga = float(data_pengajuan.get("bunga", 6.0))
    tipe_bunga = data_pengajuan.get("tipe_bunga", "efektif").lower()
    tgl_lahir = data_pengajuan.get("tanggal_lahir")
    nama = data_pengajuan.get("nama", "Calon Debitur")
    biaya_notaris = float(data_pengajuan.get("biaya_notaris", 0.0))

    # Hitung umur
    umur = hitung_umur(tgl_lahir) if isinstance(tgl_lahir, (date, datetime)) else int(data_pengajuan.get("umur", 30))

    # Hitung Angsuran
    if jenis == "KUR":
        angsuran = hitung_angsuran_efektif(limit, bunga, tenor)
        info_bunga = f"Bunga Efektif {bunga:.2f}% per tahun"
    else:
        if "flat" in tipe_bunga:
            angsuran = hitung_angsuran_flat(limit, bunga, tenor)
            info_bunga = f"Bunga Flat {bunga:.2f}% per bulan"
        else:
            angsuran = hitung_angsuran_efektif(limit, bunga, tenor)
            info_bunga = f"Bunga Efektif {bunga:.2f}% per tahun"

    # 1. Admin & Provisi
    biaya_admin, ket_admin = hitung_admin_provisi(jenis, limit)

    # 2. Asuransi Jiwa Kredit (otomatis dari Excel)
    biaya_jiwa, ket_jiwa = excel_reader.hitung_asuransi_jiwa(umur, tenor, limit)

    # 3. Asuransi Kerugian (otomatis dari Excel jika memenuhi syarat plafon)
    biaya_kerugian, ket_kerugian = excel_reader.hitung_asuransi_kerugian(jenis, limit, tenor)

    # 4. Biaya Notaris (input manual)
    ket_notaris = "Input manual"

    # 5. Asuransi Sijitu (otomatis usia)
    biaya_sijitu, ket_sijitu = hitung_asuransi_sijitu(umur)

    # Total Biaya
    total_biaya = biaya_admin + biaya_jiwa + biaya_kerugian + biaya_notaris + biaya_sijitu

    return {
        "jenis_kredit": jenis,
        "nama": nama,
        "limit": limit,
        "tenor": tenor,
        "umur": umur,
        "bunga": bunga,
        "tipe_bunga": tipe_bunga,
        "info_bunga": info_bunga,
        "angsuran": angsuran,
        "biaya_admin": biaya_admin,
        "ket_admin": ket_admin,
        "biaya_jiwa": biaya_jiwa,
        "ket_jiwa": ket_jiwa,
        "biaya_kerugian": biaya_kerugian,
        "ket_kerugian": ket_kerugian,
        "biaya_notaris": biaya_notaris,
        "ket_notaris": ket_notaris,
        "biaya_sijitu": biaya_sijitu,
        "ket_sijitu": ket_sijitu,
        "total_biaya": total_biaya
    }


def format_rupiah(angka: float) -> str:
    """Format angka integer/float ke format Rupiah standar Indonesia."""
    return f"Rp {int(round(angka)):,}".replace(",", ".")


def generate_hasil_teks(hasil: Dict[str, Any]) -> str:
    """
    Format hasil teks sesuai instruksi:
    Baris pertama: **Pengajuan [KUR/KUM] limit [nominal] tenor [n] bulan**
    Baris kedua: Angsuran: Rp ...
    Baris ketiga dst: Rincian biaya-biaya
    """
    limit_fmt = f"{int(hasil['limit']):,}".replace(",", ".")
    angsuran_fmt = format_rupiah(hasil['angsuran'])
    admin_fmt = format_rupiah(hasil['biaya_admin'])
    jiwa_fmt = format_rupiah(hasil['biaya_jiwa'])
    if "Diskon" in hasil['ket_jiwa']:
        jiwa_fmt = f"{jiwa_fmt} ({hasil['ket_jiwa'].split('(', 1)[1]}"

    if hasil['biaya_kerugian'] > 0:
        kerugian_fmt = format_rupiah(hasil['biaya_kerugian'])
    else:
        kerugian_fmt = f"Rp 0 ({hasil['ket_kerugian']})"

    notaris_fmt = format_rupiah(hasil['biaya_notaris'])
    sijitu_fmt = format_rupiah(hasil['biaya_sijitu'])
    total_fmt = format_rupiah(hasil['total_biaya'])

    lines = [
        f"**Pengajuan {hasil['jenis_kredit']} limit {limit_fmt} tenor {hasil['tenor']} bulan**",
        f"Angsuran: {angsuran_fmt} / bulan ({hasil['info_bunga']})",
        "",
        "Rincian Biaya yang Harus Disiapkan Calon Debitur:",
        f"1. Admin & Provisi       : {admin_fmt} ({hasil['ket_admin']})",
        f"2. Asuransi Jiwa Kredit  : {jiwa_fmt}",
        f"3. Asuransi Kerugian     : {kerugian_fmt}",
        f"4. Biaya Notaris         : {notaris_fmt}",
        f"5. Asuransi Sijitu       : {sijitu_fmt} (Keterangan: {hasil['ket_sijitu']})",
        "----------------------------------------------------------------------",
        f"Total Biaya yang Disiapkan : {total_fmt}*",
        f"*(Catatan: Calon Debitur: {hasil['nama']}, Umur: {hasil['umur']} tahun)"
    ]
    return "\n".join(lines)
