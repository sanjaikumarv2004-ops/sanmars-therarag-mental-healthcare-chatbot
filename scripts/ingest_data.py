import os
import re
import pdfplumber

# PATHS
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PDF_DIR = os.path.join(BASE_DIR, 'data', 'raw_pdfs')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')

def clean_text(text):
    if not text:
        return ""
        
    # 1. Fix hyphenated words broken across lines
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    # 2. Remove specific academic noise
    noise_patterns = [
        r'Sensors 2022.*', r'JETIR.*', r'IJARSCT.*', 
        r'https?://\S+', r'DOI:.*', r'©.*', 
        r'page \d+', r'^\d+$'
    ]
    
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

    # 3. Remove Citations [12]
    text = re.sub(r'\[\d+(?:-\d+)?\]', '', text)
    
    # 4. Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def process_pdfs():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    files = [f for f in os.listdir(RAW_PDF_DIR) if f.endswith('.pdf')]
    print(f"--- Starting Processing for {len(files)} PDFs ---\n")

    for filename in files:
        file_path = os.path.join(RAW_PDF_DIR, filename)
        output_filename = filename.replace('.pdf', '.txt')
        output_path = os.path.join(PROCESSED_DIR, output_filename)
        
        try:
            full_text = ""
            print(f"Processing: {filename}...", end=" ")
            
            # Open with pdfplumber (more robust than pypdf)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        full_text += extracted + "\n"
            
            # DIAGNOSTIC: Check if we actually got text
            raw_char_count = len(full_text)
            
            if raw_char_count < 100:
                print(f"⚠️ WARNING: Found only {raw_char_count} characters. This PDF might be an image/scan.")
            else:
                # Only clean and save if we have text
                cleaned_content = clean_text(full_text)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                print(f"✔ Success. Extracted {len(cleaned_content)} characters.")

        except Exception as e:
            print(f"\n❌ CRITICAL ERROR on {filename}: {e}")

if __name__ == "__main__":
    process_pdfs()