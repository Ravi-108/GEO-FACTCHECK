import pdfplumber

pdf = pdfplumber.open(r'c:\Users\rairo\OneDrive\Desktop\geo_factcheck\Assessment_Product Management Trainee.pdf')
for i, p in enumerate(pdf.pages):
    text = p.extract_text() or ""
    print(f"--- PAGE {i+1} ---")
    print(text)
    print()
pdf.close()
