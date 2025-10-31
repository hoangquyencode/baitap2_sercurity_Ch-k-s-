# Xacminh_signature.py — Kiểm tra chữ ký số của file PDF
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509

# Đường dẫn
BASE = Path(__file__).resolve().parents[1]
DOCS = BASE / "docs"
KEYS = BASE / "keys"

pdf_path = DOCS / "signed.pdf"
sig_path = DOCS / "signature.sig"
cert_path = KEYS / "signer_cert.pem"

def verify_signature(pdf_path, sig_path, cert_path):
    """Kiểm tra xem file PDF có bị sửa và chữ ký có hợp lệ không."""
    print("🔍 Đang xác minh chữ ký...")

    if not pdf_path.exists():
        print("❌ Không tìm thấy file PDF:", pdf_path)
        return
    if not sig_path.exists():
        print("❌ Không tìm thấy file chữ ký:", sig_path)
        return
    if not cert_path.exists():
        print("❌ Không tìm thấy chứng thư số:", cert_path)
        return

    # Đọc dữ liệu
    data = pdf_path.read_bytes()
    signature = sig_path.read_bytes()

    # Load public key từ chứng thư PEM
    cert_data = cert_path.read_bytes()
    cert = x509.load_pem_x509_certificate(cert_data)
    public_key = cert.public_key()

    # Kiểm tra chữ ký
    try:
        public_key.verify(
            signature,
            data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print("✅ Xác minh thành công!")
        print("   → Chữ ký hợp lệ và file PDF chưa bị chỉnh sửa.")
    except Exception as e:
        print("❌ Xác minh thất bại!")
        print("   Lỗi:", e)

if __name__ == "__main__":
    verify_signature(pdf_path, sig_path, cert_path)
