"""
Streamlit dashboard for Docto Trace storage audits.
Built with a modern, clean light-themed aesthetic.
"""
import sys
import json
from pathlib import Path

import pandas as pd

try:
    import streamlit as st
except ImportError:
    print("Streamlit not installed. Run: pip install docto-trace-storage[ui]")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Data Loading
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_path: str):
    path = Path(file_path)
    if not path.exists():
        st.error(f"Report file not found: {path}")
        st.stop()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading report: {e}")
        st.stop()

def human_size(bytes_val: int | float) -> str:
    bytes_float = float(bytes_val)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_float < 1024.0:
            return f"{bytes_float:.1f} {unit}"
        bytes_float /= 1024.0
    return f"{bytes_float:.1f} EB"

# -----------------------------------------------------------------------------
# Aesthetic & Layout Setup
# -----------------------------------------------------------------------------
def apply_custom_css():
    st.set_page_config(
        page_title="Docto Trace | Dashboard", 
        page_icon="🔍", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
        <style>
            /* Global Adjustments */
            .stApp {
                background-color: #111827;
            }
            .block-container {
                padding-top: 2rem !important;
                padding-bottom: 2rem !important;
                max-width: 1400px;
            }
            header {visibility: hidden;}
            #MainMenu {visibility: hidden;}
            
            /* Custom CSS for Folder Cards */
            .folder-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            .folder-card {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 1rem;
                display: flex;
                flex-direction: column;
                gap: 1rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                transition: box-shadow 0.2s;
            }
            .folder-card:hover {
                box-shadow: 0 10px 15px rgba(0, 0, 0, 0.5);
            }
            .folder-image-bg {
                background-color: #111827;
                border-radius: 8px;
                height: 120px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .folder-yellow-icon {
                font-size: 4rem;
            }
            .folder-info {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }
            .folder-name-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .folder-name-text {
                font-size: 0.95rem;
                font-weight: 600;
                color: #F9FAFB;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .folder-dots {
                color: #D1D5DB;
                font-weight: bold;
                letter-spacing: 2px;
                cursor: pointer;
            }
            .folder-meta-text {
                font-size: 0.8rem;
                color: #D1D5DB;
            }
            
            /* Custom CSS for File Tables */
            .table-container {
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #4B5563;
                border-radius: 8px;
                background-color: #1F2937;
            }
            .file-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 0;
            }
            .file-table th {
                position: sticky;
                top: 0;
                background-color: #374151;
                z-index: 10;
                text-align: left;
                padding: 1rem;
                color: #F9FAFB;
                font-weight: 600;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                border-bottom: 2px solid #4B5563;
            }
            .file-row {
                background-color: transparent;
                border-bottom: 1px solid #374151;
                transition: background-color 0.2s;
            }
            .file-row:hover {
                background-color: #374151;
            }
            .file-row td {
                padding: 1rem;
                color: #F3F4F6;
                font-size: 0.95rem;
                vertical-align: middle;
            }
            .file-name-container {
                display: flex;
                align-items: center;
                gap: 1rem;
            }
            .file-icon-box {
                background-color: #312E81;
                color: #818CF8;
                height: 40px;
                width: 40px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
            }
            .file-name-text {
                font-weight: 600;
                color: #F9FAFB;
                max-width: 300px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            /* Custom CSS for Data Storage Bar */
            .storage-card {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                margin-bottom: 2rem;
            }
            .storage-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1.5rem;
            }
            .storage-header h3 {
                margin: 0 !important;
                font-size: 1.25rem;
            }
            .storage-badge {
                border: 1px solid #374151;
                background-color: #111827;
                padding: 0.35rem 0.75rem;
                border-radius: 8px;
                font-size: 0.85rem;
                font-weight: 600;
                color: #F9FAFB;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .storage-legend {
                display: flex;
                justify-content: space-between;
                margin-bottom: 1rem;
            }
            .legend-item {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }
            .legend-title {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.9rem;
                font-weight: 600;
                color: #D1D5DB;
            }
            .legend-dot {
                width: 14px;
                height: 7px;
                border-radius: 4px;
            }
            .legend-meta {
                font-size: 0.85rem;
                color: #D1D5DB;
                padding-left: 1.5rem;
            }
            .storage-bar-container {
                display: flex;
                height: 16px;
                border-radius: 8px;
                overflow: hidden;
            }
            .bar-segment {
                height: 100%;
            }

            /* Typography */
            h1, h2, h3, h4, h5, h6 {
                color: #F9FAFB !important;
                font-weight: 700 !important;
            }
            .subtitle {
                color: #D1D5DB;
                font-size: 0.95rem;
                margin-top: -10px;
                margin-bottom: 2rem;
            }

            /* Better Markdown text contrast */
            [data-testid="stMarkdownContainer"] p, 
            [data-testid="stMarkdownContainer"] li {
                color: #F9FAFB !important;
                line-height: 1.6;
                font-size: 1.1rem;
            }
            [data-testid="stMarkdownContainer"] blockquote {
                border-left: 4px solid #4F46E5;
                padding-left: 1rem;
                margin-left: 0;
                color: #D1D5DB;
                font-style: italic;
            }
            [data-testid="stMarkdownContainer"] strong {
                color: #FFFFFF !important;
                font-weight: 700;
            }
            /* Make Markdown headings smaller in reports */
            [data-testid="stMarkdownContainer"] h2 {
                font-size: 1.3rem !important;
                margin-top: 1.5rem !important;
                margin-bottom: 0.75rem !important;
            }
            [data-testid="stMarkdownContainer"] h3 {
                font-size: 1.15rem !important;
                margin-top: 1.25rem !important;
                margin-bottom: 0.5rem !important;
            }
            [data-testid="stMarkdownContainer"] h4 {
                font-size: 1.1rem !important;
                margin-top: 1rem !important;
                margin-bottom: 0.5rem !important;
            }
            /* Styling for Markdown-rendered tables (like the AI report) */
            [data-testid="stMarkdownContainer"] table {
                width: 100%;
                border-collapse: collapse;
                margin: 1rem 0;
                border: 1px solid #4B5563;
                background-color: #1F2937;
                color: #F9FAFB;
            }
            [data-testid="stMarkdownContainer"] th {
                background-color: #374151 !important;
                color: #F9FAFB !important;
                padding: 0.75rem;
                text-align: left;
                border: 1px solid #4B5563 !important;
            }
            [data-testid="stMarkdownContainer"] td {
                padding: 0.75rem;
                border: 1px solid #4B5563 !important;
                color: #F3F4F6 !important;
            }
            [data-testid="stMarkdownContainer"] tr:nth-child(even) {
                background-color: #111827;
            }
        </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Components
# -----------------------------------------------------------------------------

def get_file_type_info(filename: str):
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext in ['pdf']: return '📄', 'Document'
    if ext in ['doc', 'docx', 'txt', 'rtf']: return '📝', 'Document'
    if ext in ['xls', 'xlsx', 'csv']: return '📊', 'Spreadsheet'
    if ext in ['ppt', 'pptx']: return '📽️', 'Presentation'
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'svg', 'heic', 'webp']: return '🖼️', 'Images'
    if ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']: return '🎥', 'Video'
    if ext in ['mp3', 'wav', 'ogg', 'm4a']: return '🎵', 'Audio'
    if ext in ['zip', 'rar', 'tar', 'gz', '7z']: return '📦', 'Archive'
    return '📄', 'File'

