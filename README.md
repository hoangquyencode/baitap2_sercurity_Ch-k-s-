# baitap2_sercurity_Ch-k-s-
BÀI TẬP VỀ NHÀ – MÔN: AN TOÀN VÀ BẢO MẬT THÔNG TIN
 Chủ đề: Chữ ký số trong file PDF
 Giảng viên: Đỗ Duy Cốp
 Thời điểm giao: 2025-10-24 11:45
 Đối tượng áp dụng: Toàn bộ sv lớp học phần 58KTPM
 Hạn nộp: Sv upload tất cả lên github trước 2025-10-31 23:59:59--
I. MÔ TẢ CHUNG
 Sinh viên thực hiện báo cáo và thực hành: phân tích và hiện thực việc nhúng, xác 
thực chữ ký số trong file PDF.
 Phải nêu rõ chuẩn tham chiếu (PDF 1.7 / PDF 2.0, PAdES/ETSI) và sử dụng công cụ 
thực thi (ví dụ iText7, OpenSSL, PyPDF, pdf-lib)

# Bailam


 1) Cấu trúc PDF liên quan chữ ký (Nghiên cứu)- Mô tả ngắn gọn: Catalog, Pages tree, Page object, Resources, Content streams, 
XObject, AcroForm, Signature field (widget), Signature dictionary (/Sig), 
/ByteRange, /Contents, incremental updates, và DSS (theo PAdES).- Liệt kê object refs quan trọng và giải thích vai trò của từng object trong 
lưu/truy xuất chữ ký.- Đầu ra: 1 trang tóm tắt + sơ đồ object (ví dụ: Catalog → Pages → Page → /Contents
 ; Catalog → /AcroForm → SigField → SigDict).

Khái quát cấu trúc file PDF: 

      Một file PDF được tổ chức dưới dạng cây các đối tượng (objects).
      Mỗi object có một ID (object number) và có thể tham chiếu tới các object khác.
      Các phần chính:
      Catalog (Root Object): gốc của toàn bộ tài liệu PDF.
      Pages Tree: quản lý toàn bộ các trang (Page objects).
      Page Object: mô tả nội dung của một trang cụ thể (text, hình, annotations, forms...).
      AcroForm: mô tả biểu mẫu (form fields) trong PDF, bao gồm cả trường chữ ký số (signature field).
      XObject, Resources, Content streams: chứa dữ liệu hiển thị, font, hình ảnh.
Các thành phần liên quan đến chữ ký số:

