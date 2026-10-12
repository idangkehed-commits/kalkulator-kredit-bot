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
    if 0 < limit <= 500:
        limit = limit * 1_000_000.0

    if "KUR" in jenis:
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
    elif "KUM" in jenis:
        if limit <= 100_000_000:
            biaya = 0.01 * limit
            ket = "1% dari limit pengajuan (s/d 100jt)"
        else:
            biaya = 0.015 * limit
            ket = "1.5% dari limit pengajuan (> 100jt)"
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
    if 0 < limit <= 500:
        limit = limit * 1_000_000.0
    if "KUR" in jenis:
        if limit > 100_000_000:
            return True, "Dibebankan (KUR > 100jt)"
        else:
            return False, "Tidak dibebankan (KUR <= 100jt)"
    elif "KUM" in jenis:
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
        4. Premi Final menggunakan Premi Dasar (tanpa diskon 18%).
        """
        if 0 < limit <= 500:
            limit = limit * 1_000_000.0

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

        # Menggunakan Premi Dasar murni (tanpa diskon 18%)
        premi_final = premi_dasar
        ket = f"Rp {premi_final:,} (Rate: {prorated_rate:.2f}‰)".replace(",", ".")

        return float(premi_final), ket

    def hitung_asuransi_kerugian(
        self,
        jenis_kredit: str,
        limit: float,
        tenor_bulan: int,
        jenis_objek: str = "kebakaran",
        nilai_pertanggungan: Optional[float] = None,
        filepath: Optional[str] = None
    ) -> Tuple[float, str]:
        """
        Menghitung Asuransi Kerugian berdasarkan kalkulator AXA MyBiz Mikro:
        - Syarat pembebanan:
            KUR: di atas 100jt (> 100jt)
            KUM: di 50jt ke atas (>= 50jt)
        - Basis nilai pertanggungan:
            Mendukung nominal pertanggungan khusus (sum insured / nilai cover objek yang diasuransikan).
            Jika tidak diisi atau 0, default menggunakan limit pengajuan.
        - Pilihan Agunan (jenis_objek):
            1. 'kebakaran': FLEXAS Bangunan / Rumah Tinggal Kelas 1
               Rate dasar: 0.294 ‰ per tahun
               Formula: (tenor / 12) * (basis_nilai * 0.294 / 1000)
            2. 'kendaraan_mobil' / 'mobil': TLO Kendaraan Roda 4 (Passenger Car) OJK Zone 2
               Rate tahunan sesuai bracket OJK (0.65% s/d 0.20%)
               Formula: (tenor / 12) * (basis_nilai * rate_ojk / 100)
            3. 'kendaraan_motor' / 'motor': TLO Sepeda Motor Roda 2/3 OJK Zone 2
               Rate tahunan: 1.80%
               Formula: (tenor / 12) * (basis_nilai * 1.80 / 100)
            4. 'kendaraan_truk' / 'truk': TLO Truk / Pick Up OJK Zone 2
               Rate tahunan: 1.68%
               Formula: (tenor / 12) * (basis_nilai * 1.68 / 100)
        - Catatan Biaya Polis dan Materai: DIHILANGKAN (Rp 0) sesuai instruksi pengguna.
        """
        if 0 < limit <= 500:
            limit = limit * 1_000_000.0

        dibebankan, alasan = is_asuransi_kerugian_dibebankan(jenis_kredit, limit)
        if not dibebankan:
            return 0.0, alasan

        if nilai_pertanggungan is not None and 0 < float(nilai_pertanggungan) <= 500:
            nilai_pertanggungan = float(nilai_pertanggungan) * 1_000_000.0

        basis_nilai = float(nilai_pertanggungan) if (nilai_pertanggungan is not None and float(nilai_pertanggungan) > 0) else limit
        tenor_tahun = tenor_bulan / 12.0
        objek = str(jenis_objek or "kebakaran").strip().lower()

        if "motor" in objek:
            # TLO Sepeda Motor (Roda 2/3) - 1.80% per tahun
            rate_tahunan = 1.80
            rate_total = round(rate_tahunan * tenor_tahun, 3)
            premi = round(basis_nilai * (rate_total / 100.0))
            ket = f"Rp {premi:,} (TLO Motor, Cover: {format_rupiah(basis_nilai)}, Rate: {rate_total:.2f}%)".replace(",", ".")
            return float(premi), ket

        elif "truk" in objek or "truck" in objek or "pickup" in objek or "pick_up" in objek:
            # TLO Truk / Pick Up - 1.68% per tahun
            rate_tahunan = 1.68
            rate_total = round(rate_tahunan * tenor_tahun, 3)
            premi = round(basis_nilai * (rate_total / 100.0))
            ket = f"Rp {premi:,} (TLO Truk/Pick Up, Cover: {format_rupiah(basis_nilai)}, Rate: {rate_total:.2f}%)".replace(",", ".")
            return float(premi), ket

        elif "mobil" in objek or "car" in objek or "kendaraan" in objek:
            # TLO Kendaraan Roda 4 Passenger Car OJK Zone 2 (Bracket rate dihitung dari nilai pertanggungan kendaraan)
            if basis_nilai <= 125_000_000:
                rate_tahunan = 0.65
            elif basis_nilai <= 200_000_000:
                rate_tahunan = 0.44
            elif basis_nilai <= 400_000_000:
                rate_tahunan = 0.38
            elif basis_nilai <= 800_000_000:
                rate_tahunan = 0.25
            else:
                rate_tahunan = 0.20
            rate_total = round(rate_tahunan * tenor_tahun, 3)
            premi = round(basis_nilai * (rate_total / 100.0))
            ket = f"Rp {premi:,} (TLO Mobil Pribadi, Cover: {format_rupiah(basis_nilai)}, Rate: {rate_total:.2f}%)".replace(",", ".")
            return float(premi), ket

        else:
            # Default: Kebakaran (FLEXAS) Rumah Tinggal Konstruksi Kelas 1 (0.294 ‰)
            rate_flexas = 0.294
            rate_total = round(rate_flexas * tenor_tahun, 4)
            premi = round(tenor_tahun * (basis_nilai * rate_flexas / 1000.0))
            ket = f"Rp {premi:,} (FLEXAS Kebakaran, Cover: {format_rupiah(basis_nilai)}, Rate: {rate_total:.3f}‰)".replace(",", ".")
            return float(premi), ket


def kalkulasi_lengkap(data_pengajuan: Dict[str, Any], excel_reader: Optional[ExcelInsuranceReader] = None) -> Dict[str, Any]:
    """Melakukan kalkulasi menyeluruh dan mengembalikan objek hasil perhitungan."""
    if excel_reader is None:
        excel_reader = ExcelInsuranceReader()

    jenis_input = str(data_pengajuan.get("jenis_kredit", "KUR")).strip()
    jenis_upper = jenis_input.upper()

    is_topup = "TOP UP" in jenis_upper or "TOPUP" in jenis_upper or bool(data_pengajuan.get("is_topup", False))
    base_jenis = "KUR" if "KUR" in jenis_upper else "KUM"

    sisa_bade = float(data_pengajuan.get("sisa_bade", 0.0))
    if 0 < sisa_bade <= 500:
        sisa_bade = sisa_bade * 1_000_000.0

    limit = float(data_pengajuan.get("limit", 0))
    if 0 < limit <= 500:
        limit = limit * 1_000_000.0

    tenor = int(data_pengajuan.get("tenor", 12))
    bunga = float(data_pengajuan.get("bunga", 6.0))
    tipe_bunga = data_pengajuan.get("tipe_bunga", "efektif").lower()
    tgl_lahir = data_pengajuan.get("tanggal_lahir")
    nama = data_pengajuan.get("nama", "Calon Debitur")
    biaya_notaris = float(data_pengajuan.get("biaya_notaris", 0.0))
    jenis_kerugian = str(data_pengajuan.get("jenis_kerugian") or data_pengajuan.get("agunan_kerugian") or "kebakaran").lower()

    nominal_cover = data_pengajuan.get("nilai_pertanggungan") or data_pengajuan.get("nominal_kerugian") or data_pengajuan.get("cover_kerugian")
    if nominal_cover is not None and 0 < float(nominal_cover) <= 500:
        nominal_cover = float(nominal_cover) * 1_000_000.0
    nilai_pertanggungan = float(nominal_cover) if (nominal_cover is not None and float(nominal_cover) > 0) else limit

    # Hitung umur
    umur = hitung_umur(tgl_lahir) if isinstance(tgl_lahir, (date, datetime)) else int(data_pengajuan.get("umur", 30))

    # Hitung Angsuran berdasarkan base_jenis
    if base_jenis == "KUR":
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
    biaya_admin, ket_admin = hitung_admin_provisi(base_jenis, limit)

    # 2. Asuransi Jiwa Kredit (otomatis dari Excel)
    biaya_jiwa, ket_jiwa = excel_reader.hitung_asuransi_jiwa(umur, tenor, limit)

    # 3. Asuransi Kerugian (otomatis dari AXA MyBiz Mikro tanpa polis dan materai, dengan nominal cover yang dipilih)
    biaya_kerugian, ket_kerugian = excel_reader.hitung_asuransi_kerugian(
        base_jenis, limit, tenor, jenis_objek=jenis_kerugian, nilai_pertanggungan=nilai_pertanggungan
    )

    # 4. Biaya Notaris (input manual)
    ket_notaris = "Input manual"

    # 5. Asuransi Sijitu (otomatis usia)
    biaya_sijitu, ket_sijitu = hitung_asuransi_sijitu(umur)

    # 6. BPJSTK (khusus KUR > 100jt jika tidak punya kartu)
    punya_bpjstk = data_pengajuan.get("punya_bpjstk")
    biaya_bpjstk_in = float(data_pengajuan.get("biaya_bpjstk", 0.0))

    if base_jenis == "KUR" and limit > 100_000_000:
        if punya_bpjstk is False or biaya_bpjstk_in > 0:
            biaya_bpjstk = 170_000.0
            ket_bpjstk = "Rp 170.000 (Tidak punya kartu BPJSTK)"
        elif punya_bpjstk is True:
            biaya_bpjstk = 0.0
            ket_bpjstk = "Rp 0 (Sudah punya kartu BPJSTK)"
        else:
            biaya_bpjstk = 0.0
            ket_bpjstk = "Rp 0"
    else:
        biaya_bpjstk = 0.0
        ket_bpjstk = "Rp 0"

    # Blokir 2x Angsuran (ditempatkan pada Perhitungan Penerimaan Bersih)
    biaya_blokir = float(round(2 * angsuran))
    ket_blokir = f"2 x {format_rupiah(angsuran)}"

    # Total Biaya (Biaya operasional & premi yang harus disiapkan)
    total_biaya = biaya_admin + biaya_jiwa + biaya_kerugian + biaya_notaris + biaya_sijitu + biaya_bpjstk

    # Perhitungan Penerimaan Bersih: Limit - (Sisa Bade) - Total Biaya - Blokir 2x Angsuran
    dana_cair_bersih = limit - sisa_bade - total_biaya - biaya_blokir if is_topup else (limit - total_biaya - biaya_blokir)
    jenis_label = f"Top Up {base_jenis}" if is_topup else base_jenis

    return {
        "jenis_kredit": jenis_label,
        "base_jenis": base_jenis,
        "is_topup": is_topup,
        "sisa_bade": sisa_bade,
        "dana_cair_bersih": dana_cair_bersih,
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
        "jenis_kerugian": jenis_kerugian,
        "nilai_pertanggungan": nilai_pertanggungan,
        "biaya_notaris": biaya_notaris,
        "ket_notaris": ket_notaris,
        "biaya_sijitu": biaya_sijitu,
        "ket_sijitu": ket_sijitu,
        "biaya_bpjstk": biaya_bpjstk,
        "ket_bpjstk": ket_bpjstk,
        "punya_bpjstk": punya_bpjstk,
        "biaya_blokir": biaya_blokir,
        "ket_blokir": ket_blokir,
        "total_biaya": total_biaya
    }


def format_rupiah(angka: float) -> str:
    """Format angka integer/float ke format Rupiah standar Indonesia."""
    return f"Rp {int(round(angka)):,}".replace(",", ".")


def generate_hasil_teks(hasil: Dict[str, Any]) -> str:
    """
    Format hasil teks sesuai instruksi:
    Baris pertama: **Pengajuan [KUR/KUM/Top Up KUM] limit [nominal] tenor [n] bulan**
    Baris kedua: Angsuran: Rp ...
    Baris ketiga dst: Rincian biaya-biaya
    Setelah Total Biaya Disiapkan: Perhitungan Penerimaan Bersih (termasuk Blokir 2x Angsuran)
    """
    limit_fmt = f"{int(hasil['limit']):,}".replace(",", ".")
    angsuran_fmt = format_rupiah(hasil['angsuran'])
    admin_fmt = format_rupiah(hasil['biaya_admin'])
    jiwa_fmt = format_rupiah(hasil['biaya_jiwa'])
    if "Diskon" in hasil.get('ket_jiwa', ''):
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
    ]

    if hasil.get("biaya_bpjstk", 0) > 0:
        lines.append(f"6. BPJSTK                : {format_rupiah(hasil['biaya_bpjstk'])}")
    elif hasil.get("base_jenis") == "KUR" and hasil.get("limit", 0) > 100_000_000 and hasil.get("punya_bpjstk") is True:
        lines.append("6. BPJSTK                : Rp 0 (Sudah punya kartu)")

    lines.extend([
        "----------------------------------------------------------------------",
        f"Total Biaya yang Disiapkan : {total_fmt}*",
        f"*(Catatan: Calon Debitur: {hasil['nama']}, Umur: {hasil['umur']} tahun)"
    ])

    blokir_fmt = format_rupiah(hasil.get("biaya_blokir", 0))

    if hasil.get("is_topup"):
        sisa_bade_fmt = format_rupiah(hasil.get("sisa_bade", 0))
        dana_cair_fmt = format_rupiah(hasil.get("dana_cair_bersih", 0))
        lines.extend([
            "----------------------------------------------------------------------",
            "Perhitungan Penerimaan Bersih (Top Up):",
            f"- Limit Pengajuan Baru      : Rp {limit_fmt}",
            f"- Sisa Pokok / Bade Hutang  : {sisa_bade_fmt}",
            f"- Total Biaya Disiapkan     : {total_fmt}",
            f"- Blokir 2x Angsuran        : {blokir_fmt} ({hasil.get('ket_blokir', '')})",
            "----------------------------------------------------------------------",
            f"Estimasi Dana Diterima Bersih : {dana_cair_fmt}"
        ])
    else:
        dana_cair_fmt = format_rupiah(hasil.get("dana_cair_bersih", 0))
        lines.extend([
            "----------------------------------------------------------------------",
            "Perhitungan Penerimaan Bersih:",
            f"- Limit Pengajuan (Plafond) : Rp {limit_fmt}",
            f"- Total Biaya Disiapkan     : {total_fmt}",
            f"- Blokir 2x Angsuran        : {blokir_fmt} ({hasil.get('ket_blokir', '')})",
            "----------------------------------------------------------------------",
            f"Estimasi Dana Diterima Bersih : {dana_cair_fmt}"
        ])

    return "\n".join(lines)
