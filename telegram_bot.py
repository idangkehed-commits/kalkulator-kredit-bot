# -*- coding: utf-8 -*-
"""
Bot Telegram Kalkulator Kredit (KUR & KUM)
Menghitung estimasi angsuran dan rincian biaya calon debitur secara interaktif via Telegram.
"""

import os
import sys
import json
import logging
import html
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, date
from typing import Dict, Any, Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from kalkulator import (
    kalkulasi_lengkap,
    hitung_umur,
    format_rupiah,
    generate_hasil_teks,
    ExcelInsuranceReader
)
from bot import parse_nominal, parse_persen, parse_tanggal

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler sederhana untuk memenuhi health check cloud server (Render/Koyeb/Railway)."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Kalkulator Kredit (KUR & KUM) is LIVE 24/7!")

    def log_message(self, format, *args):
        pass


def start_health_server():
    """Menjalankan HTTP health check server di background thread jika variabel PORT diset."""
    port_str = os.environ.get("PORT")
    if not port_str:
        return
    try:
        port = int(port_str)
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info(f"Cloud Health Check server berjalan di port {port}")
    except Exception as e:
        logger.warning(f"Tidak dapat memulai Health Check server: {e}")

# Definisi State Percakapan
(
    STATE_JENIS,
    STATE_SISA_BADE,
    STATE_LIMIT,
    STATE_BUNGA,
    STATE_TIPE_BUNGA,
    STATE_TENOR,
    STATE_NAMA,
    STATE_TGL_LAHIR,
    STATE_NOTARIS
) = range(9)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
EXCEL_DIR = os.path.join(os.path.dirname(__file__), "excel_data")


def load_token() -> str:
    """Membaca Telegram Bot Token dari file config.json atau Environment Variable."""
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        return env_token.strip()

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                token = data.get("telegram_bot_token", "").strip()
                if token and token != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
                    return token
        except Exception as e:
            logger.error(f"Gagal membaca config.json: {e}")
    return ""


def save_token(token: str):
    """Menyimpan Telegram Bot Token ke config.json."""
    data = {"telegram_bot_token": token.strip()}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def generate_hasil_html(hasil: Dict[str, Any]) -> str:
    """Format hasil untuk Telegram menggunakan HTML agar bold dan karakter khusus rapi."""
    limit_fmt = f"{int(hasil['limit']):,}".replace(",", ".")
    angsuran_fmt = format_rupiah(hasil['angsuran'])
    admin_fmt = format_rupiah(hasil['biaya_admin'])

    ket_admin_esc = html.escape(str(hasil['ket_admin']))
    ket_sijitu_esc = html.escape(str(hasil['ket_sijitu']))
    nama_esc = html.escape(str(hasil['nama']))
    info_bunga_esc = html.escape(str(hasil['info_bunga']))
    jenis_esc = html.escape(str(hasil['jenis_kredit']))

    if hasil['biaya_jiwa'] > 0:
        jiwa_fmt = format_rupiah(hasil['biaya_jiwa'])
        if "(" in hasil['ket_jiwa']:
            detail_jiwa = hasil['ket_jiwa'].split("(", 1)[1].rstrip(")")
            jiwa_fmt += f" <i>({html.escape(detail_jiwa)})</i>"
    else:
        jiwa_fmt = html.escape(str(hasil['ket_jiwa']))

    if hasil['biaya_kerugian'] > 0:
        kerugian_fmt = format_rupiah(hasil['biaya_kerugian'])
        if "(" in hasil['ket_kerugian']:
            detail_kerugian = hasil['ket_kerugian'].split("(", 1)[1].rstrip(")")
            kerugian_fmt += f" <i>({html.escape(detail_kerugian)})</i>"
    else:
        kerugian_fmt = f"Rp 0 <i>({html.escape(str(hasil['ket_kerugian']))})</i>"

    notaris_fmt = format_rupiah(hasil['biaya_notaris'])
    sijitu_fmt = format_rupiah(hasil['biaya_sijitu'])
    total_fmt = format_rupiah(hasil['total_biaya'])

    lines = [
        f"<b>Pengajuan {jenis_esc} limit {limit_fmt} tenor {hasil['tenor']} bulan</b>",
        f"Angsuran: {angsuran_fmt} / bulan ({info_bunga_esc})",
        "",
        "<b>Rincian Biaya yang Harus Disiapkan Calon Debitur:</b>",
        f"1. Admin &amp; Provisi : {admin_fmt} <i>({ket_admin_esc})</i>",
        f"2. Asuransi Jiwa Kredit : {jiwa_fmt}",
        f"3. Asuransi Kerugian : {kerugian_fmt}",
        f"4. Biaya Notaris : {notaris_fmt}",
        f"5. Asuransi Sijitu : {sijitu_fmt} <i>({ket_sijitu_esc})</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>Total Biaya yang Disiapkan : {total_fmt}*</b>",
        f"<i>*(Catatan: Calon Debitur: {nama_esc}, Umur: {hasil['umur']} tahun)</i>"
    ]

    if hasil.get("is_topup"):
        sisa_bade_fmt = format_rupiah(hasil.get("sisa_bade", 0))
        dana_cair_fmt = format_rupiah(hasil.get("dana_cair_bersih", 0))
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "<b>Perhitungan Penerimaan Bersih (Top Up):</b>",
            f"• Limit Pengajuan Baru      : <b>Rp {limit_fmt}</b>",
            f"• Sisa Pokok / Bade Hutang  : <b>{sisa_bade_fmt}</b>",
            f"• Total Biaya Disiapkan     : <b>{total_fmt}</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"💰 <b>Estimasi Dana Diterima Bersih : {dana_cair_fmt}</b>"
        ])

    return "\n".join(lines)