| Thành phần                        | Vai trò                                                                                  | Ghi chú                                                                            |
| --------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Catalog (Root)**                | Gốc của tài liệu, chứa tham chiếu đến `/Pages`, `/AcroForm`, `/DSS`                      | `/AcroForm` chứa các form fields, trong đó có trường chữ ký                        |
| **Pages Tree**                    | Quản lý danh sách các trang PDF                                                          | Không trực tiếp liên quan đến chữ ký, nhưng chữ ký có thể hiển thị trên một Page   |
| **Page Object**                   | Một trang cụ thể; có thể chứa annotation (như widget của chữ ký)                         | Annotation type `/Widget` dùng để hiển thị vùng chữ ký                             |
| **Resources**                     | Font, hình ảnh, màu sắc được dùng trong trang                                            | Vùng hiển thị chữ ký có thể dùng font hoặc hình ảnh từ đây                         |
| **Content Stream**                | Dữ liệu vẽ nội dung trang (text, hình, vector)                                           | Không chứa chữ ký, nhưng hiển thị vùng khung chữ ký                                |
| **AcroForm**                      | Định nghĩa biểu mẫu PDF, chứa các trường form (text field, checkbox, signature field...) | `/Fields` → danh sách các form field                                               |
| **Signature Field (Widget)**      | Một **field** trong `/AcroForm`, kiểu `/Sig`                                             | Là nơi người dùng ký số, hiển thị khung chữ ký                                     |
| **Signature Dictionary (/Sig)**   | Chứa **dữ liệu chữ ký thực tế**                                                          | Đây là phần quan trọng nhất – chứa thông tin ký và tham chiếu đến nội dung được ký |
| **/ByteRange**                    | Mảng xác định **phạm vi byte** trong file PDF được bao phủ bởi chữ ký                    | Giúp đảm bảo rằng không phần nào ngoài phạm vi này bị sửa đổi sau khi ký           |
| **/Contents**                     | Chứa **chữ ký số** (thường là chuỗi Base64 của chữ ký PKCS#7/CMS)                        | Sinh ra từ private key của người ký                                                |
| **Incremental Updates**           | PDF hỗ trợ ghi chồng (append) mà không thay đổi nội dung cũ                              | Cho phép thêm chữ ký mới mà vẫn giữ chữ ký cũ hợp lệ                               |
| **DSS (Document Security Store)** | Theo chuẩn **PAdES**, lưu trữ các thông tin xác thực đi kèm: certificate, CRL, OCSP      | Giúp xác minh chữ ký ngay cả khi máy offline                                       |


Liệt kê object refs quan trọng và vai trò:

                          | Object Ref | Tên / Kiểu                       | Vai trò trong quá trình ký và xác thực                          |
                          | ---------- | -------------------------------- | --------------------------------------------------------------- |
                          | `1 0 obj`  | `/Catalog`                       | Tham chiếu đến `/Pages`, `/AcroForm`, `/DSS`                    |
                          | `2 0 obj`  | `/Pages`                         | Danh sách các trang                                             |
                          | `3 0 obj`  | `/Page`                          | Một trang cụ thể có vùng ký (annotation)                        |
                          | `4 0 obj`  | `/AcroForm`                      | Chứa danh sách các field, trong đó có trường chữ ký `/SigField` |
                          | `5 0 obj`  | `/SigField` (Widget Annotation)  | Liên kết đến `/Sig` để hiển thị và ký                           |
                          | `6 0 obj`  | `/Sig` (Signature Dictionary)    | Lưu trữ chữ ký số, /ByteRange, /Contents, /Name, /Reason...     |
                          | `7 0 obj`  | `/DSS` (Document Security Store) | Lưu các certificate, OCSP, CRL phục vụ xác thực               


2) Thời gian ký được lưu ở đâu?- Nêu tất cả vị trí có thể lưu thông tin thời gian:
 + /M trong Signature dictionary (dạng text, không có giá trị pháp lý).
 + Timestamp token (RFC 3161) trong PKCS#7 (attribute timeStampToken).
 + Document timestamp object (PAdES).
 + DSS (Document Security Store) nếu có lưu timestamp và dữ liệu xác minh.- Giải thích khác biệt giữa thông tin thời gian /M và timestamp RFC3161.