def render_file_table(items, kind="zombie"):
    if kind == "zombie":
        columns = ["File Name", "Size File", "Type File", "Last Modified", "Location"]
    else:
        columns = ["File Name", "Size File", "Type File", "Copies", "Wasted Space"]

    html = '<div class="table-container"><table class="file-table"><thead><tr>'
    for col in columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'
    
    for item in items:
        html += '<tr class="file-row">'
        
        name = item.get("name", "Unknown File")
        if kind == "duplicate" and item.get("file_names"):
            name = item["file_names"][0]
        
        icon, ftype = get_file_type_info(name)
        
        html += f'''
        <td>
            <div class="file-name-container">
                <div class="file-icon-box">{icon}</div>
                <div class="file-name-text" title="{name}">{name}</div>
            </div>
        </td>
        '''
        
        if kind == "zombie":
            size = human_size(item.get("size_bytes", 0))
            last_mod = item.get("last_modified", "Unknown")[:10] if item.get("last_modified") else "Unknown"
            location = item.get("path", "Unknown")
            loc_disp = location if len(location) < 40 else f"...{location[-37:]}"
            html += f'<td>{size}</td><td>{ftype}</td><td>{last_mod}</td><td><div title="{location}">{loc_disp}</div></td>'
        else:
            size_raw = item.get("size_bytes_per_copy", 0)
            size = human_size(size_raw)
            wasted = human_size(item.get("wasted_bytes", 0))
            copies = len(item.get("file_names", []))
            html += f'<td>{size}</td><td>{ftype}</td><td><span style="font-weight:600;">{copies}</span></td><td><span style="color:#EF4444; font-weight:600;">{wasted}</span></td>'
            
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

