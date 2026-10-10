import sys
import re
from datetime import datetime, date
from typing import Optional

# Pastikan output konsol Windows mendukung UTF-8 jika tersedia
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stdin, 'reconfigure'):
    try:
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

from kalkulator import (
    kalkulasi_lengkap,
    generate_hasil_teks,
    hitung_umur,
    format_rupiah,
    ExcelInsuranceReader
)


def parse_nominal(text: str) -> Optional[float]:
    """Mengubah input teks seperti '110jt', '110.000.000', '110000000' menjadi float."""
    if not text:
        return None
    cleaned = text.strip().lower()
    
    # Handle singkatan 'jt' atau 'juta'
    if "jt" in cleaned or "juta" in cleaned:
        num_str = re.sub(r"[^\d.,]", "", cleaned)
        num_str = num_str.replace(",", ".")
        try:
            return float(num_str) * 1_000_000
        except ValueError:
            return None
            
    # Handle singkatan 'rb' atau 'ribu' atau 'k'
    if "rb" in cleaned or "ribu" in cleaned or cleaned.endswith("k"):
        num_str = re.sub(r"[^\d.,]", "", cleaned)
        num_str = num_str.replace(",", ".")
        try:
            return float(num_str) * 1_000
        except ValueError:
            return None

    # Handle angka standar dengan titik/koma ribuan
    # Jika ada titik sebagai pemisah ribuan
    num_str = cleaned.replace(".", "").replace(",", ".")
    num_str = re.sub(r"[^\d.]", "", num_str)
    try:
        return float(num_str)
    except ValueError:
        return None


