# generate_test_file.py
import re
from core.pii_detector import _verhoeff_check, _luhn_check

# Let's find a valid Aadhaar
aadhaar = ""
for i in range(100000000000, 999999999999):
    s = str(i)
    if _verhoeff_check(s):
        aadhaar = f"{s[:4]} {s[4:8]} {s[8:]}"
        break

# Let's find a valid Credit Card (Visa prefix 4)
cc = ""
for i in range(4111111111111110, 4111111111111120):
    s = str(i)
    if _luhn_check(s):
        cc = s
        break

content = f"""COMPLIANCE SENTINEL TEST DOCUMENT - CONFIDENTIAL AND PROPRIETARY
This document contains sensitive training data for verification.

1. Identity Details:
Aadhaar Number: {aadhaar}
PAN Card: ABCDE1234F

2. Contact Info:
Email: support@protecciodata.com
Phone: 9876543210

3. Financial Records:
Credit Card: {cc}
Bank Account: A/C 987654321012
IFSC Code: SBIN0001234

4. Developer Keys & Access:
Employee ID: EMP-12345
API Key: AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6

5. Business Information:
This is a highly restricted TRADE SECRET. Any distribution violates NDA agreements.
"""

with open("sample_compliance.txt", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Generated sample_compliance.txt with Aadhaar: {aadhaar} and Credit Card: {cc}")
