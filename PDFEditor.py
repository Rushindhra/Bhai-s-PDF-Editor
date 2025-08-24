import streamlit as st
import fitz  # PyMuPDF
import io

# ---------------- PDF Processing ----------------
def replace_footer_text_in_pdf(pdf_bytes, old_text, new_text, footer_margin=120):
    """
    Replace old_text with new_text in the footer area of each page in a PDF.
    Places new text at the same coordinates as the old one.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    replacements = 0

    for page in doc:
        rect = page.rect
        footer_area = fitz.Rect(rect.x0, rect.y1 - footer_margin, rect.x1, rect.y1)

        instances = page.search_for(old_text, clip=footer_area)
        for inst in instances:
            replacements += 1
            page.add_redact_annot(inst, fill=(1, 1, 1))
            page.apply_redactions()

            # Place new roll number at the same X/Y position
            x, y = inst.x0, inst.y1 - 2
            page.insert_text(
                (x, y),
                new_text,
                fontsize=10,
                fontname="helv",
                color=(0, 0, 0),
            )

    out = io.BytesIO()
    doc.save(out)
    doc.close()
    out.seek(0)
    return out, replacements


# ---------------- Streamlit Layout ----------------
st.set_page_config(page_title="Bhai's PDF Editor", page_icon="📑", layout="centered")

# --- Custom Header ---
st.markdown("""
    <div style="background-color:#2E86C1;padding:15px;border-radius:10px;margin-bottom:20px;">
        <h2 style="color:white;text-align:center;margin:0;">📑 Bhai's PDF Editor</h2>
        <p style="color:white;text-align:center;margin:0;">Update roll numbers in PDF footers with precision</p>
    </div>
""", unsafe_allow_html=True)


st.markdown("### Upload your PDF and replace the roll number in the footer")

uploaded = st.file_uploader("📂 Upload PDF file", type=["pdf"])

col1, col2 = st.columns(2)
with col1:
    old_roll = st.text_input("Old roll number (in footer)", value="23071A1234")
with col2:
    new_roll = st.text_input("New roll number", placeholder="e.g., 23071A1201")

if st.button("🔄 Replace in Footer"):
    if uploaded is None:
        st.error("Please upload a PDF file.")
    elif not old_roll.strip() or not new_roll.strip():
        st.error("Both old and new roll numbers are required.")
    else:
        with st.spinner("Processing PDF..."):
            buf, count = replace_footer_text_in_pdf(uploaded.read(),
                                                    old_roll.strip(),
                                                    new_roll.strip())

        if count == 0:
            st.warning("⚠️ No roll number found in the footer area. "
                       "It may be split into chunks inside the PDF.")
        else:
            st.success(f"✅ Replaced {count} occurrence(s) in the footer.")

        st.download_button(
            label="⬇️ Download updated PDF",
            data=buf,
            file_name="updated_footer.pdf",
            mime="application/pdf",
        )


# --- Custom Footer ---
st.markdown("""
    <hr style="margin-top:40px;margin-bottom:10px;">
    <div style="text-align:center; color:gray; font-size:14px;">
        Developed with ❤️ by <b>Rushindhra Marri</b> <br>
        <b>Roll Number PDF Editor</b> © 2025
    </div>
""", unsafe_allow_html=True)