# ==================== HANDLER PERCAKAPAN ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai bot dan menampilkan sambutan."""
    context.user_data.clear()

    keyboard = [
        [
            InlineKeyboardButton("KUR", callback_data="JENIS_KUR"),
            InlineKeyboardButton("Top Up KUR", callback_data="JENIS_TOPUP_KUR")
        ],
        [
            InlineKeyboardButton("KUM", callback_data="JENIS_KUM"),
            InlineKeyboardButton("Top Up KUM", callback_data="JENIS_TOPUP_KUM")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "Halo! Selamat datang di <b>Bot Kalkulator Kredit (KUR & KUM)</b> 🤖\n\n"
        "Saya dapat membantu Anda menghitung angsuran per bulan dan rincian biaya yang perlu disiapkan calon debitur.\n\n"
        "<b>1. Haloo, mau pengajuan apa nih?</b>\n"
        "Silakan pilih jenis kredit di bawah:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(welcome_text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=reply_markup)

    return STATE_JENIS


async def jenis_kredit_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani pemilihan jenis kredit (KUR, Top Up KUR, KUM, Top Up KUM)."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "JENIS_KUR":
        jenis = "KUR"
        is_topup = False
    elif data == "JENIS_TOPUP_KUR":
        jenis = "Top Up KUR"
        is_topup = True
    elif data == "JENIS_KUM":
        jenis = "KUM"
        is_topup = False
    elif data == "JENIS_TOPUP_KUM":
        jenis = "Top Up KUM"
        is_topup = True
    else:
        jenis = "KUR"
        is_topup = False

    context.user_data["jenis_kredit"] = jenis
    context.user_data["is_topup"] = is_topup

    if is_topup:
        await query.edit_message_text(
            f"✅ Jenis Kredit: <b>{jenis}</b>\n\n"
            "👉 <b>Berapa Sisa Bade atau Pokok hutangnya saat ini?</b>\n"
            "<i>(Contoh: ketik 25jt, 25.000.000, atau 30000000)</i>",
            parse_mode="HTML"
        )
        return STATE_SISA_BADE
    else:
        context.user_data["sisa_bade"] = 0.0
        await query.edit_message_text(
            f"✅ Jenis Kredit: <b>{jenis}</b>\n\n"
            "👉 <b>Berapa limit pengajuan yang diinginkan?</b>\n"
            "<i>(Contoh: ketik 110jt, 110.000.000, atau 50000000)</i>",
            parse_mode="HTML"
        )
        return STATE_LIMIT


async def handle_sisa_bade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani input Sisa Bade / Pokok Hutang untuk Top Up."""
    text = update.message.text
    sisa = parse_nominal(text)

    if sisa is None or sisa < 0:
        await update.message.reply_text(
            "⚠️ Nominal Sisa Pokok Hutang / Bade tidak valid. Silakan ketik kembali:\n"
            "<i>(Contoh: 25jt atau 25.000.000)</i>",
            parse_mode="HTML"
        )
        return STATE_SISA_BADE

    context.user_data["sisa_bade"] = sisa
    await update.message.reply_text(
        f"✅ Sisa Pokok / Bade: <b>{format_rupiah(sisa)}</b>\n\n"
        "👉 <b>Berapa Limit Pengajuan baru yang diinginkan?</b>\n"
        "<i>(Contoh: ketik 110jt, 110.000.000, atau 50000000)</i>",
        parse_mode="HTML"
    )
    return STATE_LIMIT


async def handle_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani input limit pengajuan."""
    text = update.message.text
    limit = parse_nominal(text)

    if limit is None or limit <= 0:
        await update.message.reply_text(
            "⚠️ Nominal limit tidak valid. Silakan ketik kembali nominal pengajuan:\n"
            "<i>(Contoh: 110jt atau 110.000.000)</i>",
            parse_mode="HTML"
        )
        return STATE_LIMIT

    is_topup = context.user_data.get("is_topup", False)
    sisa_bade = context.user_data.get("sisa_bade", 0.0)
    if is_topup and limit <= sisa_bade:
        await update.message.reply_text(
            f"⚠️ Untuk pengajuan Top Up, limit pengajuan baru harus lebih besar dari sisa pokok hutang ({format_rupiah(sisa_bade)}).\n"
            "Silakan ketik kembali nominal limit baru:",
            parse_mode="HTML"
        )
        return STATE_LIMIT

    context.user_data["limit"] = limit
    jenis = context.user_data.get("jenis_kredit", "KUR")

    if "KUR" in jenis:
        # Untuk KUR / Top Up KUR tipe bunga sudah pasti Efektif per tahun
        context.user_data["tipe_bunga"] = "efektif"
        keyboard = [
            [
                InlineKeyboardButton("6% (Pengajuan ke-1)", callback_data="BUNGA_6"),
                InlineKeyboardButton("7% (Pengajuan ke-2)", callback_data="BUNGA_7")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ Limit Pengajuan: <b>{format_rupiah(limit)}</b>\n\n"
            "ℹ️ <i>Tipe Bunga: Otomatis 'Efektif per tahun' (Ketentuan baku KUR)</i>\n\n"
            "👉 <b>Mau pakai bunga berapa?</b>\n"
            "<i>(Untuk KUR biasanya 6% untuk ke-1 atau 7% untuk ke-2. Pilih tombol atau ketik angka):</i>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return STATE_BUNGA
    else:
        # Untuk KUM / Top Up KUM: tanyakan dulu mau Flat perbulan apa Efektif per tahun
        keyboard = [
            [
                InlineKeyboardButton("Flat per bulan", callback_data="TIPE_FLAT"),
                InlineKeyboardButton("Efektif per tahun", callback_data="TIPE_EFEKTIF")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ Limit Pengajuan: <b>{format_rupiah(limit)}</b>\n\n"
            "👉 <b>Mau Flat perbulan apa Efektif per tahun?</b>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return STATE_TIPE_BUNGA


async def handle_tipe_bunga_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani pemilihan tipe bunga KUM lalu menanyakan persentase bunganya."""
    query = update.callback_query
    await query.answer()

    data = query.data
    tipe = "flat" if data == "TIPE_FLAT" else "efektif"
    context.user_data["tipe_bunga"] = tipe

    if tipe == "flat":
        await query.edit_message_text(
            "✅ Tipe Bunga KUM: <b>Flat per bulan</b>\n\n"
            "👉 <b>Mau pakai bunga berapa % flat per bulan?</b>\n"
            "<i>(Contoh: ketik 0.9 atau 1)</i>",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            "✅ Tipe Bunga KUM: <b>Efektif per tahun</b>\n\n"
            "👉 <b>Mau pakai bunga berapa % efektif per tahun?</b>\n"
            "<i>(Contoh: ketik 11 atau 12)</i>",
            parse_mode="HTML"
        )
    return STATE_BUNGA


async def handle_bunga_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani pemilihan tombol bunga 6% atau 7% untuk KUR."""
    query = update.callback_query
    await query.answer()

    data = query.data
    bunga = 6.0 if data == "BUNGA_6" else 7.0
    context.user_data["bunga"] = bunga
    context.user_data["tipe_bunga"] = "efektif"

    keyboard = [
        [
            InlineKeyboardButton("12 Bulan", callback_data="TENOR_12"),
            InlineKeyboardButton("24 Bulan", callback_data="TENOR_24"),
            InlineKeyboardButton("36 Bulan", callback_data="TENOR_36")
        ],
        [
            InlineKeyboardButton("48 Bulan", callback_data="TENOR_48"),
            InlineKeyboardButton("60 Bulan", callback_data="TENOR_60")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Bunga KUR: <b>{bunga}% per tahun (Efektif)</b>\n\n"
        "👉 <b>Tenor mau berapa?</b>\n"
        "<i>(Pilih opsi tombol bulan di bawah atau ketik angka bulan secara langsung):</i>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return STATE_TENOR


async def handle_bunga_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani input teks untuk bunga lalu lanjut ke pertanyaan tenor."""
    text = update.message.text
    bunga = parse_persen(text)

    if bunga is None or bunga < 0:
        await update.message.reply_text(
            "⚠️ Format bunga tidak valid. Masukkan angka persentase (contoh: 6 atau 0.9):"
        )
        return STATE_BUNGA

    context.user_data["bunga"] = bunga
    tipe = context.user_data.get("tipe_bunga", "efektif")
    tipe_label = "Flat per bulan" if tipe == "flat" else "Efektif per tahun"

    keyboard = [
        [
            InlineKeyboardButton("12 Bulan", callback_data="TENOR_12"),
            InlineKeyboardButton("24 Bulan", callback_data="TENOR_24"),
            InlineKeyboardButton("36 Bulan", callback_data="TENOR_36")
        ],
        [
            InlineKeyboardButton("48 Bulan", callback_data="TENOR_48"),
            InlineKeyboardButton("60 Bulan", callback_data="TENOR_60")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"✅ Bunga: <b>{bunga}% ({tipe_label})</b>\n\n"
        "👉 <b>Tenor mau berapa?</b>\n"
        "<i>(Pilih tombol atau ketik angka bulan):</i>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return STATE_TENOR


async def handle_tenor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani pemilihan tenor via tombol."""
    query = update.callback_query
    await query.answer()

    tenor = int(query.data.replace("TENOR_", ""))
    context.user_data["tenor"] = tenor

    await query.edit_message_text(
        f"✅ Tenor: <b>{tenor} bulan</b>\n\n"
        "<b>5. Nama calon debitur?</b>",
        parse_mode="HTML"
    )
    return STATE_NAMA


async def handle_tenor_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani input tenor via teks."""
    text = update.message.text
    try:
        tenor = int(text.strip().replace("bulan", "").strip())
        if tenor <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("⚠️ Tenor harus angka bulat dalam bulan (contoh: 24 atau 36):")
        return STATE_TENOR

    context.user_data["tenor"] = tenor
    await update.message.reply_text(
        f"✅ Tenor: <b>{tenor} bulan</b>\n\n"
        "<b>5. Nama calon debitur?</b>",
        parse_mode="HTML"
    )
    return STATE_NAMA


async def handle_nama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani input nama calon debitur."""
    nama = update.message.text.strip()
    if not nama:
        nama = "Calon Debitur"
    context.user_data["nama"] = nama

    await update.message.reply_text(
        f"✅ Calon Debitur: <b>{nama}</b>\n\n"
        "<b>6. Tanggal Lahir?</b>\n"
        "<i>(Format: DD-MM-YYYY, contoh: 17-08-1985)</i>",
        parse_mode="HTML"
    )
    return STATE_TGL_LAHIR


async def handle_tgl_lahir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani input tanggal lahir calon debitur."""
    text = update.message.text
    tgl = parse_tanggal(text)

    if not tgl:
        await update.message.reply_text(
            "⚠️ Format tanggal tidak dikenali. Gunakan format DD-MM-YYYY (contoh: 15-05-1980):"
        )
        return STATE_TGL_LAHIR

    umur = hitung_umur(tgl)
    context.user_data["tanggal_lahir"] = tgl
    context.user_data["umur"] = umur

    keyboard = [
        [
            InlineKeyboardButton("Rp 0 (Tanpa Notaris)", callback_data="NOTARIS_0")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Tanggal Lahir: <b>{tgl.strftime('%d-%m-%Y')}</b> (Umur: <b>{umur} tahun</b>)\n\n"
        "👉 <b>Biaya Notaris:</b>\n"
        "<i>(Input manual nominal, misal: 1500000 atau klik tombol Rp 0 di bawah jika tidak ada):</i>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return STATE_NOTARIS


async def handle_notaris_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani tombol Rp 0 untuk notaris."""
    query = update.callback_query
    await query.answer()

    context.user_data["biaya_notaris"] = 0.0
    return await proses_kalkulasi_dan_kirim(query, context, is_callback=True)


async def handle_notaris_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani input nominal notaris via pesan teks."""
    text = update.message.text
    nom = parse_nominal(text)
    if nom is None:
        nom = 0.0

    context.user_data["biaya_notaris"] = nom
    return await proses_kalkulasi_dan_kirim(update, context, is_callback=False)


async def proses_kalkulasi_dan_kirim(event_source, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> int:
    """Menjalankan kalkulasi lengkap dan mengirimkan teks hasil sesuai permintaan."""
    excel_reader = ExcelInsuranceReader(data_folder=EXCEL_DIR)
    hasil = kalkulasi_lengkap(context.user_data, excel_reader)
    pesan_hasil = generate_hasil_html(hasil)

    keyboard = [
        [InlineKeyboardButton("🔄 Hitung Simulasi Baru", callback_data="RESTART")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if is_callback:
            await event_source.edit_message_text(pesan_hasil, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await event_source.message.reply_text(pesan_hasil, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"Gagal mengirim pesan HTML ({e}), fallback ke teks biasa...")
        pesan_plain = generate_hasil_teks(hasil)
        if is_callback:
            await event_source.edit_message_text(pesan_plain, reply_markup=reply_markup)
        else:
            await event_source.message.reply_text(pesan_plain, reply_markup=reply_markup)

    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan sesi perhitungan."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Simulasi dibatalkan. Ketik /start atau /hitung untuk memulai simulasi baru.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ==================== MAIN RUNNER ====================

def main():
    token = load_token()
    if not token:
        print("\n" + "=" * 70)
        print("⚠️  TELEGRAM BOT TOKEN BELUM DIISI!")
        print("=" * 70)
        print("Untuk menjalankan bot di Telegram:")
        print("1. Buka aplikasi Telegram dan cari @BotFather")
        print("2. Kirim perintah /newbot untuk membuat bot baru dan dapatkan HTTP API Token")
        print("3. Masukkan token Anda di bawah ini:")
        try:
            token = input("👉 Paste Telegram Bot Token: ").strip()
            if token:
                save_token(token)
                print("✅ Token berhasil disimpan ke config.json!\n")
            else:
                print("❌ Token kosong. Silakan isi token di file E:\\kalkulator-kredit-bot\\config.json")
                sys.exit(1)
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)

    print("=" * 70)
    print("   🤖 MEMULAI TELEGRAM BOT KALKULATOR KREDIT (KUR & KUM)")
    print("=" * 70)
    print("Bot sedang berjalan dan siap menerima pesan di Telegram...")
    print("Tekan Ctrl+C untuk menghentikan bot.")

    start_health_server()

    app = ApplicationBuilder().token(token).build()

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.warning(f"Telegram error: {context.error}")

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("hitung", start_command),
            CallbackQueryHandler(start_command, pattern="^RESTART$")
        ],
        states={
            STATE_JENIS: [
                CallbackQueryHandler(jenis_kredit_selected, pattern="^JENIS_")
            ],
            STATE_SISA_BADE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sisa_bade)
            ],
            STATE_LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_limit)
            ],
            STATE_BUNGA: [
                CallbackQueryHandler(handle_bunga_callback, pattern="^BUNGA_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bunga_text)
            ],
            STATE_TIPE_BUNGA: [
                CallbackQueryHandler(handle_tipe_bunga_callback, pattern="^TIPE_")
            ],
            STATE_TENOR: [
                CallbackQueryHandler(handle_tenor_callback, pattern="^TENOR_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tenor_text)
            ],
            STATE_NAMA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nama)
            ],
            STATE_TGL_LAHIR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tgl_lahir)
            ],
            STATE_NOTARIS: [
                CallbackQueryHandler(handle_notaris_callback, pattern="^NOTARIS_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notaris_text)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CommandHandler("start", start_command)
        ],
        per_message=False
    )

    app.add_error_handler(error_handler)
    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
