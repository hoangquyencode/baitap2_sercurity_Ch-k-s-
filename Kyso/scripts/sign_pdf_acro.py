#!/usr/bin/env python3
"""
sign_pdf_acro.py
Create a PDF signature field (AcroForm) with reserved /Contents and insert a PKCS#7 (CMS) detached SignedData.

Outputs:
  - interim.pdf    (with placeholder)
  - interim.der    (PKCS#7 DER)
  - docs/signed_pdf_pkcs7.pdf  (final signed PDF)
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pikepdf

# ---- CONFIG ----
BASE = Path(__file__).resolve().parents[1]
INPUT_PDF = str(BASE / "docs" / "original.pdf")
INTERIM_PDF = str(BASE / "interim.pdf")
SIGNED_PDF = str(BASE / "docs" / "signed_pdf_pkcs7.pdf")
PRIVATE_KEY = str(BASE / "keys" / "signer_key.pem")
SIGNER_CERT = str(BASE / "keys" / "signer_cert.pem")
CHAIN_PEM = None  # Optional: str(BASE / "keys" / "chain.pem")
CONTENTS_RESERVE = 32768  # bytes reserved in /Contents (use large reserve)
HASH_ALG = "sha256"  # "sha256" or "sha512"
OPENSSL_BIN = "openssl"  # or full path to openssl.exe

# ---- Helpers ----
def ensure_files_exist():
    for p in (INPUT_PDF, PRIVATE_KEY, SIGNER_CERT):
        if not Path(p).exists():
            print(f"[ERROR] Required file not found: {p}")
            sys.exit(1)

def add_sig_field_with_placeholder(input_pdf, out_pdf, reserve_len):
    """
    Add a signature form field with /Contents hex placeholder of reserve_len bytes (00...),
    and a long /ByteRange textual placeholder so replacement won't change byte offsets.
    """
    hex_zeros = "00" * reserve_len
    # Build a long ByteRange placeholder string: four 10-digit zero slots (safe up to ~10^10)
    br_placeholder_text = "/ByteRange [ 0000000000 0000000000 0000000000 0000000000 ]"
    with pikepdf.Pdf.open(input_pdf) as pdf:
        root = pdf.Root
        # Ensure AcroForm exists
        if "/AcroForm" not in root:
            root.AcroForm = pdf.make_indirect(pikepdf.Dictionary())
        acro = root.AcroForm

        # Signature dictionary (Contents as hex string; ByteRange as a long String placeholder)
        sig_dict = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/Sig"),
            "/Filter": pikepdf.Name("/Adobe.PPKLite"),
            "/SubFilter": pikepdf.Name("/adbe.pkcs7.detached"),
            "/Contents": pikepdf.String(f"<{hex_zeros}>"),
            # store ByteRange as a String placeholder (so it occupies fixed bytes in file)
            "/ByteRange": pikepdf.String(br_placeholder_text),
            "/Reason": pikepdf.String("Signed by script"),
        })

        # Create an invisible widget annotation for signature (first page)
        widget = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/Annot"),
            "/Subtype": pikepdf.Name("/Widget"),
            "/FT": pikepdf.Name("/Sig"),
            "/Rect": pikepdf.Array([0, 0, 0, 0]),
            "/F": 4,
            "/T": pikepdf.String("Signature1"),
            "/V": pdf.make_indirect(sig_dict)
        })

        fields = acro.get("/Fields", pikepdf.Array())
        fields.append(pdf.make_indirect(widget))
        acro["/Fields"] = fields
        acro["/SigFlags"] = 3  # indicate signatures exist

        # Save without stream compression to avoid placeholder length changes
        pdf.save(out_pdf, linearize=False, compress_streams=False)
    print(f"[+] Created interim PDF with exact raw placeholder ({reserve_len} bytes): {out_pdf}")

def find_placeholder_offsets(interim_path, reserve_len):
    b = Path(interim_path).read_bytes()
    # Find "/Contents <" then '>' and measure hex length
    m2 = re.search(b"/Contents\\s*<", b)
    if not m2:
        raise ValueError("Couldn't find /Contents placeholder.")
    start = m2.end()
    end = b.find(b">", start)
    if end == -1:
        raise ValueError("Malformed /Contents placeholder.")
    length = end - start
    expected = reserve_len * 2
    if length < expected:
        raise ValueError(f"Placeholder length mismatch: found {length}, expected {expected}")
    contents_token_start = start - 1  # include '<'
    contents_token_end = end + 1      # include '>'
    br1_len = contents_token_start
    br2_start = contents_token_end
    br2_len = len(b) - br2_start

    # Also find the ByteRange placeholder span in the original bytes (start/end indices)
    # our placeholder is textual "/ByteRange [ 0000000000 ... ]", so search for "/ByteRange"
    br_pattern = re.compile(rb"/ByteRange\s*\[.*?\]")
    m_br = br_pattern.search(b)
    if not m_br:
        raise ValueError("Couldn't find /ByteRange placeholder in interim PDF.")
    br_placeholder_span = (m_br.start(0), m_br.end(0))

    return {
        "file_bytes": b,
        "contents_token_start": contents_token_start,
        "contents_token_end": contents_token_end,
        "br": (0, br1_len, br2_start, br2_len),
        "reserve_hex_len": length,
        "br_placeholder_span": br_placeholder_span
    }

def build_tbs_bytes(file_bytes, br):
    br1_start, br1_len, br2_start, br2_len = br
    part1 = file_bytes[br1_start: br1_start + br1_len]
    part2 = file_bytes[br2_start: br2_start + br2_len]
    return part1 + part2

def create_pkcs7_with_openssl(tbs_bytes, out_der_path, hash_alg="sha256"):
    # write tbs bytes to temp file
    tmp_in = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(tbs_bytes)
            tf.flush()
            tmp_in = tf.name

        # Use -md <alg> for compatibility with OpenSSL 1.1/3.x
        cmd = [
            OPENSSL_BIN, "cms", "-sign",
            "-in", tmp_in,
            "-signer", SIGNER_CERT,
            "-inkey", PRIVATE_KEY,
            "-outform", "DER",
            "-out", out_der_path,
            "-binary",
            "-md", hash_alg
        ]
        if CHAIN_PEM and Path(CHAIN_PEM).exists():
            cmd += ["-certfile", CHAIN_PEM]

        print("[*] Running OpenSSL:", " ".join(cmd))
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode != 0:
            stderr = res.stderr.decode(errors="ignore")
            print("[ERROR] OpenSSL CMS failed:")
            print(stderr)
            raise SystemExit("OpenSSL cms failed")
        print("[+] PKCS#7 DER created:", out_der_path)
        return out_der_path
    finally:
        if tmp_in and Path(tmp_in).exists():
            try:
                os.unlink(tmp_in)
            except Exception:
                pass

def insert_der_and_fix_byterange(interim_path, signed_path, der_path, offsets_info):
    """
    Insert the DER (hex) into the original file bytes between '<' and '>' (placeholder),
    then replace the ByteRange array in-place (keeping same placeholder length) so
    offsets remain valid.
    """
    b = offsets_info["file_bytes"]
    cstart = offsets_info["contents_token_start"]
    cend = offsets_info["contents_token_end"]
    br = offsets_info["br"]
    reserve_hex_len = offsets_info["reserve_hex_len"]
    br_placeholder_span = offsets_info["br_placeholder_span"]

    der = Path(der_path).read_bytes()
    der_hex = der.hex().upper()
    if len(der_hex) > reserve_hex_len:
        raise ValueError(f"DER too big ({len(der_hex)} hex chars) for reserved {reserve_hex_len} hex chars.")
    # pad with zeros to exactly the reserved hex length
    padded_hex = der_hex + ("0" * (reserve_hex_len - len(der_hex)))

    # Build new_bytes: put padded hex between '<' and '>'
    new_bytes = b[:cstart+1] + padded_hex.encode() + b[cend:]

    # Compute byte range values using original positions (these are still valid since we replaced with same-length hex)
    br1_start, br1_len, br2_start, br2_len = br
    byte_range_values = [0, br1_len, br2_start, br2_len]

    # Replace the ByteRange placeholder at the exact original span (in new_bytes)
    br_start_idx, br_end_idx = br_placeholder_span
    orig_br_text = b[br_start_idx:br_end_idx]
    if b"/ByteRange" not in orig_br_text:
        raise ValueError("Sanity check failed: expected /ByteRange in original placeholder span.")

    # Build replacement string and pad it to exactly the same length as the original placeholder
    br_repl = f"/ByteRange [ {byte_range_values[0]} {byte_range_values[1]} {byte_range_values[2]} {byte_range_values[3]} ]".encode()
    orig_len = br_end_idx - br_start_idx
    if len(br_repl) > orig_len:
        raise ValueError("Replacement ByteRange text is longer than original placeholder; increase placeholder size.")
    br_repl_padded = br_repl + (b" " * (orig_len - len(br_repl)))

    # Now write new_bytes with in-place replacement of the ByteRange placeholder span
    final_bytes = new_bytes[:br_start_idx] + br_repl_padded + new_bytes[br_end_idx:]

    # Write final PDF
    Path(signed_path).write_bytes(final_bytes)
    print("[+] Wrote signed PDF:", signed_path)

# ---- Main flow ----
def main():
    ensure_files_exist()
    # 1) create interim.pdf with placeholder (big reserve)
    add_sig_field_with_placeholder(INPUT_PDF, INTERIM_PDF, CONTENTS_RESERVE)

    # 2) find offsets and byte ranges
    offsets = find_placeholder_offsets(INTERIM_PDF, CONTENTS_RESERVE)
    print(f"[*] Found placeholder offsets: {offsets['contents_token_start']} - {offsets['contents_token_end']} (hex length {offsets['reserve_hex_len']})")
    # 3) build tbs bytes (ByteRange excluding /Contents area)
    tbs = build_tbs_bytes(offsets["file_bytes"], offsets["br"])
    print(f"[*] To-be-signed length: {len(tbs)} bytes")

    # 4) create PKCS#7 using OpenSSL (SignedData with signedAttrs: messageDigest & signingTime)
    der_path = str(Path(INTERIM_PDF).with_suffix(".der"))
    create_pkcs7_with_openssl(tbs, der_path, hash_alg=HASH_ALG)

    # 5) insert DER (hex-encoded) into placeholder and update ByteRange
    insert_der_and_fix_byterange(INTERIM_PDF, SIGNED_PDF, der_path, offsets)

    print("\n=== Done ===")
    print("Signed file:", SIGNED_PDF)
    print("PKCS#7 (DER):", der_path)
    print(f"Hash algorithm: {HASH_ALG.upper()}, RSA padding: PKCS#1 v1.5 (OpenSSL CMS default).")

if __name__ == "__main__":
    main()
