import streamlit as st
import tempfile
from google.cloud import vision
from google.oauth2 import service_account
import openai
from docx import Document
from pdf2image import convert_from_path
import os

# === Streamlit Config ===
st.set_page_config(page_title="📄 Legal Document Decoder", layout="wide")
st.title("📤 Upload Legal PDF → 🔍 OCR → 🤖 GPT-4 → 📄 Word Export")

# === Load API Keys ===
openai.api_key = st.secrets["OPENAI_API_KEY"]
CREDENTIAL_PATH = "/mount/src/legal-doc-ai/gcloud_key.json"
credentials = service_account.Credentials.from_service_account_file(CREDENTIAL_PATH)
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# === File Upload ===
uploaded_file = st.file_uploader("Upload a scanned legal PDF file", type=["pdf"])
if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    st.success("✅ File uploaded. Extracting text via OCR...")

    # Convert PDF to images
    images = convert_from_path(pdf_path)
    full_text = ""

    for img in images:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
            img.save(tmp_img.name)
            with open(tmp_img.name, "rb") as img_file:
                content = img_file.read()
                image = vision.Image(content=content)
                response = vision_client.document_text_detection(image=image)
                full_text += response.full_text_annotation.text + "\n"

    st.text_area("📃 Extracted OCR Text", full_text, height=300)

    # === GPT-4 Legal Analysis ===
    if st.button("🧠 Analyze with GPT-4"):
        st.info("Running GPT-4...")
        prompt = f"""
You are a legal assistant. Extract structured information from this legal document.

Return a JSON object with these fields:
- Agreement Type
- Parties Involved
- Effective Date
- Jurisdiction
- Monetary Amounts
- Duration
- Key Clauses

Document:
{full_text}
"""
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You extract structured legal data from OCR text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        output = response.choices[0].message.content.strip()
        st.code(output, language="json")

        # Save output to Word
        doc = Document()
        doc.add_heading("Legal Document Summary", level=1)
        doc.add_paragraph(output)

        doc_path = os.path.join(tempfile.gettempdir(), "Legal_Summary.docx")
        doc.save(doc_path)

        with open(doc_path, "rb") as f:
            st.download_button("⬇️ Download Word Document", f, file_name="Legal_Summary.docx")
