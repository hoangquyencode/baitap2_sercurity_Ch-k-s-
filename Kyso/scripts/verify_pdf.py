from pyhanko.sign import validation
from pyhanko.sign.diff_analysis import ModificationLevel
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.keys import load_cert_from_pemder
from pyhanko_certvalidator import ValidationContext
import hashlib, datetime, io
from datetime import timezone, timedelta
from pathlib import Path

# === CẤU HÌNH ===
BASE = Path(__file__).resolve().parents[1]
PDF_PATH = BASE / "docs" / "signed_pdf_pkcs7.pdf"
CERT_FILE = BASE / "keys" / "signer_cert.pem"
LOG_FILE = BASE / "scripts" / "verify_log.txt"
FIELD_NAME = "Signature1"

# === 1️⃣ Tạo ValidationContext tin cậy ===
vc = ValidationContext(trust_roots=[load_cert_from_pemder(str(CERT_FILE))])

# === 2️⃣ Chuẩn bị log ===
log = io.StringIO()
def log_print(msg):
    print(msg)
    log.write(msg + "\n")

log_print("=== KIỂM TRA XÁC THỰC CHỮ KÝ PDF ===")
log_print(f"🕒 Thời gian kiểm thử: {datetime.datetime.now()}")
log_print(f"📄 File kiểm tra: {PDF_PATH}")
log_print("====================================")

try:
    with open(PDF_PATH, "rb") as f:
        reader = PdfFileReader(f)
        embedded_sigs = reader.embedded_signatures

        if not embedded_sigs:
            log_print("❌ Không tìm thấy chữ ký nào trong file PDF.")
            raise SystemExit

        sig = embedded_sigs[0]
        sig_name = sig.field_name or FIELD_NAME
        log_print(f"🔍 Phát hiện chữ ký: {sig_name}")
        log_print("====================================")

        # === Đọc /Contents và /ByteRange ===
        sig_dict = sig.sig_object
        contents = sig_dict.get('/Contents')
        byte_range = sig_dict.get('/ByteRange')

        log_print(f"/Contents: {len(contents)} bytes")
        log_print(f"/ByteRange: {byte_range}")

        # === 5️⃣ Tính lại SHA256 vùng ByteRange ===
        f.seek(0)
        data = f.read()
        ranges = list(byte_range)
        signed_data = data[ranges[0]:ranges[0]+ranges[1]] + data[ranges[2]:ranges[2]+ranges[3]]
        digest = hashlib.sha256(signed_data).hexdigest()
        log_print(f"🔑 SHA256(ByteRange): {digest[:64]}... ✅")

        # === 6️⃣ Xác thực chữ ký ===
        status = validation.validate_pdf_signature(sig, vc)
        log_print("====================================")
        log_print("🔒 KẾT QUẢ XÁC THỰC CHỮ KÝ:")
        log_print(status.pretty_print_details())

        # === 7️⃣ Thông tin chứng thư ===
        signer_cert = status.signing_cert
        if signer_cert:
            subj = signer_cert.subject.human_friendly
            log_print("\n📜 Chứng thư người ký:")
            log_print(f"  👤 Chủ thể: {subj}")
            log_print(f"  SHA1: {signer_cert.sha1_fingerprint.hex()}")
            log_print(f"  SHA256: {signer_cert.sha256_fingerprint.hex()}")
        else:
            log_print("⚠️ Không đọc được chứng thư của người ký.")

        # === 8️⃣ Thời gian ký ===
        if status.signer_reported_dt:
            vn_tz = timezone(timedelta(hours=7))
            local_time = status.signer_reported_dt.astimezone(vn_tz)
            log_print(f"\n🕒 Thời gian ký (VN): {local_time}")
        else:
            log_print("⚠️ Không có timestamp (RFC3161).")

        # === 9️⃣ Kiểm tra chỉnh sửa ===
        mod_level = getattr(status, "modification_level", None)
        if mod_level == ModificationLevel.NONE:
            log_print("✅ File chưa bị chỉnh sửa kể từ khi ký.")
        elif mod_level == ModificationLevel.FORM_FILLING:
            log_print("⚠️ File có thay đổi nhỏ (điền form) sau khi ký.")
        else:
            log_print("❌ File đã bị chỉnh sửa sau khi ký!")

        log_print("====================================")

        # === 🔟 Tổng kết ===
        if status.bottom_line:
            log_print("✅ Chữ ký HỢP LỆ và tài liệu NGUYÊN VẸN.")
        else:
            log_print("❌ Chữ ký KHÔNG HỢP LỆ hoặc tài liệu đã bị thay đổi.")

except Exception as e:
    log_print(f"⚠️ Lỗi khi xác minh chữ ký: {e}")

# === 💾 Ghi log ===
with open(LOG_FILE, "w", encoding="utf-8") as out:
    out.write(log.getvalue())

log_print(f"\n📁 Log đã lưu tại: {LOG_FILE}")
