"""
SEO Outline Generator v6
New features:
  #1  Jina Reader fallback  — r.jina.ai/URL khi crawl thường bị block (Cloudflare)
  #2  Editable outline      — st.data_editor cho phép sửa H1/H2/H3 trực tiếp trước export
  #3  Target H2 count       — competitor_avg H2 → constraint trong prompt
"""

import streamlit as st
import httpx
import json
import re
import time
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import median
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
import pandas as pd

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Tạo Outline SEO",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main .block-container { padding-top:1.2rem; max-width:1100px; }
h1 { font-size:1.6rem !important; margin-bottom:0 !important; }

.sec { border-radius:8px; border:1px solid #e2e8f0; margin:5px 0; overflow:hidden; }
.sec-comp { border-left:4px solid #3b82f6; }
.sec-ai   { border-left:4px solid #10b981; }
.sec-hyb  { border-left:4px solid #8b5cf6; }
.sec-faq  { border-left:4px solid #f59e0b; }
.sec-head {
    display:flex; align-items:center; gap:8px; padding:9px 14px;
    background:#fff; font-weight:600; font-size:0.93rem; color:#0f172a;
}
.sec-body { background:#f8fafc; padding:4px 14px 8px; border-top:1px solid #f1f5f9; }
.h3-row   { display:flex; align-items:flex-start; gap:6px; padding:4px 0;
            font-size:0.86rem; color:#374151; }
.h3-arrow { color:#94a3b8; flex-shrink:0; margin-top:1px; }

.badge { font-size:0.6rem; font-weight:700; padding:2px 7px;
         border-radius:10px; white-space:nowrap; flex-shrink:0; }
.b-comp { background:#dbeafe; color:#1e40af; }
.b-ai   { background:#dcfce7; color:#166534; }
.b-hyb  { background:#ede9fe; color:#5b21b6; }
.b-faq  { background:#fef3c7; color:#92400e; }
.b-num  { background:#f1f5f9; color:#475569; }
.b-lang { background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; }
.b-warn { background:#fef9c3; color:#713f12; }
.b-jina { background:#fdf4ff; color:#7e22ce; border:1px solid #e9d5ff; }

.h1-card {
    background:linear-gradient(135deg,#eff6ff 0%,#f0fdf4 100%);
    border:1px solid #bfdbfe; border-radius:10px;
    padding:1rem 1.25rem; margin-bottom:0.75rem;
}
.h1-label { font-size:0.65rem; font-weight:700; text-transform:uppercase;
            letter-spacing:.8px; color:#3b82f6; margin-bottom:4px; }
.h1-text  { font-size:1.1rem; font-weight:700; color:#0f172a; margin-bottom:6px; }
.meta-text { font-size:0.82rem; color:#64748b; }

.pills { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 14px; }
.pill { background:#f8fafc; border:1px solid #e2e8f0; border-radius:20px;
        padding:3px 11px; font-size:0.78rem; color:#475569; }
.pill b { color:#0f172a; }
.pill.words { background:#f0fdf4; border-color:#bbf7d0; color:#166534; }

.angles-card { background:#fefce8; border:1px solid #fde68a;
               border-radius:8px; padding:10px 14px; margin-bottom:10px; }
.angles-title { font-size:0.65rem; font-weight:700; text-transform:uppercase;
                letter-spacing:.7px; color:#92400e; margin-bottom:6px; }
.angle-tag { display:inline-block; background:#fff7ed; border:1px solid #fed7aa;
             color:#92400e; border-radius:4px; padding:2px 8px;
             font-size:0.78rem; margin:3px 3px 3px 0; }

.intent-banner { background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px;
                 padding:8px 14px; margin-bottom:10px; font-size:0.85rem; color:#1e40af; }

.wc-bar-wrap { background:#f1f5f9; border-radius:4px; height:6px; margin:4px 0 8px; overflow:hidden; }
.wc-bar { background:#10b981; height:6px; border-radius:4px; }

.dom-card { background:#fff; border:1px solid #e2e8f0; border-radius:7px;
            padding:8px 12px; margin-bottom:6px; font-size:0.85rem; }
.dom-card a { color:#2563eb; text-decoration:none; }

.hp { display:inline-block; padding:1px 6px; border-radius:3px;
      font-size:0.65rem; font-weight:700; margin-right:5px; vertical-align:middle; }
.hp-h1{background:#dbeafe;color:#1e40af} .hp-h2{background:#dcfce7;color:#166534}
.hp-h3{background:#fef9c3;color:#713f12} .hp-h4{background:#ffe4e6;color:#9f1239}

.sec-label { font-size:0.75rem; font-weight:700; color:#64748b;
             text-transform:uppercase; letter-spacing:.5px; margin:18px 0 6px; }

.stream-box { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;
              padding:1rem; font-family:monospace; font-size:0.8rem;
              color:#374151; white-space:pre-wrap; min-height:60px;
              max-height:200px; overflow-y:auto; }

.val-err { background:#fef2f2; border:1px solid #fca5a5; border-radius:8px;
           padding:10px 14px; font-size:0.85rem; color:#991b1b; margin:8px 0; }

/* edit mode toggle */
.edit-banner { background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px;
               padding:8px 14px; font-size:0.84rem; color:#1e40af; margin-bottom:12px; }

div[data-testid="stExpander"] { border:1px solid #e2e8f0 !important;
                                 border-radius:8px !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════
SOCIAL_DOMAINS = {
    "facebook.com","twitter.com","x.com","instagram.com","tiktok.com",
    "youtube.com","linkedin.com","pinterest.com","reddit.com","quora.com",
    "tumblr.com","snapchat.com","threads.net","vk.com","weibo.com",
    "t.me","telegram.org","wikipedia.org","wikimedia.org",
    "amazon.com","amazon.co.uk","ebay.com","aliexpress.com",
    "shopee.vn","lazada.vn","tiki.vn","sendo.vn",
}

BOILERPLATE_PATTERNS = re.compile(
    r"^(related (posts?|articles?|content)|you (may|might) (also )?(like|enjoy)|"
    r"share (this|article|post)|leave a (comment|reply)|subscribe|newsletter|"
    r"bài viết liên quan|có thể bạn thích|chia sẻ bài viết|"
    r"tags?:|category:|categories:|author:|about (the )?author|"
    r"table of contents?|mục lục|contents?|navigation|"
    r"advertisement|sponsored|quảng cáo|"
    r"comments?|bình luận|phản hồi|"
    r"search|tìm kiếm|menu|home|trang chủ)$",
    re.IGNORECASE,
)

CRAWL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}

# Feature #1: Jina Reader
JINA_BASE    = "https://r.jina.ai/"
JINA_HEADERS = {
    "Accept": "text/markdown",
    "X-Return-Format": "markdown",
}

MAX_WORKERS  = 6
CRAWL_MAX_MB = 3

def _bs4_parser() -> str:
    try:
        import lxml  # noqa
        return "lxml"
    except ImportError:
        return "html.parser"

BS4_PARSER = _bs4_parser()

INTENT_MODIFIERS = [
    (r"\blà gì\b","informational",2),(r"\bcách\b","how-to",2),
    (r"\bhướng dẫn\b","how-to",2),(r"\bso sánh\b","comparison",2),
    (r"\bnên mua\b","commercial",2),(r"\bgiá\b","commercial",1),
    (r"\btốt nhất\b","commercial",2),(r"\bđánh giá\b","review",2),
    (r"\breview\b","review",2),(r"\btop \d+\b","listicle",2),
    (r"\b\d+ cách\b","listicle",2),(r"\bkinh nghiệm\b","informational",1),
    (r"\blợi ích\b","informational",1),
    (r"\bwhat is\b","informational",2),(r"\bhow to\b","how-to",2),
    (r"\bguide\b","how-to",1),(r"\btutorial\b","how-to",2),
    (r"\bbest\b","commercial",2),(r"\btop \d+\b","listicle",2),
    (r"\b\d+ ways\b","listicle",2),(r"\b\d+ tips\b","listicle",2),
    (r"\bvs\.?\b","comparison",2),(r"\bcompare\b","comparison",2),
    (r"\bprice\b","commercial",1),(r"\bbuy\b","transactional",2),
    (r"\bcheap\b","transactional",1),(r"\bdiscount\b","transactional",1),
    (r"\bwhy\b","informational",1),(r"\bbenefits\b","informational",1),
    (r"\bexamples\b","informational",1),
]

INTENT_LABELS = {
    "informational": ("📚 Thông tin","#dbeafe","#1e40af"),
    "how-to":        ("🔧 Hướng dẫn","#dcfce7","#166534"),
    "listicle":      ("📋 Danh sách","#fef9c3","#713f12"),
    "commercial":    ("🛒 Thương mại","#ede9fe","#5b21b6"),
    "transactional": ("💳 Giao dịch","#fee2e2","#991b1b"),
    "review":        ("⭐ Đánh giá","#fff7ed","#92400e"),
    "comparison":    ("⚖️ So sánh","#f0fdf4","#166534"),
    "mixed":         ("🔀 Hỗn hợp","#f1f5f9","#475569"),
}

# ═══════════════════════════════════════════════════════════════════
# LANGUAGE + INTENT
# ═══════════════════════════════════════════════════════════════════

def detect_intent_from_modifier(kw: str) -> dict:
    scores: dict[str,int] = {}
    signals: list[str] = []
    k = kw.lower()
    for pat, intent, boost in INTENT_MODIFIERS:
        if re.search(pat, k):
            scores[intent] = scores.get(intent,0) + boost
            signals.append(re.sub(r"\\b|\(|\)|\?|\.", "", pat).strip())
    if not scores:
        return {"intent":"informational","confidence":"low","signals":[]}
    top  = max(scores, key=scores.get)
    conf = "high" if scores[top]>=3 else "medium" if scores[top]>=2 else "low"
    return {"intent":top,"confidence":conf,"signals":signals}

# ═══════════════════════════════════════════════════════════════════
# SERP
# ═══════════════════════════════════════════════════════════════════
def is_blocked(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().replace("www.","")
        return any(host==d or host.endswith("."+d) for d in SOCIAL_DOMAINS)
    except Exception:
        return False

def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.","")
    except Exception:
        return url

def _raise_dfs_error(resp: httpx.Response) -> None:
    if resp.status_code == 401:
        raise ValueError("❌ DataForSEO: Invalid credentials (401).")
    if resp.status_code == 402:
        raise ValueError("❌ DataForSEO: Insufficient balance (402). Top up at app.dataforseo.com.")
    if resp.status_code == 429:
        raise ValueError("❌ DataForSEO: Rate limit (429). Wait and retry.")
    if resp.status_code >= 500:
        raise ValueError(f"❌ DataForSEO: Server error ({resp.status_code}).")
    resp.raise_for_status()
    try:
        task = resp.json()["tasks"][0]
        if task.get("status_code") not in (20000,20100):
            raise ValueError(f"❌ DataForSEO task error: {task.get('status_message','unknown')}")
    except (KeyError,IndexError,json.JSONDecodeError):
        pass

def fetch_serp(keyword: str, login: str, password: str,
               location_code: int, language_code: str) -> list[dict]:
    resp = httpx.post(
        "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
        auth=(login,password),
        json=[{"keyword":keyword,"location_code":location_code,
               "language_code":language_code,"depth":20}],
        timeout=30,
    )
    _raise_dfs_error(resp)
    results = []
    try:
        for item in resp.json()["tasks"][0]["result"][0]["items"]:
            if item.get("type") != "organic":
                continue
            url = item.get("url","")
            if not url or is_blocked(url):
                continue
            results.append({
                "rank":        item.get("rank_absolute",99),
                "url":         url,
                "title":       item.get("title",""),
                "description": item.get("description",""),
            })
            if len(results) >= 5:
                break
    except (KeyError,IndexError,TypeError):
        pass
    return results

def intent_from_serp_titles(serp_results: list[dict]) -> dict:
    scores: dict[str,int] = {}
    for r in serp_results:
        title = (r.get("title") or "").lower()
        for pat, intent, _ in INTENT_MODIFIERS:
            if re.search(pat, title):
                scores[intent] = scores.get(intent,0) + 1
    if not scores:
        return {}
    return {"intent": max(scores,key=scores.get), "counts": scores}

# ═══════════════════════════════════════════════════════════════════
# CRAWL
# Strategy (in order):
#   1. DataForSEO On-Page instant_pages  — JS rendering, reliable, $0.00025/URL
#   2. DataForSEO content_parsing/live   — fallback if htags empty, $0.000125/URL
#   3. Direct HTTP + BeautifulSoup       — free, fast, blocked by Cloudflare
#   4. Jina Reader (r.jina.ai)           — last resort, free, handles Cloudflare
# ═══════════════════════════════════════════════════════════════════

# ── DFS On-Page helpers ───────────────────────────────────────────
def _dfs_instant_pages(url: str, login: str, password: str,
                       enable_js: bool = True) -> dict:
    """
    DataForSEO On-Page instant_pages — sync, returns htags + word_count.
    Supports JS rendering via enable_javascript=True (handles lazy-load headings).
    Cost: $0.00025/call.
    """
    resp = httpx.post(
        "https://api.dataforseo.com/v3/on_page/instant_pages",
        auth=(login, password),
        json=[{
            "url": url,
            "enable_javascript": enable_js,
            "load_resources": False,          # skip images/css — faster + cheaper
            "custom_js": "",
        }],
        timeout=45,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        item = data["tasks"][0]["result"][0]["items"][0]
        meta = item.get("meta", {}) or {}
        htags = meta.get("htags", {}) or {}
        # htags format: {"h1": ["text1"], "h2": ["text1","text2"], ...}
        headings: list[dict] = []
        for level in ("h1", "h2", "h3", "h4"):
            for text in (htags.get(level) or []):
                text = (text or "").strip()
                if not text or not (3 <= len(text) <= 250):
                    continue
                if BOILERPLATE_PATTERNS.match(text):
                    continue
                headings.append({"tag": level, "text": text})
        wc = (meta.get("content", {}) or {}).get("plain_text_word_count", 0) or 0
        return {"headings": headings, "word_count": wc,
                "status_code": item.get("status_code", 0)}
    except (KeyError, IndexError, TypeError):
        return {"headings": [], "word_count": 0, "status_code": 0}

def _dfs_content_parsing(url: str, login: str, password: str) -> dict:
    """
    DataForSEO content_parsing/live — structured content fallback.
    Useful when instant_pages returns empty htags on complex pages.
    Cost: $0.000125/call.
    """
    resp = httpx.post(
        "https://api.dataforseo.com/v3/on_page/content_parsing/live",
        auth=(login, password),
        json=[{"url": url, "markdown_view": False}],
        timeout=40,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        item      = data["tasks"][0]["result"][0]["items"][0]
        pc        = item.get("page_content", {}) or {}
        # Extract headings from content blocks
        headings: list[dict] = []
        for section in (pc.get("main_columns") or []):
            for block in (section.get("content") or []):
                btype = block.get("type", "")
                if btype in ("header", "title"):
                    text = (block.get("text") or block.get("content") or "").strip()
                    level_raw = block.get("level", 2)
                    try:
                        level = int(level_raw)
                    except (TypeError, ValueError):
                        level = 2
                    level = max(1, min(level, 4))
                    if text and 3 <= len(text) <= 250 and not BOILERPLATE_PATTERNS.match(text):
                        headings.append({"tag": f"h{level}", "text": text})
        wc = pc.get("text_word_count", 0) or 0
        return {"headings": headings, "word_count": wc}
    except (KeyError, IndexError, TypeError):
        return {"headings": [], "word_count": 0}

# ── Direct HTTP helpers (free, no API) ───────────────────────────
def _fetch_html(url: str, timeout: int) -> str:
    with httpx.Client(headers=CRAWL_HEADERS, timeout=timeout,
                      follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        raw = resp.content[:CRAWL_MAX_MB * 1024 * 1024]
        return raw.decode(resp.encoding or "utf-8", errors="replace")

def extract_headings_from_html(html: str) -> tuple[list[dict], int]:
    soup = BeautifulSoup(html, BS4_PARSER)
    for tag in soup(["script","style","nav","footer","header",
                     "aside","noscript","iframe","form"]):
        tag.decompose()
    headings = []
    for tag in soup.find_all(["h1","h2","h3","h4"]):
        text = tag.get_text(separator=" ", strip=True)
        if not text or not (3 <= len(text) <= 250):
            continue
        if BOILERPLATE_PATTERNS.match(text):
            continue
        headings.append({"tag": tag.name.lower(), "text": text})
    content_el = (
        soup.find("article") or soup.find("main") or
        soup.find(id=re.compile(r"content|main|post|article", re.I)) or
        soup.find(class_=re.compile(r"content|main|post|article|entry", re.I)) or
        soup.body
    )
    wc = len((content_el or soup).get_text(separator=" ", strip=True).split())
    return headings, wc

# ── Jina Reader (last resort) ─────────────────────────────────────
JINA_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

def _fetch_via_jina(url: str, timeout: int = 22) -> str:
    jina_url = JINA_BASE + url
    with httpx.Client(headers=JINA_HEADERS, timeout=timeout,
                      follow_redirects=True) as client:
        resp = client.get(jina_url)
        resp.raise_for_status()
        return resp.text

def extract_headings_from_markdown(md: str) -> tuple[list[dict], int]:
    headings = []
    for m in JINA_HEADING_RE.finditer(md):
        level = len(m.group(1))
        text  = m.group(2).strip()
        text  = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text  = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", text)
        text  = text.strip()
        if not text or not (3 <= len(text) <= 250):
            continue
        if BOILERPLATE_PATTERNS.match(text):
            continue
        headings.append({"tag": f"h{level}", "text": text})
    body_lines = [l for l in md.splitlines() if not l.startswith("#")]
    wc = len(" ".join(body_lines).split())
    return headings, wc

# ── Main crawl_one — 4-layer strategy ────────────────────────────
def crawl_one(url: str, t1: int, t2: int, use_jina_fallback: bool,
              dfs_login: str = "", dfs_password: str = "") -> dict:
    """
    4-layer crawl with fallback chain.
    Each layer records its method for display in UI.
    """
    base  = {"url": url, "headings": [], "word_count": 0,
             "error": None, "method": "direct"}
    errors: list[str] = []

    # ── Layer 1: DataForSEO instant_pages (JS rendering) ─────────
    if dfs_login and dfs_password:
        try:
            result = _dfs_instant_pages(url, dfs_login, dfs_password, enable_js=True)
            if result["headings"]:
                return {**base, **result, "status": "dfs", "method": "dfs"}
            errors.append(f"dfs_instant: empty htags (status={result['status_code']})")
        except Exception as e:
            errors.append(f"dfs_instant: {str(e)[:60]}")

        # ── Layer 2: DataForSEO content_parsing (fallback) ───────
        try:
            result2 = _dfs_content_parsing(url, dfs_login, dfs_password)
            if result2["headings"]:
                return {**base, **result2, "status": "dfs", "method": "dfs_content"}
            errors.append("dfs_content: no headings parsed")
        except Exception as e:
            errors.append(f"dfs_content: {str(e)[:60]}")

    # ── Layer 3: Direct HTTP ──────────────────────────────────────
    try:
        html = _fetch_html(url, t1)
        headings, wc = extract_headings_from_html(html)
        if headings:
            return {**base, "headings": headings, "word_count": wc,
                    "status": "ok", "method": "direct"}
    except Exception as e:
        errors.append(f"direct1: {str(e)[:60]}")

    time.sleep(0.3)
    try:
        html = _fetch_html(url, t2)
        headings, wc = extract_headings_from_html(html)
        if headings:
            return {**base, "headings": headings, "word_count": wc,
                    "status": "retry_ok", "method": "direct"}
        errors.append("direct2: empty headings")
    except Exception as e:
        errors.append(f"direct2: {str(e)[:60]}")

    # ── Layer 4: Jina Reader ──────────────────────────────────────
    if use_jina_fallback:
        try:
            md = _fetch_via_jina(url)
            headings, wc = extract_headings_from_markdown(md)
            if not headings:
                headings, wc = extract_headings_from_html(md)
            if headings:
                return {**base, "headings": headings, "word_count": wc,
                        "status": "jina", "method": "jina"}
            errors.append("jina: no headings")
        except Exception as e:
            errors.append(f"jina: {str(e)[:60]}")

    return {**base, "status": "fail", "error": " | ".join(errors[-3:])}

def crawl_all(serp_results, t1, t2, use_jina,
              dfs_login="", dfs_password="", on_done=None) -> list[dict]:
    out = [None]*len(serp_results)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        fmap = {
            ex.submit(crawl_one, r["url"], t1, t2, use_jina,
                      dfs_login, dfs_password): i
            for i, r in enumerate(serp_results)
        }
        for f in as_completed(fmap):
            i = fmap[f]
            out[i] = {**serp_results[i], **f.result()}
            if on_done:
                on_done(sum(1 for x in out if x), len(serp_results), out[i])
    return out

def competitor_word_count_stats(crawl_results: list[dict]) -> dict:
    counts = [r["word_count"] for r in crawl_results if r.get("word_count",0)>200]
    if not counts:
        return {}
    med = int(median(counts))
    return {"median":med,"min":min(counts),"max":max(counts),
            "target":int(med*1.15),"count":len(counts)}

# Feature #3: H2 count stats
def competitor_h2_stats(crawl_results: list[dict]) -> dict:
    """Compute average + median H2 count across successfully crawled pages."""
    h2_counts = [
        sum(1 for h in (r.get("headings") or []) if h["tag"]=="h2")
        for r in crawl_results if r.get("headings")
    ]
    if not h2_counts:
        return {}
    avg = round(sum(h2_counts)/len(h2_counts))
    med = int(median(h2_counts))
    return {
        "avg": avg,
        "median": med,
        "min": min(h2_counts),
        "max": max(h2_counts),
        "target": max(avg, med),   # use higher of avg/median
        "counts": h2_counts,
    }

# ═══════════════════════════════════════════════════════════════════
# HEADING DEDUP + FREQUENCY
# ═══════════════════════════════════════════════════════════════════
def _similar(a: str, b: str, threshold: float=0.72) -> bool:
    a,b = a.lower().strip(), b.lower().strip()
    return a==b or SequenceMatcher(None,a,b).ratio()>=threshold

def dedup_and_weight_headings(crawl_results: list[dict]) -> list[dict]:
    all_h: list[tuple] = []
    for r in crawl_results:
        for h in (r.get("headings") or []):
            all_h.append((h["tag"], h["text"], domain_of(r["url"])))
    clusters: list[dict] = []
    for tag,text,domain in all_h:
        matched = False
        for c in clusters:
            if c["tag"]==tag and _similar(c["canonical"],text):
                if domain not in c["domains"]:
                    c["domains"].append(domain)
                matched = True; break
        if not matched:
            clusters.append({"tag":tag,"canonical":text,"domains":[domain]})
    tag_order = {"h1":0,"h2":1,"h3":2,"h4":3}
    return [
        {"tag":c["tag"],"text":c["canonical"],"freq":len(c["domains"]),"domains":c["domains"]}
        for c in sorted(clusters,key=lambda x:(tag_order.get(x["tag"],9),-len(x["domains"])))
    ]

def format_headings_for_prompt(deduped: list[dict], total_crawled: int) -> str:
    return "\n".join(
        f"  [{h['tag'].upper()}] [{h['freq']}/{total_crawled}] {h['text']}"
        for h in deduped
    )

# ═══════════════════════════════════════════════════════════════════
# JSON VALIDATION
# ═══════════════════════════════════════════════════════════════════
REQUIRED_FIELDS    = {"h1":str,"meta_description":str,"article_type":str,"outline":list}
VALID_SOURCES      = {"competitor","ai","hybrid"}
VALID_ARTICLE_TYPES= {"informational","listicle","how-to","comparison","review","commercial","transactional"}

def validate_outline(data: dict) -> list[str]:
    errors = []
    if not isinstance(data,dict):
        return ["Response is not a JSON object"]
    for field,ftype in REQUIRED_FIELDS.items():
        if field not in data:
            errors.append(f"Thiếu trường bắt buộc: '{field}'")
        elif not isinstance(data[field],ftype):
            errors.append(f"Trường '{field}' sai kiểu dữ liệu")
    if "article_type" in data and data["article_type"] not in VALID_ARTICLE_TYPES:
        errors.append(f"Loại bài không hợp lệ '{data['article_type']}'")
    if "outline" in data and isinstance(data["outline"],list):
        if len(data["outline"])==0:
            errors.append("Outline rỗng")
        for i,item in enumerate(data["outline"]):
            if not isinstance(item,dict):
                errors.append(f"outline[{i}] không phải object"); continue
            if "h2" not in item or not isinstance(item.get("h2"),str) or not item["h2"].strip():
                errors.append(f"outline[{i}] thiếu hoặc rỗng 'h2'")
            if item.get("source") not in VALID_SOURCES:
                item["source"]="ai"
            if not isinstance(item.get("h3s"),list):
                item["h3s"]=[]
            if not isinstance(item.get("bullets"),list):
                item["bullets"]=[]
    return errors

def fix_outline_data(data: dict) -> dict:
    if not isinstance(data.get("faq"),list):          data["faq"]=[]
    if not isinstance(data.get("unique_angles"),list): data["unique_angles"]=[]
    if data.get("article_type") not in VALID_ARTICLE_TYPES:
        data["article_type"]="informational"
    for item in data.get("outline",[]):
        if isinstance(item,dict):
            if item.get("source") not in VALID_SOURCES: item["source"]="ai"
            if not isinstance(item.get("h3s"),list):     item["h3s"]=[]
            if not isinstance(item.get("bullets"),list): item["bullets"]=[]
            # Cap H3 toi da 5
            item["h3s"] = item["h3s"][:5]
            # H3 chi giu neu co >= 2
            if len(item["h3s"]) == 1:
                item["bullets"] = item["h3s"] + item["bullets"]
                item["h3s"] = []
            # Co ca h3s lan bullets -> bo bullets
            if item.get("h3s") and item.get("bullets"):
                item["bullets"] = []
    return data

# ═══════════════════════════════════════════════════════════════════
# CLAUDE STREAMING
# ═══════════════════════════════════════════════════════════════════
def call_claude_stream(system: str, user: str, key: str,
                       on_chunk=None, max_tokens: int=4096) -> str:
    """OpenAI gpt-4.1-nano with SSE streaming."""
    full = ""; buf = b""; last_call = 0.0
    with httpx.Client(timeout=httpx.Timeout(connect=10,read=120,write=30,pool=5)) as client:
        with client.stream("POST","https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}",
                     "content-type": "application/json"},
            json={"model": "gpt-4.1-nano",
                  "max_tokens": max_tokens,
                  "stream": True,
                  "messages": [
                      {"role": "system", "content": system},
                      {"role": "user",   "content": user},
                  ]},
        ) as resp:
            if resp.status_code==401: raise ValueError("❌ OpenAI: Invalid API key (401).")
            if resp.status_code==429: raise ValueError("❌ OpenAI: Rate limit (429). Check quota.")
            if resp.status_code==402: raise ValueError("❌ OpenAI: Insufficient credits (402).")
            if resp.status_code>=500: raise ValueError(f"❌ OpenAI: Server error ({resp.status_code}).")
            resp.raise_for_status()
            for raw_bytes in resp.iter_bytes(chunk_size=512):
                buf += raw_bytes
                while b"\n" in buf:
                    line_bytes, buf = buf.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data: "): continue
                    payload = line[6:]
                    if payload == "[DONE]": break
                    try:
                        evt = json.loads(payload)
                        chunk = evt["choices"][0]["delta"].get("content","")
                        if chunk:
                            full += chunk
                            now = time.monotonic()
                            if on_chunk and (now - last_call) >= 0.25:
                                on_chunk(full); last_call = now
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    if on_chunk and full: on_chunk(full)
    return full

def parse_json_response(raw: str) -> dict:
    clean = re.sub(r"^```[a-z]*\n?","",raw.strip())
    clean = re.sub(r"\n?```$","",clean)
    return json.loads(clean)

# ═══════════════════════════════════════════════════════════════════
# PROMPTS  — Feature #3: H2 count constraint
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# 2-CALL AI WORKFLOW
#
# Call 1 — Tổng hợp semantic:
#   Raw headings tất cả đối thủ → AI gộp ý trùng nghĩa,
#   phân cấp ý lớn/nhỏ → topic_clusters
#
# Call 2 — Gen outline:
#   topic_clusters + intent + stats → outline hoàn chỉnh
# ═══════════════════════════════════════════════════════════════════

def build_raw_headings_block(crawl_results: list[dict]) -> str:
    """Gom toàn bộ H2/H3 từ tất cả trang đối thủ, theo từng trang."""
    lines = []
    for i, r in enumerate(crawl_results):
        hs = r.get("headings") or []
        if not hs:
            continue
        domain = domain_of(r["url"])
        lines.append(f"\n### Trang {i+1}: {domain}")
        for h in hs:
            if h["tag"] in ("h2", "h3"):
                indent = "  " if h["tag"] == "h2" else "    "
                lines.append(f"{indent}[{h['tag'].upper()}] {h['text']}")
    return "\n".join(lines)

# ── Call 1: Tổng hợp semantic ──────────────────────────────────────
CLUSTER_SYSTEM = """Ban la chuyen gia phan tich noi dung SEO.
Nhiem vu: phan tich heading H2/H3 tu cac trang doi thu, tong hop thanh danh sach topic UNIQUE.

QUY TAC GOP:
1. Gop heading CUNG Y NGHIA du dien dat khac nhau -> 1 topic duy nhat
   - "SEO la gi?" + "Khai niem SEO" + "SEO Website la gi?" -> 1 topic: "SEO la gi?"
   - "Loi ich SEO" + "Vai tro SEO trong Marketing" -> 1 topic
   - "Xu huong SEO" xuat hien o nhieu H2 khac nhau -> gop vao 1 H2 duy nhat
2. MOI Y CHI XUAT HIEN 1 LAN trong toan bo danh sach - khong lap o nhieu H2
3. CAP BAC: H2 = y bao quat lon, H3 = y chi tiet NAM TRONG H2 do
   - H3 phai thuc su la sub-topic cua H2, khong phai y ngang hang
   - Neu 2 heading cung cap do -> cung la H2, khong phai H2-H3
4. H3 phai UNIQUE trong cung 1 H2: "SEO la gi?" va "Khai niem SEO" trong cung H2 -> gop thanh 1
5. Loai bo: menu, nav, CTA, quang cao, footer, sidebar

GIOI HAN CUNG:
- Toi da 10 topic H2
- Moi H2 toi da 5 H3 - neu co nhieu hon thi gop tiep
- H3 chi giu neu thuc su la chi tiet cua H2, khong phai y moi doc lap

Tra ve JSON thuan tuy:
{
  "topics": [
    {
      "h2": "Ten topic H2 (phien ban ro rang nhat, tieng Viet)",
      "h3s": ["Sub-topic thuc su chi tiet cua H2 nay, tieng Viet"],
      "freq": so trang de cap topic nay
    }
  ]
}"""

def build_cluster_prompt(keyword: str, crawl_results: list[dict],
                         serp_results: list[dict]) -> str:
    raw_block = build_raw_headings_block(crawl_results)
    total = sum(1 for r in crawl_results if r.get("headings"))
    titles = "\n".join(f"  #{r['rank']} {r['title']}"
                        for r in serp_results if r.get("title"))
    return f"""Từ khoá: "{keyword}"
Số trang crawl thành công: {total}

TIÊU ĐỀ TOP {len(serp_results)} KẾT QUẢ GOOGLE:
{titles}

HEADING CỦA {total} TRANG ĐỐI THỦ:
{raw_block}

Hãy tổng hợp thành danh sách topic unique, phân cấp H2/H3.
Trả về JSON thuần túy, không markdown fence."""

# ── Call 2: Gen outline từ topic clusters ─────────────────────────
OUTLINE_SYSTEM = """Ban la chuyen gia SEO content strategist.
Nhiem vu: tao outline bai viet SEO hoan chinh tu topic clusters da tong hop.

QUY TAC:
1. Dung topic clusters lam xuong song - day la insight thuc tu doi thu
2. KIEM TRA TRUNG Y truoc khi them H2: neu 2 topics cung y nghia -> chi giu 1
3. source="competitor" neu freq cao, source="hybrid" neu freq thap, source="ai" neu AI bo sung gap
4. H3:
   - CHI giu H3 neu la chi tiet thuc su cua H2 (khong phai y ngang hang)
   - Phai co >= 2 H3 moi dung h3s[], chi co 1 -> de vao bullets
   - Toi da 5 H3 moi H2
5. So H2 DUNG voi target (+-1)
6. faq: de [] neu khong can, hoac them cac FAQ thuc su huu ich
7. note: Dien SO THAT vao, vi du "[4/5 doi thu]" hoac "[2/5 doi thu]". KHONG de "[X/N]".
8. Toan bo text tieng Viet

JSON schema:
{
  "h1": "string",
  "meta_description": "string 150-160 ky tu",
  "article_type": "informational|listicle|how-to|comparison|review|commercial|transactional",
  "search_intent_confirmed": "string 1 cau",
  "unique_angles": ["gap ma doi thu chua cover"],
  "outline": [
    {
      "h2": "string",
      "source": "competitor|ai|hybrid",
      "h3s": ["string - chi neu >= 2 sub-topics thuc su"],
      "bullets": ["goi y ngan neu khong du H3"],
      "note": "[3/5 doi thu] (so that, khong de X/N)"
    }
  ],
  "faq": ["cau hoi FAQ neu phu hop, de [] neu khong can"]
}"""

def build_outline_prompt(keyword: str, topic_clusters: dict,
                         serp_intent: dict, mod_intent: dict,
                         wc_stats: dict, h2_stats: dict,
                         serp_results: list[dict]) -> str:
    import json as _json

    intent_str = (f"{mod_intent['intent']} (modifier), "
                  f"{serp_intent.get('intent','?')} (SERP titles)")

    wc_line = ""
    if wc_stats:
        wc_line = f"Số từ mục tiêu: ~{wc_stats['target']:,} từ (trung vị đối thủ: {wc_stats['median']:,})\n"

    h2_line = ""
    if h2_stats:
        h2_line = (f"Số H2 đối thủ: avg={h2_stats['avg']}, "
                   f"median={h2_stats['median']}, range={h2_stats['min']}–{h2_stats['max']}\n"
                   f"→ TARGET H2 = {h2_stats['target']} (±1)\n")

    clusters_str = _json.dumps(topic_clusters, ensure_ascii=False, indent=2)

    return f"""Từ khoá: "{keyword}"
Search intent: {intent_str}
{wc_line}{h2_line}
TOPIC CLUSTERS (đã tổng hợp từ đối thủ):
{clusters_str}

Tạo outline SEO hoàn chỉnh dựa trên topic clusters trên.
Bổ sung các AI gaps nếu có topic quan trọng mà đối thủ bỏ sót.
Trả về JSON thuần túy, không markdown fence."""

# ═══════════════════════════════════════════════════════════════════
# RENDER (read-only view)
# ═══════════════════════════════════════════════════════════════════
def render_outline_view(data: dict, wc_stats: dict):
    h1     = data.get("h1","")
    meta   = data.get("meta_description","")
    atype  = data.get("article_type","")
    intent = data.get("search_intent_confirmed","")
    angles = data.get("unique_angles",[])
    outline= data.get("outline",[])

    st.markdown(f"""
    <div class="h1-card">
      <div class="h1-label">H1 — Tiêu đề bài viết</div>
      <div class="h1-text">{h1}</div>
      <div class="meta-text"><b>Meta:</b> {meta}</div>
    </div>""", unsafe_allow_html=True)

    comp_n = sum(1 for b in outline if b.get("source")=="competitor")
    ai_n   = sum(1 for b in outline if b.get("source") in ("ai","hybrid"))
    il,ibg,icolor = INTENT_LABELS.get(atype,INTENT_LABELS["mixed"])
    wc_pill = (f'<span class="pill words">📝 ~<b>{wc_stats["target"]:,}</b> từ</span>'
               if wc_stats else "")
    st.markdown(f"""
    <div class="pills">
      <span class="pill" style="background:{ibg};color:{icolor};border-color:{ibg}">{il}</span>
      {wc_pill}
      <span class="pill">📊 <b>{len(outline)}</b> H2</span>
      <span class="pill">🔵 <b>{comp_n}</b> đối thủ</span>
      <span class="pill">🟢 <b>{ai_n}</b> AI mới</span>
    </div>""", unsafe_allow_html=True)

    if not intent:
        intent = INTENT_LABELS.get(atype, INTENT_LABELS["mixed"])[0]
    if intent:
        st.markdown(f'<div class="intent-banner">🎯 <b>Search intent:</b> {intent}</div>',
                    unsafe_allow_html=True)
    if angles:
        tags = "".join(f'<span class="angle-tag">✦ {a}</span>' for a in angles)
        st.markdown(f"""<div class="angles-card">
          <div class="angles-title">💡 Góc nhìn độc đáo</div>{tags}</div>""",
          unsafe_allow_html=True)

    if wc_stats:
        pct = min(int(wc_stats["target"]/(wc_stats["max"] or 1)*100),100)
        st.markdown(f"""
        <div style="font-size:0.75rem;color:#64748b;margin-bottom:2px">
          Số từ mục tiêu so với max ({wc_stats['min']:,}–{wc_stats['max']:,})</div>
        <div class="wc-bar-wrap"><div class="wc-bar" style="width:{pct}%"></div></div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="sec-label">📑 Outline</div>', unsafe_allow_html=True)
    for idx,block in enumerate(outline):
        src = block.get("source","ai")
        if src=="competitor":  sc,bc,bt = "sec-comp","b-comp","Đối thủ"
        elif src=="hybrid":    sc,bc,bt = "sec-hyb","b-hyb","Kết hợp"
        else:                  sc,bc,bt = "sec-ai","b-ai","AI ✦"
        # Clean note: strip nếu AI nhét source= vào đây thay vì frequency
        raw_note = block.get("note","")
        note = "" if re.search(r'source\s*=', raw_note, re.IGNORECASE) else raw_note
        nh   = (f'<span style="font-size:0.75rem;color:#94a3b8;font-weight:400"> — {note}</span>'
                if note else "")

        h3s     = block.get("h3s",[])
        bullets = block.get("bullets",[])

        # H3 rows — with frequency note if present in note field
        h3_html = ""
        if h3s:
            h3_html = "".join(
                f'<div class="h3-row">'
                f'<span class="h3-arrow">↳</span>'
                f'<span class="badge b-num" style="font-size:0.55rem;margin-right:4px">H3</span>'
                f'{h}</div>'
                for h in h3s
            )

        # Bullet rows — content guidance when no real H3s
        bullet_html = ""
        if bullets and not h3s:
            bullet_html = (
                '<div style="padding:4px 0 2px;font-size:0.72rem;color:#94a3b8;'
                'font-weight:600;text-transform:uppercase;letter-spacing:.4px">'
                '💡 Nội dung gợi ý</div>' +
                "".join(
                    f'<div class="h3-row" style="color:#64748b">'
                    f'<span style="color:#cbd5e1;margin-right:6px;flex-shrink:0">•</span>'
                    f'{b}</div>'
                    for b in bullets
                )
            )

        body_content = h3_html + bullet_html
        body = f'<div class="sec-body">{body_content}</div>' if body_content else ""

        col_m, col_c = st.columns([11,1])
        with col_m:
            st.markdown(f"""<div class="sec {sc}">
              <div class="sec-head">
                {block['h2']}
                <span class="badge {bc}">{bt}</span>{nh}
              </div>{body}</div>""", unsafe_allow_html=True)
        with col_c:
            lines = [f"H2: {block['h2']}"]
            for h in h3s:   lines.append(f"  H3: {h}")
            for b in bullets: lines.append(f"  • {b}")
            st.download_button("📋", data="\n".join(lines),
                               file_name=f"h2_{idx+1}_{_safe_filename(block["h2"], 20)}.txt",
                               mime="text/plain", key=f"dl_h2_{idx}", help="Tải về section này")

    # FAQ - hien thi neu AI gen ra
    faq = data.get("faq") or []
    if faq:
        faq_rows = "".join(
            '<div class="h3-row"><span class="h3-arrow">Q</span>' + q + '</div>'
            for q in faq
        )
        st.markdown(
            '<div class="sec sec-faq" style="margin-top:12px">'
            '<div class="sec-head"><span class="badge b-faq">FAQ</span> Câu hỏi thường gặp</div>'
            '<div class="sec-body">' + faq_rows + '</div>'
            '</div>',
            unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# Feature #2: EDITABLE OUTLINE
# ═══════════════════════════════════════════════════════════════════
def outline_to_df(data: dict) -> pd.DataFrame:
    """Convert outline JSON → flat DataFrame for st.data_editor."""
    rows = []
    rows.append({"Level":"H1","Text":data.get("h1",""),"Nguồn":"—","Ghi chú":""})
    for block in data.get("outline",[]):
        src = block.get("source","ai").capitalize()
        rows.append({"Level":"H2","Text":block.get("h2",""),"Nguồn":src,
                     "Ghi chú":block.get("note","")})
        for h3 in block.get("h3s",[]):
            rows.append({"Level":"H3","Text":h3,"Nguồn":"","Ghi chú":""})
        for b in block.get("bullets",[]):
            rows.append({"Level":"Bullet","Text":b,"Nguồn":"","Ghi chú":""})
    return pd.DataFrame(rows)

def df_to_outline(df: pd.DataFrame, original: dict) -> dict:
    """Reconstruct outline JSON from edited DataFrame."""
    result = dict(original)
    result["faq"] = []  # always empty
    h2_blocks: list[dict] = []
    current_h2: dict | None = None

    for _, row in df.iterrows():
        lvl  = (row.get("Level") or "").strip()
        text = (row.get("Text")  or "").strip()
        if not text:
            continue
        if lvl == "H1":
            result["h1"] = text
        elif lvl == "H2":
            if current_h2: h2_blocks.append(current_h2)
            src = (row.get("Nguồn") or "ai").lower()
            if src not in VALID_SOURCES: src = "ai"
            current_h2 = {"h2":text,"source":src,"h3s":[],"bullets":[],
                          "note":(row.get("Ghi chú") or "").strip()}
        elif lvl == "H3":
            if current_h2 is None:
                current_h2 = {"h2":"(untitled)","source":"ai","h3s":[],"bullets":[],"note":""}
            current_h2["h3s"].append(text)
        elif lvl == "Bullet":
            if current_h2 is None:
                current_h2 = {"h2":"(untitled)","source":"ai","h3s":[],"bullets":[],"note":""}
            current_h2["bullets"].append(text)

    if current_h2: h2_blocks.append(current_h2)
    result["outline"] = h2_blocks
    return result

def render_editor(data: dict, wc_stats: dict) -> dict:
    """
    Feature #2: Editable outline using st.data_editor.
    Returns possibly-modified outline dict.
    """
    st.markdown('<div class="edit-banner">✏️ <b>Chế độ chỉnh sửa</b> — nhấn vào ô để sửa. '
                'Thêm/xóa hàng. Level: H1 / H2 / H3 / Bullet</div>',
                unsafe_allow_html=True)

    df = outline_to_df(data)

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Level": st.column_config.SelectboxColumn(
                "Level", options=["H1","H2","H3","Bullet"], width="small"
            ),
            "Text":   st.column_config.TextColumn("Text",   width="large"),
            "Nguồn": st.column_config.SelectboxColumn(
                "Nguồn", options=["Competitor","Ai","Hybrid","—",""], width="small"
            ),
            "Ghi chú":   st.column_config.TextColumn("Ghi chú",   width="medium"),
        },
        key="outline_editor",
        height=min(60 + len(df)*35, 600),
    )

    return df_to_outline(edited_df, data)

# ═══════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════
def outline_to_text(keyword: str, data: dict, wc_stats: dict) -> str:
    lines = [f"OUTLINE: {keyword}", ""]
    if data.get("h1"):               lines.append(f"H1: {data['h1']}")
    if data.get("meta_description"): lines.append(f"Meta: {data['meta_description']}")
    if data.get("search_intent_confirmed"): lines.append(f"Intent: {data['search_intent_confirmed']}")
    if wc_stats:
        lines.append(f"Target: ~{wc_stats['target']:,} từ (trung vị {wc_stats['median']:,})")
    if data.get("unique_angles"):
        lines.append("Góc nhìn độc đáo:")
        for a in data["unique_angles"]:
            lines.append(f"  ✦ {a}")
        lines.append("")
    for b in data.get("outline",[]):
        lines.append(f"H2: {b['h2']}")
        for h in b.get("h3s",[]):      lines.append(f"   H3: {h}")
        for pt in b.get("bullets",[]): lines.append(f"   * {pt}")
        lines.append("")
    if data.get("faq"):
        lines.append("FAQ:")
        for q in data["faq"]:
            lines.append(f"  Q: {q}")
    return "\n".join(lines)

def _safe_filename(keyword: str, max_len: int = 40) -> str:
    import re as _re
    name = keyword.strip()[:max_len]
    name = _re.sub(r'[\\/:*?"<>|]', '', name)
    name = name.replace(' ', '_')
    return name or 'outline'

def call_ai_simple(system: str, prompt: str, key: str, max_tokens: int = 2048) -> str:
    """Non-streaming call for Call 1 (cluster synthesis — faster, no UI feedback needed)."""
    import httpx as _httpx
    resp = _httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
        json={"model": "gpt-4.1-nano", "max_tokens": max_tokens,
              "messages": [{"role": "system", "content": system},
                           {"role": "user",   "content": prompt}]},
        timeout=60,
    )
    if resp.status_code == 401: raise ValueError("❌ OpenAI: Invalid API key (401).")
    if resp.status_code == 429: raise ValueError("❌ OpenAI: Rate limit (429).")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def run_two_call_pipeline(keyword: str, crawl_results: list, serp_results: list,
                          serp_intent: dict, mod_intent: dict,
                          wc_stats: dict, h2_stats: dict,
                          key: str, stream_slot) -> tuple:
    """
    Call 1: Tổng hợp semantic → topic clusters
    Call 2: Gen outline từ clusters (streamed)
    Returns (outline_data, raw_call2)
    """
    # ── Call 1: Cluster synthesis ──────────────────────────────────
    stream_slot.markdown(
        '<div class="stream-box">🔍 Bước 1/2: Đang tổng hợp heading đối thủ...</div>',
        unsafe_allow_html=True
    )
    try:
        cluster_prompt = build_cluster_prompt(keyword, crawl_results, serp_results)
        raw1 = call_ai_simple(CLUSTER_SYSTEM, cluster_prompt, key, max_tokens=2048)
        topic_clusters = parse_json_response(raw1)
        n_topics = len(topic_clusters.get("topics", []))
        stream_slot.markdown(
            f'<div class="stream-box">✅ Bước 1/2: Tổng hợp xong — {n_topics} topics unique\n\n'
            f'🤖 Bước 2/2: Đang tạo outline...</div>',
            unsafe_allow_html=True
        )
    except Exception as e:
        stream_slot.empty()
        st.error(f"Lỗi bước 1 (tổng hợp): {e}")
        return None, ""

    # ── Call 2: Gen outline (streamed) ─────────────────────────────
    raw2 = ""
    try:
        outline_prompt = build_outline_prompt(
            keyword, topic_clusters, serp_intent, mod_intent,
            wc_stats, h2_stats, serp_results
        )

        def on_chunk(t: str):
            prev = t[-600:].replace("<", "&lt;").replace(">", "&gt;")
            stream_slot.markdown(
                f'<div class="stream-box">✅ Bước 1 xong · 🤖 Bước 2/2 đang tạo...\n\n{prev}</div>',
                unsafe_allow_html=True
            )

        raw2 = call_claude_stream(OUTLINE_SYSTEM, outline_prompt, key, on_chunk=on_chunk)
        stream_slot.empty()
    except ValueError as e:
        stream_slot.empty(); st.error(str(e)); return None, raw2
    except Exception as e:
        stream_slot.empty(); st.error(f"Lỗi bước 2 (gen outline): {e}"); return None, raw2

    # ── Validate ───────────────────────────────────────────────────
    try:
        data = parse_json_response(raw2)
    except json.JSONDecodeError as e:
        st.error(f"AI trả về JSON không hợp lệ: {e}")
        with st.expander("Dữ liệu thô (debug)"): st.code(raw2[:3000])
        return None, raw2

    errors = validate_outline(data)
    fatal  = [e for e in errors if "Thiếu" in e or "rỗng" in e]
    warns  = [e for e in errors if e not in fatal]
    for w in warns: st.warning(f"⚠️ {w}")
    if fatal:
        st.markdown('<div class="val-err">❌ <b>Lỗi dữ liệu AI trả về:</b><br>'
                    + "<br>".join(fatal) + "</div>", unsafe_allow_html=True)
        with st.expander("Dữ liệu thô (debug)"): st.code(raw2[:3000])
        return None, raw2

    return fix_outline_data(data), raw2

# ═══════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════
SESS_DEFAULTS = {
    "serp":None,"crawl":None,"outline":None,"edited_outline":None,
    "wc_stats":None,"h2_stats":None,"last_kw":None,
    "detected_lang":None,"intent_hint":None,"deduped":None,"serp_intent":None,
    "kw_history":[],"running":False,"edit_mode":False,
}
for k,v in SESS_DEFAULTS.items():
    if k not in st.session_state: st.session_state[k]=v

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Cài đặt")

    with st.expander("🔑 API Keys", expanded=True):
        dfs_login     = st.text_input("DataForSEO Login", placeholder="email@example.com")
        dfs_password  = st.text_input("Mật khẩu DataForSEO", type="password")
        anthropic_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")

    location_code, serp_lang = 2704, "vi"

    with st.expander("🕷️ Crawl trang web"):
        t1 = st.slider("Timeout lần 1 (giây)", 5, 15, 8)
        t2 = st.slider("Timeout thử lại (giây)", 10, 30, 18)
        # Feature #1: Jina toggle
        use_jina = st.toggle("Dùng Jina khi bị chặn", value=True,
            help="Dự phòng r.jina.ai khi trang dùng Cloudflare")

    st.divider()
    st.caption("🔒 API key chỉ lưu trong phiên làm việc.")
    st.caption(f"🔧 Parser HTML: **{BS4_PARSER}**")

    if st.session_state.kw_history:
        st.divider()
        st.markdown("**🕐 Từ khoá gần đây**")
        for kh in reversed(st.session_state.kw_history[-8:]):
            st.caption(f"• {kh}")

    if st.session_state.wc_stats:
        st.divider()
        wc = st.session_state.wc_stats
        st.caption(f"**Số từ:** {wc['min']:,}–{wc['max']:,} · mục tiêu ~{wc['target']:,}")
    if st.session_state.h2_stats:
        h2 = st.session_state.h2_stats
        st.caption(f"**H2:** tb={h2['avg']} trung vị={h2['median']} khoảng={h2['min']}–{h2['max']}")

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
st.title("🧭 Tạo Outline SEO")

kw_col,btn_col,reg_col = st.columns([5,1.5,1.8])
with kw_col:
    keyword = st.text_input("kw", placeholder="vd: cách học tiếng anh, affiliate marketing là gì, review điện thoại samsung",
                             label_visibility="collapsed", disabled=st.session_state.running)
with btn_col:
    run_btn = st.button("🚀 Tạo Outline", type="primary", use_container_width=True,
                        disabled=st.session_state.running)
with reg_col:
    regen_btn = st.button("🔄 Tạo Lại", use_container_width=True,
                          disabled=(not st.session_state.crawl) or st.session_state.running,
                          help="Chạy lại AI — giữ nguyên dữ liệu crawl")

# Live detect preview
if keyword and not st.session_state.running:
    eff_lang    = "vi"
    intent_hint = detect_intent_from_modifier(keyword)
    il,ibg,icolor = INTENT_LABELS.get(intent_hint["intent"],INTENT_LABELS["mixed"])
    cc   = {"high":"#16a34a","medium":"#d97706","low":"#94a3b8"}.get(intent_hint["confidence"],"#94a3b8")
    sig  = ", ".join(intent_hint["signals"][:4]) or "—"
    st.markdown(f"""
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;
                margin:6px 0 14px;font-size:0.82rem;">
      <span class="badge b-lang">🇻🇳 VI</span>
      <span class="badge" style="background:{ibg};color:{icolor}">{il}</span>
      <span style="color:{cc};font-weight:600">{intent_hint['confidence']} độ tin cậy</span>
      <span style="color:#94a3b8">tín hiệu: {sig}</span>
    </div>""", unsafe_allow_html=True)
else:
    eff_lang    = "vi"
    intent_hint = {"intent":"informational","confidence":"low","signals":[]}

# ═══════════════════════════════════════════════════════════════════
# PIPELINE: Full run
# ═══════════════════════════════════════════════════════════════════
if run_btn and not st.session_state.running:
    errs=[]
    if not keyword.strip(): errs.append("Vui lòng nhập từ khoá.")
    if not dfs_login:       errs.append("Vui lòng nhập DataForSEO login.")
    if not dfs_password:    errs.append("Vui lòng nhập DataForSEO password.")
    if not anthropic_key:   errs.append("Vui lòng nhập OpenAI API key.")
    if errs:
        for e in errs: st.error(e)
        st.stop()
    st.session_state.running    = True
    st.session_state.edit_mode  = False
    st.session_state.edited_outline = None
    st.rerun()

if st.session_state.running and not regen_btn:
    kw = (keyword.strip() if keyword.strip()
          else st.session_state.get("last_kw",""))
    if not kw:
        st.session_state.running = False; st.stop()

    st.session_state.last_kw       = kw
    st.session_state.detected_lang  = eff_lang
    st.session_state.intent_hint    = intent_hint
    hist = st.session_state.kw_history or []
    if kw not in hist: hist.append(kw)
    st.session_state.kw_history = hist[-20:]

    try:
        # Step 1: SERP
        with st.status("🔍 Đang lấy kết quả Google...", expanded=False) as s:
            try:
                serp = fetch_serp(kw, dfs_login, dfs_password, location_code, serp_lang)
                st.session_state.serp = serp
                si = intent_from_serp_titles(serp)
                st.session_state.serp_intent = si
                s.update(label=f"✅ SERP — {len(serp)} trang · intent: {si.get('intent','?')}",
                         state="complete")
            except ValueError as e:
                s.update(label="❌ Lỗi lấy SERP", state="error"); st.error(str(e))
                st.session_state.running=False; st.stop()
            except Exception as e:
                s.update(label="❌ Lỗi lấy SERP", state="error"); st.error(f"Lỗi không xác định: {e}")
                st.session_state.running=False; st.stop()

        if not serp:
            st.error("Không tìm thấy kết quả SERP hợp lệ."); st.session_state.running=False; st.stop()

        with st.expander(f"📋 Kết quả Google Top {len(serp)} — {kw}", expanded=False):
            for r in serp:
                st.markdown(f"""<div class="dom-card">
                  <b>#{r['rank']}</b> {r['title']}<br>
                  <a href="{r['url']}" target="_blank">🔗 {domain_of(r['url'])}</a>
                </div>""", unsafe_allow_html=True)

        # Step 2: Parallel crawl
        crawl_hdr = st.empty()
        prog      = st.progress(0)
        log_slot  = st.empty()
        log: list[str] = []
        crawl_hdr.markdown("**🕷️ Đang crawl các trang song song...**")
        t0 = time.time()

        def on_crawl(done, total, r):
            d   = domain_of(r["url"])
            wc  = r.get("word_count",0)
            sts = r.get("status","fail")
            mtd = r.get("method","direct")
            method_tag = (
                " 🟢dfs"   if mtd in ("dfs","dfs_content") else
                " 🟣jina"  if mtd == "jina" else ""
            )
            icon = "✅" if sts in ("ok","dfs","jina") else ("🔁" if sts=="retry_ok" else "❌")
            log.append(f"{icon} {d}{f' · {wc:,}w' if wc else ''}{method_tag}")
            prog.progress(done/total)
            log_slot.markdown("  \n".join(log[-8:]))

        crawl = crawl_all(serp, t1, t2, use_jina,
                          dfs_login, dfs_password, on_crawl)
        elapsed = time.time()-t0
        st.session_state.crawl = crawl

        wc_stats = competitor_word_count_stats(crawl)
        st.session_state.wc_stats = wc_stats
        h2_stats = competitor_h2_stats(crawl)   # Feature #3
        st.session_state.h2_stats = h2_stats
        deduped  = dedup_and_weight_headings(crawl)
        st.session_state.deduped = deduped

        prog.empty(); log_slot.empty(); crawl_hdr.empty()

        ok_n    = sum(1 for r in crawl if r.get("headings"))
        dfs_n   = sum(1 for r in crawl if r.get("method") in ("dfs","dfs_content"))
        jina_n  = sum(1 for r in crawl if r.get("method")=="jina")
        retry_n = sum(1 for r in crawl if r.get("status")=="retry_ok")
        fail_n  = sum(1 for r in crawl if r.get("status")=="fail")
        method_parts = []
        if dfs_n:   method_parts.append(f"🟢 {dfs_n} qua DFS On-Page")
        if jina_n:  method_parts.append(f"🟣 {jina_n} qua Jina")
        if retry_n: method_parts.append(f"{retry_n} thử lại")
        if fail_n:  method_parts.append(f"{fail_n} thất bại")
        method_str = " · " + " · ".join(method_parts) if method_parts else ""
        st.success(
            f"✅ Crawl {ok_n}/{len(crawl)} trang trong **{elapsed:.1f}s**"
            f"{method_str}"
            f" · {len(deduped)} heading duy nhất"
        )
        if h2_stats:
            st.info(f"📊 Số H2 đối thủ: tb={h2_stats['avg']} · "
                    f"trung vị={h2_stats['median']} · khoảng {h2_stats['min']}–{h2_stats['max']} "
                    f"→ **mục tiêu: {h2_stats['target']} H2**")

        with st.expander("🕷️ Chi tiết crawl", expanded=False):
            tab1,tab2 = st.tabs(["Theo trang","Đã gộp (tần suất)"])
            with tab1:
                for r in crawl:
                    d  = domain_of(r["url"])
                    hs = r.get("headings") or []
                    wc = r.get("word_count",0)
                    sts= r.get("status","fail")
                    mtd= r.get("method","direct")
                    if not hs:
                        err=(r.get("error") or "")[:120]
                        st.markdown(f'<div class="dom-card">❌ <b>{d}</b><br>'
                                    f'<small style="color:#94a3b8">{err}</small></div>',
                                    unsafe_allow_html=True); continue
                    h2c=sum(1 for h in hs if h["tag"]=="h2")
                    h3c=sum(1 for h in hs if h["tag"]=="h3")
                    if mtd in ("dfs","dfs_content"):
                        rb = ' <span class="badge b-comp">🟢 DFS</span>'
                    elif mtd=="jina":
                        rb = ' <span class="badge b-jina">🟣 Jina</span>'
                    elif sts=="retry_ok":
                        rb = ' <span class="badge b-warn">retry</span>'
                    else:
                        rb = ""
                    rows="".join(f'<span class="hp hp-{h["tag"]}">{h["tag"].upper()}</span>{h["text"]}<br>'
                                 for h in hs)
                    st.markdown(f"""<div class="dom-card">
                      <b>{d}</b>{rb}
                      <span class="badge b-comp">{len(hs)}·{h2c}H2·{h3c}H3</span>
                      {f'· <b>{wc:,}</b>w' if wc else ''}
                      <a href="{r['url']}" target="_blank" style="float:right">🔗</a><br>
                      <div style="margin-top:6px;font-size:0.82rem;color:#374151">{rows}</div>
                    </div>""", unsafe_allow_html=True)
            with tab2:
                tok = sum(1 for r in crawl if r.get("headings"))
                for h in deduped:
                    f_ = h["freq"]
                    c_ = "#166534" if f_>=tok*0.6 else "#92400e" if f_>=tok*0.3 else "#64748b"
                    st.markdown(f'<span class="hp hp-{h["tag"]}">{h["tag"].upper()}</span>'
                                f'<span style="color:{c_};font-weight:600;font-size:0.75rem">'
                                f'[{f_}/{tok}]</span> {h["text"]}',
                                unsafe_allow_html=True)

        # Step 3: AI — 2-call workflow
        st.markdown("**🤖 Đang xử lý outline (2 bước)...**")
        ss = st.empty()
        ss.markdown('<div class="stream-box">Đang khởi động...</div>',
                    unsafe_allow_html=True)
        od, _ = run_two_call_pipeline(
            keyword=kw,
            crawl_results=crawl,
            serp_results=serp,
            serp_intent=st.session_state.serp_intent or {},
            mod_intent=intent_hint,
            wc_stats=wc_stats,
            h2_stats=h2_stats,
            key=anthropic_key,
            stream_slot=ss,
        )
        if od:
            st.session_state.outline = od
            st.success("✅ Outline đã sẵn sàng!")

    finally:
        st.session_state.running = False

# PIPELINE: Regenerate
elif regen_btn and not st.session_state.running:
    if not anthropic_key:
        st.error("Vui lòng nhập OpenAI API key."); st.stop()
    st.session_state.running    = True
    st.session_state.edit_mode  = False
    st.session_state.edited_outline = None
    try:
        kw      = st.session_state.last_kw or keyword
        lang    = st.session_state.detected_lang or eff_lang
        hint    = st.session_state.intent_hint or intent_hint
        wc      = st.session_state.wc_stats or {}
        h2      = st.session_state.h2_stats or {}
        deduped = st.session_state.deduped or []
        si      = st.session_state.serp_intent or {}
        serp_r  = st.session_state.serp or []
        crawl_r = st.session_state.crawl or []
        st.markdown("**🔄 Đang tạo lại outline (2 bước)...**")
        ss = st.empty()
        ss.markdown('<div class="stream-box">Đang khởi động...</div>', unsafe_allow_html=True)
        od, _ = run_two_call_pipeline(
            keyword=kw,
            crawl_results=crawl_r,
            serp_results=serp_r,
            serp_intent=si,
            mod_intent=hint,
            wc_stats=wc,
            h2_stats=h2,
            key=anthropic_key,
            stream_slot=ss,
        )
        if od:
            st.session_state.outline = od
            st.success("✅ Outline mới đã sẵn sàng!")
    finally:
        st.session_state.running = False

# ═══════════════════════════════════════════════════════════════════
# RENDER RESULTS
# ═══════════════════════════════════════════════════════════════════
if st.session_state.outline and not st.session_state.running:
    kw = st.session_state.last_kw or keyword
    wc = st.session_state.wc_stats or {}

    st.divider()

    # Header row with edit toggle
    hcol, ecol = st.columns([6,2])
    with hcol:
        st.subheader(f"📝 Outline — {kw}")
    with ecol:
        edit_mode = st.toggle("✏️ Chỉnh sửa outline", value=st.session_state.edit_mode,
                              key="edit_toggle",
                              help="Chuyển giữa xem và chỉnh sửa")
        st.session_state.edit_mode = edit_mode

    # Get the working outline (edited or original)
    working = st.session_state.edited_outline or st.session_state.outline

    if st.session_state.edit_mode:
        # Feature #2: editable grid
        edited = render_editor(working, wc)
        st.session_state.edited_outline = edited
        # Preview in real-time below editor
        with st.expander("👁️ Xem trước outline đã sửa", expanded=False):
            render_outline_view(edited, wc)
        export_data = edited
    else:
        render_outline_view(working, wc)
        export_data = working

    # Export
    st.divider()
    txt = outline_to_text(kw, export_data, wc)

    # Helper: generate compact copy strings
    def _copy_h1_h2(data: dict) -> str:
        lines = []
        if data.get("h1"):
            lines.append(f"H1: {data['h1']}")
        for b in data.get("outline", []):
            lines.append(f"H2: {b['h2']}")
        return "\n".join(lines)

    def _copy_h1_h2_h3(data: dict) -> str:
        lines = []
        if data.get("h1"):
            lines.append(f"H1: {data['h1']}")
        for b in data.get("outline", []):
            lines.append(f"H2: {b['h2']}")
            for h in b.get("h3s", []):
                lines.append(f"   H3: {h}")
            for pt in b.get("bullets", []):
                lines.append(f"   • {pt}")
        return "\n".join(lines)

    txt_h1h2    = _copy_h1_h2(export_data)
    txt_h1h2h3  = _copy_h1_h2_h3(export_data)

    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        st.download_button("⬇️ Tải xuống .txt", data=txt,
                           file_name=f"outline_{_safe_filename(kw)}.txt",
                           mime="text/plain", use_container_width=True)
    with c2:
        with st.expander("📋 H1 + H2"):
            st.code(txt_h1h2, language=None)
    with c3:
        with st.expander("📋 H1 + H2 + H3"):
            st.code(txt_h1h2h3, language=None)
    with c4:
        if st.session_state.edited_outline:
            if st.button("↩️ Hoàn tác chỉnh sửa", use_container_width=True):
                st.session_state.edited_outline = None
                st.session_state.edit_mode = False
                st.rerun()

    with st.expander("📋 Sao chép toàn bộ"):
        st.code(txt, language=None)

    with st.expander("🔧 Dữ liệu JSON"):
        st.json(export_data)

# Landing
elif not st.session_state.outline:
    st.markdown("""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;
                padding:2rem;text-align:center;margin-top:1rem">
      <div style="font-size:2.5rem">🧭</div>
      <div style="font-size:1.05rem;font-weight:600;margin:8px 0 4px">SEO Outline Generator</div>
      <div style="color:#64748b;font-size:0.88rem">
        Từ khoá → DataForSEO Top 5 → Crawl + Jina → Outline AI
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    **Hướng dẫn sử dụng:**
    - 🔑 Nhập API keys vào sidebar (DataForSEO + OpenAI)
    - ⌨️ Gõ từ khoá tiếng Việt vào ô nhập → nhấn **Tạo Outline**
    - 🕷️ Tool tự động crawl top 5 Google và phân tích đối thủ
    - 📝 Outline được tạo dựa trên cấu trúc đối thủ + AI bổ sung
    - ✏️ Nhấn "Chỉnh sửa outline" để sửa trực tiếp trước khi export
    """)