Trong file PDF có chữ ký số, thông tin thời gian (time information) có thể xuất hiện ở nhiều vị trí khác nhau, tùy theo mức độ và chuẩn của chữ ký (PDF cơ bản, PKCS#7, hoặc PAdES).
Dưới đây là các vị trí có thể lưu thời gian ký:
      Trường /M trong Signature Dictionary
            Vị trí: Trong Signature Dictionary (/Sig) – là phần chứa dữ liệu chữ ký chính.
            Cú pháp ví dụ: /M (D:20251028113000+07'00')
      Ý nghĩa: Thể hiện thời điểm mà phần mềm ký ghi nhận (theo đồng hồ hệ thống máy tính).
               Định dạng theo chuẩn PDF: D:YYYYMMDDHHmmSSOHH'mm' 
               Ví dụ: D:20251028113000+07'00' → 28/10/2025, 11:30:00 GMT+7
      Giá trị pháp lý: Không có giá trị xác thực pháp lý.  
                       Vì thời gian này không được chứng thực bởi bên thứ ba (TSA).
                       Có thể bị thay đổi hoặc sai lệch nếu người ký sửa thời gian hệ thống.
      Timestamp Token trong PKCS#7 (RFC 3161)
              Vị trí: Bên trong dữ liệu chữ ký /Contents, thuộc cấu trúc PKCS#7 / CMS (Cryptographic Message Syntax).
              Thành phần: timeStampToken (theo chuẩn RFC 3161 – Time-Stamp Protocol).
              Nguồn: Được cấp bởi TSA (Time Stamping Authority) – một bên thứ ba tin cậy.
              Cơ chế:
                  + Người ký gửi hàm băm (hash) của tài liệu đến TSA.
                  + TSA ký lại hàm băm + thời gian hiện tại → tạo timeStampToken.
                  + Token này được chèn vào chữ ký PKCS#7 → trở thành bằng chứng rằng tài liệu đã tồn tại tại thời điểm đó.
              Giá trị pháp lý: Có giá trị xác thực pháp lý, vì được chứng thực bởi TSA.
    Document Timestamp Object (PAdES)
              Vị trí: Là một chữ ký đặc biệt trong file PDF, nhưng không gắn với người ký.
              Định nghĩa: Một loại chữ ký có /Type /DocTimeStamp thay vì /Sig.
              Mục đích:
                    +  Xác nhận toàn bộ tài liệu PDF tại một thời điểm cụ thể.
                    +  Được dùng trong PAdES-LT / PAdES-LTA để bảo tồn tính xác thực lâu dài.
              Cơ chế: Cũng dựa trên RFC 3161 timestamp, nhưng áp dụng cho toàn bộ tài liệu (không chỉ riêng chữ ký).

    DSS (Document Security Store)
        Vị trí: /DSS object trong Catalog, theo chuẩn PAdES.
        Nội dung có thể chứa:
                  /Certs – các chứng chỉ (certificate chain)
                  /OCSPs – phản hồi xác thực chứng thực online
                  /CRLs – danh sách chứng chỉ bị thu hồi
                  Timestamp (RFC 3161) – thời gian xác minh hoặc thời điểm ký
        Vai trò: Lưu thông tin xác thực lâu dài, phục vụ PAdES-LTV (Long-Term Validation).

So sánh giữa /M và Timestamp RFC 3161: 
        | Tiêu chí                  | `/M` trong /Sig                   | Timestamp RFC 3161                                                        |
| ------------------------- | --------------------------------- | ------------------------------------------------------------------------- |
| **Nguồn gốc**             | Lấy từ hệ thống máy của người ký  | Do **TSA** (bên thứ ba tin cậy) cấp                                       |
| **Vị trí lưu**            | Trực tiếp trong `/Sig` dictionary | Bên trong chữ ký PKCS#7 (trong `/Contents`) hoặc trong Document Timestamp |
| **Chuẩn tham chiếu**      | PDF 1.7 / PDF 2.0                 | RFC 3161 (Time-Stamp Protocol)                                            |
| **Bảo đảm tính toàn vẹn** | Không được xác thực               | Có chữ ký số của TSA → chống giả mạo                                      |
| **Giá trị pháp lý**       | ❌ Không có                        | ✅ Có giá trị chứng thực thời gian ký                                      |
| **Mục đích sử dụng**      | Thông tin hiển thị (tham khảo)    | Chứng minh tài liệu tồn tại tại thời điểm ký                              |


3) Các bước tạo và lưu chữ ký trong PDF (đã có private RSA)- Viết script/code thực hiện tuần tự:
 1. Chuẩn bị file PDF gốc.
 2. Tạo Signature field (AcroForm), reserve vùng /Contents (8192 bytes).
 3. Xác định /ByteRange (loại trừ vùng /Contents khỏi hash).
 4. Tính hash (SHA-256/512) trên vùng ByteRange.
 5. Tạo PKCS#7/CMS detached hoặc CAdES:- Include messageDigest, signingTime, contentType.- Include certificate chain.- (Tùy chọn) thêm RFC3161 timestamp token.
 6. Chèn blob DER PKCS#7 vào /Contents (hex/binary) đúng offset.
 7. Ghi incremental update.
 8. (LTV) Cập nhật DSS với Certs, OCSPs, CRLs, VRI.- Phải nêu rõ: hash alg, RSA padding, key size, vị trí lưu trong PKCS#7.- Đầu ra: mã nguồn, file PDF gốc, file PDF đã ký




<img width="1108" height="912" alt="image" src="https://github.com/user-attachments/assets/bae64ca1-fc22-4c9c-852c-c2ae63634bf1" />






<img width="1354" height="915" alt="image" src="https://github.com/user-attachments/assets/aeb2319a-1a13-43aa-8da4-f36b8c7a9313" />







<img width="1065" height="895" alt="image" src="https://github.com/user-attachments/assets/ff2b120d-1a6b-49af-a500-e3e7e4b34d3c" />






