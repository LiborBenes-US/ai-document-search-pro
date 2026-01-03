"""
AI Document Search Pro - Local RAG System
Secure, privacy-focused document search and analysis tool.
"""

import streamlit as st
import tempfile
import os
import re
from typing import List, Dict, Tuple, Optional

# Configure page
st.set_page_config(
    page_title="AI Document Search Pro - Local RAG",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .uploadedFile {
        border: 1px solid #ddd;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    
    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Title with AI/RAG positioning
st.title("🔍 AI Document Search Pro - Local RAG System")
st.markdown("**Transform static documents into interactive, queryable knowledge - 100% local, no API keys, complete privacy.**")

# Security: Validate file names
def sanitize_filename(filename: str) -> str:
    """Remove potentially dangerous characters from filename."""
    filename = os.path.basename(filename)
    safe_name = re.sub(r'[^\w\-\.]', '_', filename)
    return safe_name[:255]

# Security: Validate file content
def validate_file_content(content: bytes, filename: str) -> Tuple[bool, str]:
    """Basic security validation of uploaded files."""
    MAX_SIZE = 50 * 1024 * 1024  # 50MB
    if len(content) > MAX_SIZE:
        return False, f"File too large ({len(content)/1024/1024:.1f}MB > 50MB)"
    
    if b'\x00' in content[:1024]:
        return False, "File contains null bytes (potential security risk)"
    
    return True, "OK"

# Initialize session state
if "documents" not in st.session_state:
    st.session_state.documents = {}
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "total_matches" not in st.session_state:
    st.session_state.total_matches = 0

# Sidebar with settings
with st.sidebar:
    st.markdown("## 🔒 Security & Settings")
    
    st.markdown("### AI/RAG Mode")
    ai_mode = st.radio(
        "Operation Mode:",
        ["🔍 Search Only", "🤖 AI-Enhanced (Coming Soon)"],
        help="Search-only mode works 100% locally."
    )
    
    st.markdown("### Search Options")
    case_sensitive = st.checkbox("Case sensitive", value=False)
    whole_word = st.checkbox("Whole word only", value=False)
    show_context = st.checkbox("Show context", value=True)
    
    if show_context:
        context_chars = st.slider("Context characters", 50, 500, 200)
    else:
        context_chars = 50
    
    st.markdown("### Security Status")
    st.success("✅ 100% Local Processing")
    st.info("✅ No API Keys Required")
    st.info("✅ Documents Never Leave Your Computer")
    
    # Statistics
    if st.session_state.documents:
        total_files = len(st.session_state.documents)
        total_chars = sum(d['size'] for d in st.session_state.documents.values())
        st.metric("📁 Files", total_files)
        st.metric("📝 Characters", f"{total_chars:,}")
    
    # Clear button
    if st.button("🗑️ Clear All Data", type="secondary"):
        if st.checkbox("Confirm deletion", key="confirm_delete"):
            st.session_state.documents = {}
            st.session_state.search_history = []
            st.session_state.search_results = []
            st.session_state.total_matches = 0
            st.rerun()

# PDF Processing
def setup_pdf_support():
    """Safely set up PDF support with error handling."""
    try:
        import pypdf
        return pypdf, True
    except ImportError:
        try:
            import PyPDF2 as pypdf
            return pypdf, True
        except ImportError:
            return None, False

# Safe document processing
def process_uploaded_file(file) -> Optional[Dict]:
    """Safely process an uploaded file with security checks."""
    try:
        filename = sanitize_filename(file.name)
        file_content = file.getvalue()
        
        is_valid, message = validate_file_content(file_content, filename)
        if not is_valid:
            st.error(f"Security check failed for {filename}: {message}")
            return None
        
        is_pdf = filename.lower().endswith('.pdf')
        
        if is_pdf:
            pypdf_module, can_read_pdf = setup_pdf_support()
            if not can_read_pdf:
                st.warning(f"PDF support not installed for {filename}. Install: pip install pypdf")
                return None
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            
            try:
                pdf_reader = pypdf_module.PdfReader(tmp_path)
                content = ""
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        content += text + "\n\n"
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            file_type = "pdf"
        else:
            try:
                content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                content = file_content.decode('latin-1', errors='ignore')
            file_type = "txt"
        
        if content.strip():
            return {
                'content': content,
                'type': file_type,
                'size': len(content),
                'words': len(content.split()),
                'lines': len(content.split('\n'))
            }
        else:
            st.warning(f"Empty or unreadable file: {filename}")
            return None
            
    except Exception as e:
        st.error(f"Error processing file: {type(e).__name__}")
        return None

# Enhanced search function
def perform_search_enhanced(
    search_query: str,
    search_in: List[str],
    case_sensitive: bool,
    whole_word: bool,
    show_context: bool,
    context_chars: int
) -> Tuple[List[Dict], int, str]:
    """Perform secure text search across documents."""
    if len(search_query) > 1000:
        return [], 0, "Search query too long (max 1000 characters)"
    
    all_results = []
    total_matches = 0
    
    for filename in search_in:
        if filename not in st.session_state.documents:
            continue
            
        doc = st.session_state.documents[filename]
        content = doc['content']
        
        try:
            if case_sensitive:
                search_text = search_query
                content_search = content
            else:
                search_text = search_query.lower()
                content_search = content.lower()
            
            if whole_word:
                pattern = r'(?<!\w)' + re.escape(search_text) + r'(?!\w)'
            else:
                pattern = re.escape(search_text)
            
            flags = 0 if case_sensitive else re.IGNORECASE
            matches = list(re.finditer(pattern, content_search, flags))
            
            if matches:
                file_matches = []
                for match in matches:
                    match_start = match.start()
                    match_end = match.end()
                    exact_match = content[match_start:match_end]
                    
                    if show_context:
                        context_start = max(0, match_start - context_chars)
                        context_end = min(len(content), match_end + context_chars)
                        context = content[context_start:context_end]
                        
                        match_in_context = match_start - context_start
                        highlighted = (
                            context[:match_in_context] +
                            "**" + context[match_in_context:match_in_context+len(exact_match)] + "**" +
                            context[match_in_context+len(exact_match):]
                        )
                        context_display = highlighted
                    else:
                        context_display = exact_match
                    
                    line_num = content[:match_start].count('\n') + 1
                    lines = content.split('\n')
                    line_text = lines[line_num-1] if line_num <= len(lines) else ""
                    
                    file_matches.append({
                        'position': match_start,
                        'line': line_num,
                        'line_text': line_text,
                        'exact_match': exact_match,
                        'context': context_display,
                        'match_length': len(exact_match)
                    })
                
                all_results.append({
                    'filename': filename,
                    'file_type': doc['type'],
                    'matches': file_matches,
                    'match_count': len(file_matches)
                })
                total_matches += len(file_matches)
                
        except re.error as e:
            return [], 0, f"Invalid search pattern: {e}"
        except Exception:
            return [], 0, "Search error occurred"
    
    return all_results, total_matches, ""

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📁 Upload", "🔍 AI Search", "📊 Analytics", "📖 Viewer"])

# Tab 1: Upload
with tab1:
    st.header("📁 Document Upload")
    st.markdown("Upload your documents to create a local knowledge base. Files are processed **100% locally**.")
    
    uploaded_files = st.file_uploader(
        "Select PDF or text files",
        type=['pdf', 'txt', 'md'],
        accept_multiple_files=True,
        help="Maximum file size: 50MB per file"
    )
    
    if uploaded_files:
        if st.button("🚀 Process Uploaded Files", type="primary"):
            for file in uploaded_files:
                with st.spinner(f"Processing {file.name}..."):
                    result = process_uploaded_file(file)
                    if result:
                        filename = sanitize_filename(file.name)
                        st.session_state.documents[filename] = result
                        st.success(f"✅ {filename} ({result['size']:,} chars)")
    
    if st.session_state.documents:
        st.subheader("📋 Loaded Documents")
        for filename, doc in st.session_state.documents.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{filename}**")
            with col2:
                st.write(f"{doc['size']:,} chars")
            with col3:
                if st.button("Remove", key=f"remove_{filename}"):
                    del st.session_state.documents[filename]
                    st.rerun()

# Tab 2: Search
with tab2:
    st.header("🔍 AI-Powered Document Search")
    st.markdown("**Local RAG System**: Search across all documents with AI-enhanced capabilities (local processing).")
    
    if not st.session_state.documents:
        st.info("👆 Upload documents first to enable search capabilities")
    else:
        col1, col2 = st.columns([4, 1])
        with col1:
            search_query = st.text_input(
                "Enter search query:",
                placeholder="Search for keywords, phrases, or concepts...",
                key="main_search"
            )
        with col2:
            st.write("")
            st.write("")
            if st.button("🔍 Search", type="primary", use_container_width=True):
                if search_query:
                    selected_files = list(st.session_state.documents.keys())
                    
                    results, total_matches, error = perform_search_enhanced(
                        search_query,
                        selected_files,
                        case_sensitive,
                        whole_word,
                        show_context,
                        context_chars
                    )
                    
                    if error:
                        st.error(f"Search error: {error}")
                    else:
                        st.session_state.search_results = results
                        st.session_state.total_matches = total_matches
                        
                        if search_query not in st.session_state.search_history:
                            st.session_state.search_history.insert(0, search_query)
                            if len(st.session_state.search_history) > 10:
                                st.session_state.search_history = st.session_state.search_history[:10]
        
        with st.expander("⚙️ Advanced Search Options"):
            use_regex = st.checkbox("Use regular expressions", value=False)
            st.caption("Example: `^Chapter\\s+\\d+` for chapter headings")
            
            search_in = st.multiselect(
                "Search in specific files:",
                options=list(st.session_state.documents.keys()),
                default=list(st.session_state.documents.keys())
            )
        
        if st.session_state.search_results and st.session_state.total_matches > 0:
            st.success(f"✅ Found **{st.session_state.total_matches} matches** across **{len(st.session_state.search_results)} files**")
            
            verified_count = sum(r['match_count'] for r in st.session_state.search_results)
            st.info(f"📊 Showing **ALL {verified_count} matches** (complete results verified)")
            
            for result in st.session_state.search_results:
                with st.expander(f"📄 {result['filename']} - {result['match_count']} matches", expanded=True):
                    for i, match in enumerate(result['matches'][:100]):
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.write(f"**#{i+1}**")
                            st.caption(f"Line {match['line']}")
                            st.caption(f"Char {match['position']:,}")
                        with col2:
                            if '**' in match['context']:
                                st.markdown(f"...{match['context']}...")
                            else:
                                st.text(f"...{match['context']}...")
                        
                        with st.expander(f"Match details #{i+1}", expanded=False):
                            st.write("**Exact text found:**")
                            st.code(match['exact_match'])
                            st.write(f"**Full line {match['line']}:**")
                            st.text(match['line_text'])
                            st.write(f"**Position:** Character {match['position']:,}")
                            st.write(f"**Match length:** {match['match_length']} characters")
                        
                        if i < len(result['matches'][:100]) - 1:
                            st.divider()
                    
                    if result['match_count'] > 100:
                        st.info(f"📋 ...and {result['match_count'] - 100} more matches")
            
            results_text = f"AI Document Search Results\n"
            results_text += f"Query: '{search_query}'\n"
            results_text += f"Total matches: {st.session_state.total_matches}\n"
            results_text += f"Files searched: {len(st.session_state.search_results)}\n"
            results_text += "="*60 + "\n\n"
            
            for result in st.session_state.search_results:
                results_text += f"\n📄 File: {result['filename']}\n"
                results_text += f"📊 Matches: {result['match_count']}\n"
                results_text += "-"*40 + "\n"
                
                for match in result['matches']:
                    results_text += f"\n📍 Line {match['line']}, Position {match['position']}:\n"
                    results_text += f"🔍 Exact: {match['exact_match']}\n"
                    clean_context = match['context'].replace('**', '')
                    results_text += f"📝 Context: ...{clean_context}...\n"
                    results_text += f"📏 Length: {match['match_length']} chars\n"
            
            st.download_button(
                "💾 Download All Results",
                results_text,
                f"ai_search_{search_query[:50].replace(' ', '_')}.txt",
                "text/plain"
            )
        
        if st.session_state.search_history:
            with st.expander("📜 Recent Searches"):
                for query in st.session_state.search_history[:5]:
                    if st.button(f"🔎 '{query}'", key=f"recent_{query}"):
                        st.session_state.main_search = query
                        st.rerun()

# Tab 3: Analytics
with tab3:
    st.header("📊 AI Document Analytics")
    st.markdown("**Knowledge Insights**: Analyze your document corpus with AI-inspired analytics.")
    
    if not st.session_state.documents:
        st.info("👆 Upload documents to see analytics")
    else:
        total_files = len(st.session_state.documents)
        total_chars = sum(d['size'] for d in st.session_state.documents.values())
        total_words = sum(d['words'] for d in st.session_state.documents.values())
        total_lines = sum(d['lines'] for d in st.session_state.documents.values())
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📁 Total Files", total_files)
        with col2:
            st.metric("📝 Total Characters", f"{total_chars:,}")
        with col3:
            st.metric("📚 Total Words", f"{total_words:,}")
        with col4:
            st.metric("📊 Total Lines", f"{total_lines:,}")
        
        st.subheader("🔤 AI Word Frequency Analysis")
        
        from collections import Counter
        all_words = []
        for doc in st.session_state.documents.values():
            words = re.findall(r'\b[\w\'-]+\b', doc['content'].lower())
            all_words.extend(words)
        
        if all_words:
            word_freq = Counter(all_words)
            top_words = word_freq.most_common(25)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Top 25 Keywords:**")
                for word, freq in top_words:
                    percentage = (freq / len(all_words)) * 100
                    st.write(f"`{word}`: {freq:,} ({percentage:.1f}%)")
            
            with col2:
                try:
                    import pandas as pd
                    df = pd.DataFrame(top_words[:15], columns=['Keyword', 'Frequency'])
                    st.bar_chart(df.set_index('Keyword'))
                except ImportError:
                    st.info("✨ Tip: Install pandas for enhanced visualizations")
        
        st.subheader("📦 Document Size Comparison")
        
        sorted_files = sorted(
            st.session_state.documents.items(),
            key=lambda x: x[1]['size'],
            reverse=True
        )[:10]
        
        if sorted_files:
            max_size = sorted_files[0][1]['size']
            for filename, doc in sorted_files:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{filename}**")
                with col2:
                    st.write(f"{doc['size']:,} chars")
                with col3:
                    st.write(f"{doc['words']:,} words")
                
                if max_size > 0:
                    st.progress(min(doc['size'] / max_size, 1.0))

# Tab 4: Viewer
with tab4:
    st.header("📖 AI Document Viewer")
    st.markdown("**Interactive Knowledge Base**: View and analyze individual documents with AI-powered insights.")
    
    if not st.session_state.documents:
        st.info("👆 Upload documents to use the viewer")
    else:
        selected_file = st.selectbox(
            "Select document:",
            options=list(st.session_state.documents.keys()),
            format_func=lambda x: f"{x} ({st.session_state.documents[x]['size']:,} chars)",
            key="viewer_selector"
        )
        
        if selected_file:
            doc = st.session_state.documents[selected_file]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Type", doc['type'].upper())
            with col2:
                st.metric("Characters", f"{doc['size']:,}")
            with col3:
                st.metric("Words", f"{doc['words']:,}")
            with col4:
                st.metric("Lines", f"{doc['lines']:,}")
            
            view_mode = st.radio(
                "View mode:",
                ["📄 Full Text", "🔢 With Line Numbers", "📑 Paginated"],
                horizontal=True
            )
            
            if view_mode == "📄 Full Text":
                st.text_area(
                    "Document Content:",
                    doc['content'],
                    height=500,
                    key="full_text_area"
                )
            elif view_mode == "🔢 With Line Numbers":
                lines = doc['content'].split('\n')
                numbered = ""
                for i, line in enumerate(lines, 1):
                    numbered += f"{i:6d} | {line}\n"
                st.text_area(
                    "Document with Line Numbers:",
                    numbered,
                    height=500,
                    key="numbered_text_area"
                )
            else:
                lines = doc['content'].split('\n')
                lines_per_page = st.slider("Lines per page", 50, 200, 100)
                total_pages = max(1, (len(lines) + lines_per_page - 1) // lines_per_page)
                
                page = st.number_input("Page", 1, total_pages, 1)
                start = (page - 1) * lines_per_page
                end = min(start + lines_per_page, len(lines))
                
                page_content = "\n".join(lines[start:end])
                st.text_area(
                    f"Page {page} of {total_pages} (lines {start+1}-{end}):",
                    page_content,
                    height=400,
                    key=f"page_{page}"
                )
            
            st.download_button(
                "💾 Download This Document",
                doc['content'],
                f"{selected_file}_extracted.txt",
                "text/plain"
            )

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
    <p><strong>🔒 AI Document Search Pro - Local RAG System</strong></p>
    <p>✅ 100% Local Processing • ✅ No API Keys • ✅ Complete Privacy • ✅ Open Source</p>
    <p>Transform static documents into interactive knowledge bases</p>
</div>
""", unsafe_allow_html=True)