def render_overview(data: dict):
    # Header
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown("<h1>Docto Trace</h1>", unsafe_allow_html=True)
        st.markdown("<div class='subtitle'>Mapping your company's digital chaos to build an organized memory ready for humans and AI agents.</div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(
            """
            <div style='text-align: right; margin-top: 1.5rem;'>
                <a href='https://docto.com.co/' target='_blank' style='color: #4F46E5; text-decoration: none; font-weight: 500; font-size: 0.95rem; margin-right: 1.5rem;'>Website</a>
                <a href='https://github.com/Docto-Studio' target='_blank' style='color: #4F46E5; text-decoration: none; font-weight: 500; font-size: 0.95rem;'>GitHub</a>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # Extract Executive Summary if it exists in the AI report
    ai_readiness = data.get("ai_readiness", {})
    report_text = ""
    exec_summary = ""
    
    if isinstance(ai_readiness, dict) and ai_readiness.get("ai_analysis_report"):
        report_text = ai_readiness["ai_analysis_report"]
        # Look for "Executive Summary:" at the start
        if "**Executive Summary:**" in report_text:
            # Match the new title '## Readiness Assessment'
            parts = report_text.split("## Readiness Assessment", 1)
            if len(parts) > 1:
                exec_summary = parts[0].replace("**Executive Summary:**", "").strip()
                report_text = "## Readiness Assessment" + parts[1]
    
    if exec_summary:
        st.markdown(f"> {exec_summary}")
        st.markdown("<br>", unsafe_allow_html=True)

    # Storage Horizontal Bar
    quota = data.get("quota")
    tree = data.get("storage_tree", {})
    
    if quota and quota.get("limit_bytes", 0) > 0:
        limit = quota["limit_bytes"]
        drive_b = quota.get("drive_bytes", 0)
        trash_b = quota.get("trash_bytes", 0)
        other_b = quota.get("other_bytes", 0)
        free_b = max(0, limit - (drive_b + trash_b + other_b))
        
        # Percentages
        p_drive = (drive_b / limit) * 100
        p_trash = (trash_b / limit) * 100
        p_other = (other_b / limit) * 100
        p_free = (free_b / limit) * 100
        p_used = ((limit - free_b) / limit) * 100
        
        storage_html = f"""
        <div class="storage-card">
            <div class="storage-header">
                <h3>Data Storage</h3>
                <div class="storage-badge"><span style="color:#8B5CF6;">📊</span> {human_size(limit - free_b)} of {human_size(limit)} Used ({p_used:.0f}%)</div>
            </div>
            <div class="storage-legend">
                <div class="legend-item">
                    <div class="legend-title"><div class="legend-dot" style="background:#F472B6;"></div>Drive Files</div>
                    <div class="legend-meta">{human_size(drive_b)} • {p_drive:.0f}%</div>
                </div>
                <div class="legend-item">
                    <div class="legend-title"><div class="legend-dot" style="background:#A78BFA;"></div>Gmail & Photos</div>
                    <div class="legend-meta">{human_size(other_b)} • {p_other:.0f}%</div>
                </div>
                <div class="legend-item">
                    <div class="legend-title"><div class="legend-dot" style="background:#34D399;"></div>Trash</div>
                    <div class="legend-meta">{human_size(trash_b)} • {p_trash:.0f}%</div>
                </div>
                <div class="legend-item">
                    <div class="legend-title"><div class="legend-dot" style="background:#E5E7EB;"></div>Free Storage</div>
                    <div class="legend-meta">{human_size(free_b)} • {p_free:.0f}%</div>
                </div>
            </div>
            <div class="storage-bar-container">
                <div class="bar-segment" style="width: {p_drive}%; background:#F472B6;"></div>
                <div class="bar-segment" style="width: {p_other}%; background:#A78BFA;"></div>
                <div class="bar-segment" style="width: {p_trash}%; background:#34D399;"></div>
                <div class="bar-segment" style="width: {p_free}%; background:#E5E7EB;"></div>
            </div>
        </div>
        """
        st.markdown(storage_html, unsafe_allow_html=True)
    else:
        # Fallback if no quota
        st.info(f"Total Scanned Size: **{human_size(tree.get('total_size_bytes', 0))}** (across {tree.get('total_files', 0):,} files).")

    st.markdown("<br>", unsafe_allow_html=True)

    # Autonomous AI Report (Only if executed)
    if report_text:
        # Display entropy score if available
        entropy = ai_readiness.get("naming_entropy_score")
        if entropy is not None:
            score_color = "#34D399" if entropy > 70 else "#FBBF24" if entropy > 40 else "#EF4444"
            st.markdown(f"**Naming Entropy Score**: <span style='color:{score_color}; font-weight:bold;'>{entropy}/100.0</span>", unsafe_allow_html=True)
            
        st.markdown(report_text)
        st.markdown("<br><br>", unsafe_allow_html=True)

    # Top Folders Cards
    st.markdown("### Top 10 Largest Folders")
    insights = data.get("insights", {})
    top_folders = insights.get("top_folders", [])
    
    if top_folders:
        cards_html = '<div class="folder-grid">'
        svg_icon = '<svg viewBox="0 0 24 24" fill="#FBBF24" style="width: 64px; height: 64px;"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>'
        for folder in top_folders[:10]:
            fname = folder.get("name", "Unknown")
            fsize = folder.get("total_size_human", "0 B")
            fcount = folder.get("file_count", 0)
            cards_html += f'<div class="folder-card"><div class="folder-image-bg">{svg_icon}</div><div class="folder-info"><div class="folder-name-row"><span class="folder-name-text" title="{fname}">{fname}</span></div><div class="folder-meta-text">{fcount} files • {fsize}</div></div></div>'
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)
    else:
        st.write("No folder data available.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Recent / Problematic Files
    st.markdown("### Identifying Digital Dementia")
    
    st.markdown("<br><h4>🧟 Zombie Files</h4>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Orphaned and forgotten files hindering your organization's AI-readiness.</div>", unsafe_allow_html=True)
    zombies = data.get("zombies", [])
    if zombies:
        render_file_table(zombies, kind="zombie")
    else:
        st.success("Your Drive is extremely clean! Zero zombie files detected.")
            
    st.markdown("<br><h4>♻️ Duplicate Groups</h4>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Redundant data creating noise in your Centralized Memory.</div>", unsafe_allow_html=True)
    dupes = data.get("duplicates", [])
    if dupes:
        render_file_table(dupes, kind="duplicate")
    else:
        st.success("Great job! No duplicate groups found.")

    st.markdown("<br><br><hr style='border-top: 1px solid #374151; margin-bottom: 2rem;'>", unsafe_allow_html=True)
    footer_html = """
    <div style="text-align: center; padding: 2rem 0; color: #D1D5DB; font-size: 0.95rem; max-width: 800px; margin: 0 auto;">
        <div style="font-size: 1.2rem; font-weight: 700; color: #F9FAFB; margin-bottom: 0.5rem;">Discover the Docto Ecosystem</div>
        <div style="margin-bottom: 1.5rem; line-height: 1.5;">
            Building the ecosystem to turn any company’s chaos of files and data from any source into a centralized, organized memory ready to be used by humans and AI agents.
        </div>
        <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
            <a href="https://docto.com.co/" target="_blank" style="background-color: #4F46E5; color: #FFFFFF; font-weight: 600; padding: 0.6rem 1.2rem; border-radius: 8px; text-decoration: none; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);">Visit our Website</a>
            <a href="https://github.com/Docto-Studio" target="_blank" style="background-color: #1F2937; color: #F9FAFB; font-weight: 600; padding: 0.6rem 1.2rem; border-radius: 8px; text-decoration: none; border: 1px solid #4B5563; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);">Explore our GitHub</a>
        </div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------
def main():
    apply_custom_css()
    
    args = sys.argv
    report_path = None
    if len(args) > 1 and not args[-1].startswith("-"):
        report_path = args[-1]
    
    if not report_path:
        st.error("Report path not provided. Did you launch via `docto-trace ui`?")
        st.stop()
        
    data = load_data(report_path)
    render_overview(data)

if __name__ == "__main__":
    main()
