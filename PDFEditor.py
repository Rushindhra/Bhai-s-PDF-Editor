import streamlit as st
import fitz  # PyMuPDF
import io
import datetime
import re

# ---------- helpers ----------
def text_width(text, fontsize=10, fontname="helv"):
    """Robust width measurement across PyMuPDF versions."""
    try:
        return fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
    except Exception:
        # fallback approximation (Helvetica-ish average width ≈ 0.55 * fontsize per char)
        return fontsize * 0.55 * len(text)

def scale_font_to_fit(target_width, text, base_fontsize=10, fontname="helv", min_fs=8, max_fs=14):
    w = text_width(text, fontsize=base_fontsize, fontname=fontname)
    if w <= 0:
        return base_fontsize
    fs = base_fontsize * (target_width / w)
    return max(min_fs, min(max_fs, fs))

# ---------------- PDF Processing ----------------
def replace_text_in_pdf(pdf_bytes, old_roll, new_roll,
                        replace_name=False, old_name="", new_name="",
                        replace_date=False, new_date="",
                        footer_margin=120, header_margin=120):
    """
    - Always replace roll number in footer (exact match, same coordinates).
    - Optionally replace name in footer.
    - Optionally replace ONLY the numeric date after 'Date:' in the header.
    - Date font auto-scales to fit original date box.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    replacements = 0

    for page in doc:
        rect = page.rect
        footer_area = fitz.Rect(rect.x0, rect.y1 - footer_margin, rect.x1, rect.y1)
        header_area = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + header_margin)

        # --- Replace Roll Number (footer) ---
        if old_roll.strip():
            for inst in page.search_for(old_roll, clip=footer_area):
                replacements += 1
                page.add_redact_annot(inst, fill=(1, 1, 1))
                page.apply_redactions()
                x, y = inst.x0, inst.y1 - 2
                page.insert_text((x, y), new_roll,
                                 fontsize=10, fontname="helv", color=(0, 0, 0))

        # --- Replace Name (footer, optional) ---
        if replace_name and old_name.strip() and new_name.strip():
            for inst in page.search_for(old_name, clip=footer_area):
                replacements += 1
                page.add_redact_annot(inst, fill=(1, 1, 1))
                page.apply_redactions()
                x, y = inst.x0, inst.y1 - 2
                page.insert_text((x, y), new_name,
                                 fontsize=10, fontname="helv", color=(0, 0, 0))

        # --- Replace Date (header, optional) ---
        if replace_date and new_date.strip():
            # 1) Preferred: word-based detection — find "Date:" then the next word is the date
            words = page.get_text("words", clip=header_area)
            # sort by block, line, word order so "next" means visually next
            words.sort(key=lambda w: (w[5], w[6], w[7]))  # (block, line, word_no)

            did_replace_on_page = False
            for i, w in enumerate(words):
                token = (w[4] or "").strip().lower()
                if token == "date:" and i + 1 < len(words):
                    # next word is the numeric date (expected)
                    date_word = words[i + 1]
                    date_text = (date_word[4] or "").strip()
                    # sanity check: look like dd-mm-yyyy or dd/mm/yyyy
                    if re.fullmatch(r"\d{2}[-/]\d{2}[-/]\d{4}", date_text):
                        # redact ONLY the numeric date box
                        x0, y0, x1, y1 = date_word[0], date_word[1], date_word[2], date_word[3]
                        date_rect = fitz.Rect(x0, y0, x1, y1)
                        page.add_redact_annot(date_rect, fill=(1, 1, 1))
                        page.apply_redactions()

                        # auto-scale font to fit original date box width
                        target_w = date_rect.width
                        fs = scale_font_to_fit(target_w, new_date, base_fontsize=10, fontname="helv")
                        page.insert_text((x0, y1 - 2), new_date, fontsize=fs, fontname="helv", color=(0, 0, 0))
                        replacements += 1
                        did_replace_on_page = True

            # 2) Fallback: pattern search on the whole "Date: dd-mm-yyyy" then only replace the numeric part
            if not did_replace_on_page:
                header_text = page.get_text("text", clip=header_area)
                m = re.search(r"(Date:\s*)(\d{2}[-/]\d{2}[-/]\d{4})", header_text, flags=re.IGNORECASE)
                if m:
                    full_match = m.group(0)   # "Date: 13-08-2025"
                    prefix = m.group(1)       # "Date: "
                    # find the visual box of the whole match
                    for inst in page.search_for(full_match, clip=header_area):
                        # compute a sub-rect for just the numeric date by shifting x0 by prefix width
                        base_fs = 10
                        prefix_w = text_width(prefix, fontsize=base_fs, fontname="helv")
                        date_x0 = inst.x0 + prefix_w
                        date_rect = fitz.Rect(date_x0, inst.y0, inst.x1, inst.y1)

                        page.add_redact_annot(date_rect, fill=(1, 1, 1))
                        page.apply_redactions()

                        fs = scale_font_to_fit(date_rect.width, new_date, base_fontsize=base_fs, fontname="helv")
                        page.insert_text((date_x0, inst.y1 - 2), new_date, fontsize=fs, fontname="helv", color=(0, 0, 0))
                        replacements += 1

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
        <p style="color:white;text-align:center;margin:0;">Update roll numbers, names, and header dates with precision</p>
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

# --- Date Replacement (optional) ---
st.subheader("📅 Date Replacement (Optional)")
replace_date = st.checkbox("Replace Date in Header?")
new_date = ""
if replace_date:
    picked_date = st.date_input("Pick new date", value=datetime.date.today())
    # Keep format consistent with typical lab headers
    new_date = picked_date.strftime("%d-%m-%Y")

# --- Action Button ---
if st.button("🔄 Replace in PDF"):
    if uploaded is None:
        st.error("Please upload a PDF file.")
    elif not old_roll.strip() or not new_roll.strip():
        st.error("Both old and new roll numbers are required.")
    else:
        with st.spinner("Processing PDF..."):
            buf, count = replace_text_in_pdf(
                uploaded.read(),
                old_roll.strip(), new_roll.strip(),
                replace_name, old_name.strip(), new_name.strip(),
                replace_date, new_date.strip()
            )

        if count == 0:
            st.warning("⚠️ No matches found.")
        else:
            st.success(f"✅ Replaced {count} occurrence(s).")

        st.download_button(
            label="⬇️ Download updated PDF",
            data=buf,
            file_name="updated_pdf.pdf",
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
