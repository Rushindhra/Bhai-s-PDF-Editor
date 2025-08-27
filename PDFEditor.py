import streamlit as st
import fitz  # PyMuPDF
import io

# ---------------- PDF Processing ----------------
def replace_footer_text_in_pdf(pdf_bytes, old_roll, new_roll,
                               replace_name=False, old_name="", new_name="", footer_margin=120):
    """
    Replace roll number (always) and optionally name in the footer of each page.
    Keeps replacements at the same coordinates as old ones.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    replacements = 0

    for page in doc:
        rect = page.rect
        footer_area = fitz.Rect(rect.x0, rect.y1 - footer_margin, rect.x1, rect.y1)

        # --- Replace Roll Number ---
        roll_instances = page.search_for(old_roll, clip=footer_area)
        for inst in roll_instances:
            replacements += 1
            page.add_redact_annot(inst, fill=(1, 1, 1))
            page.apply_redactions()
            x, y = inst.x0, inst.y1 - 2
            page.insert_text((x, y), new_roll,
                             fontsize=10, fontname="helv", color=(0, 0, 0))

        # --- Replace Name (if checkbox is ticked) ---
        if replace_name and old_name.strip() and new_name.strip():
            name_instances = page.search_for(old_name, clip=footer_area)
            for inst in name_instances:
                replacements += 1
                page.add_redact_annot(inst, fill=(1, 1, 1))
                page.apply_redactions()
                x, y = inst.x0, inst.y1 - 2
                page.insert_text((x, y), new_name,
                                 fontsize=10, fontname="helv", color=(0, 0, 0))

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
        <p style="color:white;text-align:center;margin:0;">Update roll numbers (and names) in PDF footers with precision</p>
    </div>
""", unsafe_allow_html=True)


# --- File Upload ---
uploaded = st.file_uploader("📂 Upload PDF file", type=["pdf"])

# --- Roll Number Fields ---
st.subheader("🔢 Roll Number Replacement")
col1, col2 = st.columns(2)
with col1:
    old_roll = st.text_input("Old roll number", placeholder="e.g., 23071A12##")
with col2:
    new_roll = st.text_input("New roll number", placeholder="e.g., 23071A12##")

# --- Name Replacement (optional) ---
st.subheader("👤 Name Replacement (Optional)")
replace_name = st.checkbox("Replace Name in Footer?")
old_name, new_name = "", ""
if replace_name:
    col3, col4 = st.columns(2)
    with col3:
        old_name = st.text_input("Old name", placeholder="e.g., Bhai")
    with col4:
        new_name = st.text_input("New name", placeholder="e.g., Don")

# --- Action Button ---
if st.button("🔄 Replace in Footer"):
    if uploaded is None:
        st.error("Please upload a PDF file.")
    elif not old_roll.strip() or not new_roll.strip():
        st.error("Both old and new roll numbers are required.")
    else:
        with st.spinner("Processing PDF..."):
            buf, count = replace_footer_text_in_pdf(
                uploaded.read(),
                old_roll.strip(), new_roll.strip(),
                replace_name, old_name.strip(), new_name.strip()
            )

        if count == 0:
            st.warning("⚠️ No matches found in the footer area.")
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
        Developed with ❤️ by <b>IT - A</b> <br>
        <b>Bhai's PDF Editor</b> © 2025
    </div>
""", unsafe_allow_html=True)


