import json
import os
import streamlit as st

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Literature Search — Keyword", layout="wide")

# -----------------------------
# Config
# -----------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "example-bib.json")


# -----------------------------
# Helpers
# -----------------------------
@st.cache_data
def load_papers(path=DATA_PATH):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["references"]


def norm_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [str(v)]


def norm_authors(p):
    return [str(x) for x in norm_list(p.get("authors")) if str(x).strip()]


def norm_keywords(p):
    return [str(x) for x in norm_list(p.get("keywords")) if str(x).strip()]


def paper_url(p):
    url = p.get("url") or p.get("link") or p.get("pdf")
    if url:
        return str(url).strip()
    doi = (p.get("doi") or "").strip()
    if doi:
        return f"https://doi.org/{doi}"
    return ""


def searchable_text(p):
    authors = " ".join(norm_authors(p))
    keywords = " ".join(norm_keywords(p))
    return " ".join(
        [
            str(p.get("title", "")),
            str(p.get("abstract", "")),
            authors,
            str(p.get("journal", "")),
            str(p.get("venue", "")),
            str(p.get("doi", "")),
            keywords,
        ]
    ).lower()


def toggle_save(pid, saved_ids):
    if pid is None:
        return
    if pid in saved_ids:
        saved_ids.discard(pid)
    else:
        saved_ids.add(pid)


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
<style>
div.stButton > button{
    border-radius: 999px;
    padding: 0.18rem 0.55rem;
}
.meta-chip {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    margin: 0.1rem 0.25rem 0.1rem 0;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.12);
    font-size: 0.85rem;
    opacity: 0.95;
}
.small-muted {
    opacity: 0.7;
    font-size: 0.9rem;
}
</style>
""",
    unsafe_allow_html=True,
)


def render_paper_card_keyword(p, saved_ids, key_prefix=""):
    """Paper card without AI summary tab (keyword-only app)."""
    pid = p.get("id")
    title = p.get("title", "(no title)")
    year = p.get("year", "")
    venue = p.get("journal", "") or p.get("venue", "")
    authors = ", ".join(norm_authors(p))
    url = paper_url(p)
    doi = (p.get("doi") or "").strip()
    kw = norm_keywords(p)
    abstract = (p.get("abstract") or "").strip()

    saved = pid in saved_ids
    star = "★" if saved else "☆"
    save_text = "Saved" if saved else "Save"

    cols = st.columns([0.12, 0.88], vertical_alignment="top")
    with cols[0]:
        btn_key = f"{key_prefix}save_{pid}_{hash(title)}"
        if st.button(f"{star} {save_text}", key=btn_key, use_container_width=True):
            toggle_save(pid, saved_ids)
            st.rerun()

    with cols[1]:
        st.markdown(f"**{title}**")
        if year or venue:
            st.caption(f"{year} • {venue}")
        if authors:
            st.write(authors)
        if url:
            st.write(url)
        if doi:
            st.write(f"**DOI:** {doi}")
        if kw:
            preview = ", ".join(kw[:12])
            more = f" … (+{len(kw)-12})" if len(kw) > 12 else ""
            st.caption("Tags: " + preview + more)

        tab_meta, tab_abs = st.tabs(["Metadata", "Abstract"])
        with tab_meta:
            st.json(p)
        with tab_abs:
            if abstract:
                st.write(abstract)
            else:
                st.caption("No abstract.")

    st.divider()


def render_saved_panel(papers_by_id):
    st.markdown("---")
    st.markdown(f"### Saved papers ({len(st.session_state.saved_ids)})")

    saved = [papers_by_id[pid] for pid in st.session_state.saved_ids if pid in papers_by_id]
    saved.sort(key=lambda p: (p.get("year") is None, p.get("year", 0)), reverse=True)

    if not saved:
        st.caption("No saved papers yet. Click ☆ Save on any paper card to save it.")
        return

    a1, a2, a3 = st.columns([0.34, 0.33, 0.33], vertical_alignment="center")
    with a1:
        export_obj = {"references": saved}
        st.download_button(
            "Download saved papers (JSON)",
            data=json.dumps(export_obj, ensure_ascii=False, indent=2),
            file_name="saved-papers.json",
            mime="application/json",
            key="download_saved",
            use_container_width=True,
        )
    with a2:
        if st.button("Clear all saved", use_container_width=True):
            st.session_state.saved_ids = set()
            st.rerun()
    with a3:
        st.caption("Saved items persist during this session.")

    for i, p in enumerate(saved):
        render_paper_card_keyword(p, st.session_state.saved_ids, key_prefix=f"saved_{i}_")


# -----------------------------
# Load data & session state
# -----------------------------
papers = load_papers()
papers_by_id = {p.get("id"): p for p in papers if p.get("id") is not None}

if "saved_ids" not in st.session_state:
    st.session_state.saved_ids = set()
if "query" not in st.session_state:
    st.session_state.query = ""
if "kw_ran" not in st.session_state:
    st.session_state.kw_ran = False
if "kw_results" not in st.session_state:
    st.session_state.kw_results = []

# -----------------------------
# UI
# -----------------------------
st.markdown("## Literature Search — Keyword")

top = st.container()
with top:
    c1, c2 = st.columns([0.7, 0.3], vertical_alignment="bottom")
    with c1:
        st.text_input(
            "Search query (keyword matching uses this)",
            key="query",
            placeholder="Type keywords or a short phrase",
        )
    with c2:
        max_kw = st.slider("Keyword results", 5, 200, 30)

    with st.expander("Keyword filters", expanded=False):
        years = [p.get("year") for p in papers if isinstance(p.get("year"), int)]
        if years:
            y_min, y_max = min(years), max(years)
            year_range = st.slider("Year range", y_min, y_max, (y_min, y_max))
        else:
            year_range = None
        only_with_doi = st.checkbox("Only with DOI", value=False)

st.markdown("### Keyword matching")

b1, b2 = st.columns([0.5, 0.5])
with b1:
    run_kw = st.button("Run keyword search", type="primary", use_container_width=True)
with b2:
    clear_kw = st.button("Clear keyword results", use_container_width=True)

if clear_kw:
    st.session_state.kw_ran = False
    st.session_state.kw_results = []
    st.rerun()

if run_kw:
    q = (st.session_state.query or "").strip()
    if not q:
        st.warning("Please enter a query first.")
    else:
        ql = q.lower()
        results = []
        for p in papers:
            if year_range and isinstance(p.get("year"), int):
                if not (year_range[0] <= p["year"] <= year_range[1]):
                    continue
            if only_with_doi and not p.get("doi"):
                continue
            if ql in searchable_text(p):
                results.append(p)

        st.session_state.kw_results = results
        st.session_state.kw_ran = True
        st.rerun()

if not st.session_state.kw_ran:
    st.caption('Click “Run keyword search” to view matches.')
else:
    results = st.session_state.kw_results
    st.caption(f"Found {len(results)} matches. Showing up to {max_kw}.")
    with st.container(height=650):
        for i, p in enumerate(results[:max_kw]):
            render_paper_card_keyword(p, st.session_state.saved_ids, key_prefix=f"kw_{i}_")

render_saved_panel(papers_by_id)