def parse_persen(text: str) -> Optional[float]:
    """Mengubah teks persentase seperti '6%', '6.5', '7' menjadi float."""
    cleaned = text.strip().replace("%", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_tanggal(text: str) -> Optional[date]:
    """Mendukung format DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, dll."""
    cleaned = text.strip()
    formats = [
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %m %Y",
        "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.date()
        except ValueError:
            continue
    return None


def tanya_dengan_validasi(prompt_text: str, validator_fn, error_msg: str):
    """Menanyakan input ke user berulang kali sampai valid."""
    while True:
        user_input = input(prompt_text).strip()
        hasil = validator_fn(user_input)
        if hasil is not None:
            return hasil
        print(f"⚠️  {error_msg}\n")


def jalankan_bot():
    print("=" * 70)
    print("   🤖 BOT KALKULATOR KREDIT (KUR & KUM) - ANGSURAN & BIAYA")
    print("=" * 70)
    print("Ketik data sesuai pertanyaan di bawah ini.\n")

    # 1. Jenis Pengajuan
    def validate_jenis(inp: str):
        val = inp.upper()
        if val == "1" or val == "KUR":
            return "KUR"
        if val == "2" or val == "KUM":
            return "KUM"
        if val == "3" or "TOP UP" in val or "TOPUP" in val:
            return "Top Up KUM"
        return None

    print("1. Haloo, mau pengajuan apa nih?")
    print("   [1] KUR (Kredit Usaha Rakyat)")
    print("   [2] KUM (Kredit Usaha Mikro)")
    print("   [3] Top Up KUM")
    jenis_kredit = tanya_dengan_validasi(
        "👉 Pilih (1 s/d 3): ",
        validate_jenis,
        "Pilihan tidak valid! Silakan ketik angka 1, 2, atau 3."
    )
    print(f"   -> Anda memilih: {jenis_kredit}\n")

    is_topup = "Top Up" in jenis_kredit
    sisa_bade = 0.0
    if is_topup:
        def validate_sisa(inp: str):
            nom = parse_nominal(inp)
            if nom is not None and nom >= 0:
                return nom
            return None

        sisa_bade = tanya_dengan_validasi(
            "👉 Berapa Sisa Bade / Pokok hutangnya? (contoh: 25jt atau 25.000.000): ",
            validate_sisa,
            "Format nominal sisa pokok hutang tidak valid!"
        )
        print(f"   -> Sisa pokok / bade: {format_rupiah(sisa_bade)}\n")

    # Limit Pengajuan
    def validate_limit(inp: str):
        nom = parse_nominal(inp)
        if nom and nom > 0:
            if is_topup and nom <= sisa_bade:
                print(f"⚠️ Limit pengajuan baru harus lebih besar dari sisa hutang ({format_rupiah(sisa_bade)}).")
                return None
            return nom
        return None

    limit = tanya_dengan_validasi(
        "👉 Limit / Plafond pengajuan berapa? (contoh: 110jt atau 110.000.000): ",
        validate_limit,
        "Format limit tidak valid! Masukkan angka seperti 50jt, 100000000, dsb."
    )
    print(f"   -> Limit pengajuan: {format_rupiah(limit)}\n")

    # 2. Tipe Bunga (Flat perbulan atau Efektif per tahun)
    tipe_bunga = "efektif"
    if "KUR" in jenis_kredit:
        tipe_bunga = "efektif"
        print("2. Tipe Bunga: Otomatis 'Efektif per tahun' (Ketentuan baku KUR).\n")
    else:
        def validate_tipe_bunga(inp: str):
            val = inp.lower()
            if "flat" in val or val == "1":
                return "flat"
            if "efektif" in val or val == "2":
                return "efektif"
            return None

        print("2. Mau Flat perbulan apa Efektif per tahun?")
        print("   [1] Flat per bulan")
        print("   [2] Efektif per tahun")
        tipe_bunga = tanya_dengan_validasi(
            "👉 Pilih tipe bunga (1/flat atau 2/efektif): ",
            validate_tipe_bunga,
            "Pilihan tidak valid! Ketik 1 untuk Flat per bulan atau 2 untuk Efektif per tahun."
        )
        print(f"   -> Tipe bunga: {'Flat per bulan' if tipe_bunga == 'flat' else 'Efektif per tahun'}\n")

    # 3. Bunga
    def validate_bunga(inp: str):
        b = parse_persen(inp)
        if b is not None and b >= 0:
            return b
        return None

    if jenis_kredit == "KUR":
        print("3. Mau pakai bunga berapa? (untuk KUR biasanya 6% untuk ke-1, atau 7% untuk ke-2)")
        bunga = tanya_dengan_validasi(
            "👉 Masukkan bunga KUR (% per tahun, contoh: 6): ",
            validate_bunga,
            "Format bunga tidak valid! Masukkan angka persentase (contoh: 6 atau 7)."
        )
    else:
        if tipe_bunga == "flat":
            print("3. Mau pakai bunga berapa? (bunga flat per bulan)")
            bunga = tanya_dengan_validasi(
                "👉 Masukkan bunga flat KUM (% per bulan, contoh: 0.9 atau 1): ",
                validate_bunga,
                "Format bunga tidak valid! Masukkan angka persentase."
            )
        else:
            print("3. Mau pakai bunga berapa? (bunga efektif per tahun)")
            bunga = tanya_dengan_validasi(
                "👉 Masukkan bunga efektif KUM (% per tahun, contoh: 11 atau 12): ",
                validate_bunga,
                "Format bunga tidak valid! Masukkan angka persentase."
            )
    print(f"   -> Bunga: {bunga}%\n")

    # 4. Tenor
    def validate_tenor(inp: str):
        match = re.search(r"\d+", inp)
        if match:
            t = int(match.group(0))
            if t > 0:
                return t
        return None

    tenor = tanya_dengan_validasi(
        "4. Tenor mau berapa? (dalam satuan bulan, contoh: 36): ",
        validate_tenor,
        "Tenor harus berupa angka bulat dalam bulan (contoh: 12, 24, 36)."
    )
    print(f"   -> Tenor: {tenor} bulan\n")

    # 5. Nama Calon Debitur
    nama_debitur = input("5. Nama calon debitur?: ").strip()
    if not nama_debitur:
        nama_debitur = "Calon Debitur"
    print(f"   -> Nama: {nama_debitur}\n")

    # 6. Tanggal Lahir
    def validate_tgl_lahir(inp: str):
        tgl = parse_tanggal(inp)
        if tgl:
            umur = hitung_umur(tgl)
            if 17 <= umur <= 85:
                return tgl
            print(f"   (Perhatian: Umur terhitung {umur} tahun, di luar batas wajar 17-85 tahun)")
            return tgl
        return None

    tgl_lahir = tanya_dengan_validasi(
        "6. Tanggal Lahir? (Format: DD-MM-YYYY, contoh: 17-08-1985): ",
        validate_tgl_lahir,
        "Format tanggal tidak dikenali. Gunakan format DD-MM-YYYY (contoh: 15-05-1980)."
    )
    umur_hitung = hitung_umur(tgl_lahir)
    print(f"   -> Tanggal Lahir: {tgl_lahir.strftime('%d-%m-%Y')} (Umur: {umur_hitung} tahun)\n")

    # 7. Biaya Notaris (Poin 4: Manual input)
    def validate_notaris(inp: str):
        if not inp:
            return 0.0
        nom = parse_nominal(inp)
        if nom is not None and nom >= 0:
            return nom
        return None

    biaya_notaris = tanya_dengan_validasi(
        "👉 Biaya Notaris (input manual, ketik 0 jika tidak ada, atau contoh: 1.500.000): ",
        validate_notaris,
        "Format biaya notaris tidak valid. Masukkan angka (misal: 1500000 atau 0)."
    )
    print(f"   -> Biaya Notaris: {format_rupiah(biaya_notaris)}\n")

    print("\n" + "=" * 70)
    print("   📊 HASIL KALKULASI KREDIT")
    print("=" * 70)

    # Lakukan kalkulasi
    data_input = {
        "jenis_kredit": jenis_kredit,
        "is_topup": is_topup,
        "sisa_bade": sisa_bade,
        "limit": limit,
        "tenor": tenor,
        "bunga": bunga,
        "tipe_bunga": tipe_bunga,
        "tanggal_lahir": tgl_lahir,
        "nama": nama_debitur,
        "biaya_notaris": biaya_notaris
    }

    excel_reader = ExcelInsuranceReader(data_folder="E:\\kalkulator-kredit-bot\\excel_data")
    hasil = kalkulasi_lengkap(data_input, excel_reader)
    teks_output = generate_hasil_teks(hasil)

    print("\n" + teks_output + "\n")
    print("=" * 70)


def main():
    while True:
        jalankan_bot()
        ulang = input("\nApakah ingin menghitung simulasi kredit lainnya? (y/n): ").strip().lower()
        if ulang not in ["y", "ya", "yes"]:
            print("\nTerima kasih telah menggunakan Bot Kalkulator Kredit KUR & KUM!")
            break
        print("\n\n")


if __name__ == "__main__":
    main()
