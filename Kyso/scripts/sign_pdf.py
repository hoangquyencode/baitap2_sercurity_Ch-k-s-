# sign_pdf.py — merge overlay (ảnh chữ ký) vào original.pdf rồi ký file kết quả
from pathlib import Path
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE = Path(__file__).resolve().parents[1]
DOCS = BASE / "docs"
ASSETS = BASE / "assets"
KEYS = BASE / "keys"

original_pdf = DOCS / "original.pdf"
signed_pdf = DOCS / "signed.pdf"
signature_img = ASSETS / "signature_img.png"
key_path = KEYS / "signer_key.pem"
sig_file = DOCS / "signature.sig"


# ====== Tạo overlay (ảnh + chữ) ======
def make_overlay(page_width, page_height, img_path, text="   Hoang Thi Quyen",
                 img_w=120, img_h=50, x=75, y=330):
    """
    Tạo một lớp PDF trong bộ nhớ chứa ảnh chữ ký + text.
    Mặc định tọa độ (x=120, y=230) nằm đúng vùng “Ký tên (Ghi rõ họ tên)” theo hình bạn gửi.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_width, page_height))

    if img_path.exists():
        img = ImageReader(str(img_path))
        c.drawImage(img, x, y, width=img_w, height=img_h, mask="auto")

    c.setFont("Helvetica", 10)
    c.drawString(x, y - 14, text)
    c.save()
    buf.seek(0)
    return buf


# ====== Gộp overlay vào PDF gốc ======
def merge_overlay_to_pdf(original_path, out_path, overlay_img):
    reader = PdfReader(str(original_path))
    writer = PdfWriter()

    for pnum, page in enumerate(reader.pages):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        # chỉ ký trang cuối
        if pnum == len(reader.pages) - 1:
            overlay_buf = make_overlay(w, h, overlay_img)
            overlay_pdf = PdfReader(overlay_buf)
            page.merge_page(overlay_pdf.pages[0])

        writer.add_page(page)

    # copy metadata nếu có
    if reader.trailer and reader.trailer.get("/Info"):
        writer._info = reader.trailer["/Info"]

    with open(out_path, "wb") as f:
        writer.write(f)


# ====== Ký số RSA-SHA256 ======
def sign_file_rsa_sha256(file_path, private_key_path, out_sig_path):
    data = file_path.read_bytes()
    with open(private_key_path, "rb") as kf:
        private_key = serialization.load_pem_private_key(kf.read(), password=None)
    signature = private_key.sign(
        data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    out_sig_path.write_bytes(signature)
    return signature


# ====== Chạy chính ======
def main():
    if not original_pdf.exists():
        print("❌ Lỗi: Không tìm thấy original.pdf tại", original_pdf)
        return
    if not key_path.exists():
        print("❌ Lỗi: Không tìm thấy private key tại", key_path)
        return

    print("📄 Đang chèn ảnh chữ ký vào PDF...")
    merge_overlay_to_pdf(original_pdf, signed_pdf, signature_img)
    print("✅ Đã tạo:", signed_pdf)

    print("🔐 Đang ký file bằng RSA-SHA256...")
    signature = sign_file_rsa_sha256(signed_pdf, key_path, sig_file)
    print(f"✨ Đã lưu chữ ký ({len(signature)} bytes) tại:", sig_file)


if __name__ == "__main__":
    main()
