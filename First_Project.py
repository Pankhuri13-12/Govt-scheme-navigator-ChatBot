import requests, json, os, time
from bs4 import BeautifulSoup

os.makedirs("data", exist_ok=True)

HEADERS = {
    "accept":             "application/json, text/plain, */*",
    "accept-language":    "en-US,en-GB;q=0.9,en;q=0.8",
    "origin":             "https://www.myscheme.gov.in",
    "referer":            "https://www.myscheme.gov.in/",
    "priority":           "u=1, i",
    "sec-ch-ua":          '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile":   "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest":     "empty",
    "sec-fetch-mode":     "cors",
    "sec-fetch-site":     "same-site",
    "user-agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "x-api-key":          "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc",
}

LIST_API   = "https://api.myscheme.gov.in/search/v6/schemes"
DETAIL_API = "https://api.myscheme.gov.in/schemes/v6/public/schemes"


# ── STEP 0: Build ID ──────────────────────────────────────────────────────────
def get_build_id():
    r    = requests.get("https://www.myscheme.gov.in/search", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    tag  = soup.find("script", id="__NEXT_DATA__")
    if tag:
        build_id = json.loads(tag.string).get("buildId")
        print(f"  Build ID: {build_id}")
        return build_id
    raise Exception("__NEXT_DATA__ not found")


# ── STEP 1: List API → slugs + IDs ───────────────────────────────────────────
def get_all_slugs(max_schemes=100):
    results, seen, page_size = [], set(), 10
    for page in range(max_schemes // page_size):
        params = {"lang": "en", "q": "[]", "keyword": "", "sort": "",
                  "from": page * page_size, "size": page_size}
        try:
            r     = requests.get(LIST_API, headers=HEADERS, params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("data", {}).get("hits", {}).get("items", [])
            if not items:
                break
            for item in items:
                slug = item.get("fields", {}).get("slug", "").strip().lower()
                iid  = item.get("id", "")
                if slug and slug not in seen:
                    results.append((slug, iid))
                    seen.add(slug)
            print(f"  Page {page+1}: +{len(items)} | total = {len(results)}")
            time.sleep(0.8)
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break
    return results


# ── STEP 2a: Detail API ───────────────────────────────────────────────────────
def fetch_detail(slug):
    try:
        r = requests.get(DETAIL_API, headers=HEADERS,
                         params={"slug": slug, "lang": "en"}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"    detail error ({slug}): {e}")
        return {}


# ── STEP 2b: Documents API ────────────────────────────────────────────────────
def fetch_documents(scheme_id):
    if not scheme_id:
        return []
    try:
        r = requests.get(f"{DETAIL_API}/{scheme_id}/documents",
                         headers=HEADERS, params={"lang": "en"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        docs = data.get("data", data.get("documents", []))
        if isinstance(docs, list):
            return [str(d.get("documentName") or d.get("name") or d) for d in docs if d]
        return []
    except Exception as e:
        print(f"    docs error: {e}")
        return []


# ── Helper: extract plain text from rich-text node list ──────────────────────
def extract_text(nodes):
    if not nodes:
        return ""
    if isinstance(nodes, str):
        return nodes
    lines = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if "text" in node and node["text"].strip():
            lines.append(node["text"].strip())
        if "children" in node:
            child_text = extract_text(node["children"])
            if child_text:
                lines.append(child_text)
    return "\n".join(lines)


# ── Helper: extract application process steps ─────────────────────────────────
def extract_application_process(app_process):
    if not app_process or not isinstance(app_process, list):
        return ""
    lines = []
    for mode_item in app_process:
        mode = mode_item.get("mode", "")
        url  = mode_item.get("url", "")
        if mode:
            lines.append(f"Mode: {mode}")
        if url:
            lines.append(f"URL: {url}")
        process = mode_item.get("process", [])
        lines.append(extract_text(process))
    return "\n".join(lines)


# ── STEP 3: Flatten confirmed JSON structure → readable text ──────────────────
def flatten_scheme(raw: dict, slug: str, docs: list) -> str:
    """
    Confirmed structure from debug_detail3.py:
    raw.data.en.basicDetails      → name, ministry, tags, level, category
    raw.data.en.schemeContent     → description, benefits
    raw.data.en.applicationProcess→ steps
    raw.data.en.eligibilityCriteria → eligibility text
    """
    data    = raw.get("data", {})
    en      = data.get("en", {})
    basic   = en.get("basicDetails",       {})
    content = en.get("schemeContent",      {})
    app     = en.get("applicationProcess", [])
    elig    = en.get("eligibilityCriteria", {})

    # ── Extract fields ────────────────────────────────────────────────────────
    scheme_name  = basic.get("schemeName", slug)
    short_title  = basic.get("schemeShortTitle", "")

    ministry     = basic.get("nodalMinistryName", {})
    ministry     = ministry.get("label", "") if isinstance(ministry, dict) else str(ministry or "")

    level        = basic.get("level", {})
    level        = level.get("label", "") if isinstance(level, dict) else str(level or "")

    # ✅ FIXED: use (... or []) to handle null values from API
    categories   = [c.get("label", "") for c in (basic.get("schemeCategory")    or []) if isinstance(c, dict)]
    tags         = basic.get("tags") or []
    beneficiaries= [b.get("label", "") for b in (basic.get("targetBeneficiaries") or []) if isinstance(b, dict)]

    description  = content.get("detailedDescription_md", "") or content.get("briefDescription", "")

    benefits_raw = content.get("benefits") or []
    benefits     = extract_text(benefits_raw) if isinstance(benefits_raw, list) else str(benefits_raw)

    eligibility  = elig.get("eligibilityDescription_md", "")
    if not eligibility:
        eligibility = extract_text(elig.get("eligibilityDescription") or [])

    app_process  = extract_application_process(app)
    docs_text    = "\n  - ".join(docs) if docs else ""

    # ── Build clean text ──────────────────────────────────────────────────────
    lines = []

    def add(heading, value):
        if value and str(value).strip():
            lines.append(f"### {heading}\n{value}\n")

    add("Scheme Name",          scheme_name)
    add("Short Title",          short_title)
    add("Ministry",             ministry)
    add("Level",                level)
    add("Category",             ", ".join(categories))
    add("Target Beneficiaries", ", ".join(beneficiaries))
    add("Tags",                 ", ".join(tags))
    add("Description",          description)
    add("Benefits",             benefits)
    add("Eligibility",          eligibility)
    add("Application Process",  app_process)
    add("Required Documents",   docs_text)

    return "\n".join(lines) if lines else json.dumps(raw, indent=2, ensure_ascii=False)


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("=" * 52)
    print("  STEP 0 — Get Next.js Build ID")
    print("=" * 52)
    BUILD_ID = get_build_id()

    print("\n" + "=" * 52)
    print("  STEP 1 — Collect slugs + IDs from List API")
    print("=" * 52)
    scheme_list = get_all_slugs(max_schemes=100)
    print(f"\n  Total collected: {len(scheme_list)}")

    if not scheme_list:
        print("  No schemes — check API key")
        exit(1)

    print("\n" + "=" * 52)
    print("  STEP 2 — Fetch details + documents per scheme")
    print("=" * 52)

    saved = 0
    for i, (slug, scheme_id) in enumerate(scheme_list):
        print(f"  [{i:04d}] {slug}", end=" ... ", flush=True)

        raw  = fetch_detail(slug)
        docs = fetch_documents(scheme_id)

        if not raw.get("data"):
            print("⚠ empty — skipping")
            continue

        text  = flatten_scheme(raw, slug, docs)
        fname = f"data/scheme_{i:04d}_{slug[:45]}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"SOURCE: https://www.myscheme.gov.in/schemes/{slug}\n\n{text}")

        print(f"✓ saved ({len(text)} chars)")
        saved += 1
        time.sleep(0.8)

    print(f"\n{'=' * 52}")
    print(f"  Done — {saved} files saved to /data/")
    print(f"  Next step → python ingest.py")
    print(f"{'=' * 52}")
