from OpenSSL import crypto
from pathlib import Path

# === Cấu hình thư mục ===
BASE = Path(__file__).resolve().parents[1]
KEYS_DIR = BASE / "keys"
KEYS_DIR.mkdir(exist_ok=True)

key_path = KEYS_DIR / "signer_key.pem"
cert_path = KEYS_DIR / "signer_cert.pem"

# === Thông tin cá nhân cho chứng thư ===
country_name = "VN"
locality_name = "THÁI NGUYÊN"
common_name = "HOÀNG THỊ QUYÊN"
serial_number = "CCCD:012345678900"  # thay bằng CCCD thật nếu muốn
organization_name = "KySo Demo"
organization_unit = "Demo Unit"
email = "hoangthiquyen@example.com"

# === Sinh khóa RSA 2048-bit ===
key = crypto.PKey()
key.generate_key(crypto.TYPE_RSA, 2048)

# === Tạo chứng thư tự ký (self-signed certificate) ===
cert = crypto.X509()
subject = cert.get_subject()
subject.C = country_name
subject.L = locality_name
subject.O = organization_name
subject.OU = organization_unit
subject.CN = common_name
subject.serialNumber = serial_number
subject.emailAddress = email

cert.set_serial_number(1000)
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 1 năm
cert.set_issuer(subject)
cert.set_pubkey(key)
cert.sign(key, "sha256")

# === Lưu khóa và chứng thư ra file ===
with open(key_path, "wb") as f:
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

with open(cert_path, "wb") as f:
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

print("✅ Đã tạo khóa và chứng thư tại:", KEYS_DIR)
print("👤 Chủ thể:", f"{common_name} ({serial_number})")
print("📍 Khu vực:", locality_name)
print("📧 Email:", email)
