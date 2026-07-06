#!/usr/bin/env python3
# (C) MCL Electric site verifier — runs in CI on every push and locally.
# Checks: sitemap parity, internal links, required tags, NAP consistency,
# accessibility basics, no-secrets, residential-privacy pattern.
# Exit 0 = pass, 1 = fail (blocks deploy confidence, prints every violation).
import os, re, sys, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
PHONE = "(872) 378-0533"
OLD_PHONES = ["(312) 301-0388", "312-301-0388", "3123010388"]
EMAIL = "info@mclelectric.org"
# Residential streets are public (street+city only); a number directly before
# one is a privacy violation (never publish house numbers of homes).
RES_STREETS = r"\d+\s+(N\.?\s|S\.?\s|E\.?\s|W\.?\s)?(Acorn|Richmond|Maplewood|Braxton|Champlain|Fargo)"
SECRETS = r"(api[_-]?key|client[_-]?secret|BEGIN (RSA|EC|OPENSSH) PRIVATE|ghp_[A-Za-z0-9]{20,})"

fails = []
def fail(page, msg): fails.append(f"  {page}: {msg}")

pages = sorted(glob.glob(os.path.join(ROOT, "**", "index.html"), recursive=True))
pages += [os.path.join(ROOT, "404.html")]
rel = lambda p: os.path.relpath(p, ROOT)

# ── sitemap parity ──
with open(os.path.join(ROOT, "sitemap.xml")) as f: sm = f.read()
sm_urls = set(re.findall(r"<loc>(.*?)</loc>", sm))
for u in sm_urls:
    path = u.replace("https://mclelectric.org", ROOT).rstrip("/")
    target = path + ("/index.html" if not path.endswith(".html") else "")
    if u == "https://mclelectric.org/": target = os.path.join(ROOT, "index.html")
    if not os.path.exists(target): fail("sitemap.xml", f"lists {u} but no file")
for p in pages:
    if p.endswith("404.html") or "/thanks/" in p or "/privacy/" in p or "/accessibility/" in p:
        continue  # intentionally out of sitemap
    url = "https://mclelectric.org/" + re.sub(r"index\.html$", "", rel(p)).rstrip("/")
    url = (url + "/") if url != "https://mclelectric.org" else url + "/"
    if url.rstrip("/") + "/" not in {x if x.endswith("/") else x + "/" for x in sm_urls}:
        fail(rel(p), "page exists but missing from sitemap.xml")

# ── per-page checks ──
for p in pages:
    if not os.path.exists(p): continue
    with open(p) as f: html = f.read()
    name = rel(p)
    if "<title>" not in html: fail(name, "missing <title>")
    if 'name="description"' not in html: fail(name, "missing meta description")
    if 'rel="canonical"' not in html and not p.endswith("404.html"):
        fail(name, "missing canonical")
    if '<html lang="en">' not in html: fail(name, 'missing lang="en"')
    if 'class="skip-link"' not in html: fail(name, "missing skip-link (a11y)")
    if '<main id="main">' not in html and "<main" not in html: fail(name, "missing <main> landmark")
    if PHONE not in html: fail(name, f"missing current phone {PHONE}")
    for old in OLD_PHONES:
        if old in html: fail(name, f"contains OLD phone {old}")
    for m in re.finditer(r"<img\b[^>]*>", html):
        if "alt=" not in m.group(0): fail(name, f"img without alt: {m.group(0)[:60]}")
    if re.search(RES_STREETS, html):
        fail(name, "HOUSE NUMBER before a residential street name (privacy rule)")
    if re.search(SECRETS, html, re.I): fail(name, "possible secret/credential")
    # internal link integrity
    for href in re.findall(r'href="(/[^"#]*)"', html):
        if href.startswith("//"): continue
        t = os.path.join(ROOT, href.lstrip("/").rstrip("/"))
        ok = (os.path.exists(t) or os.path.exists(t + "/index.html")
              or os.path.exists(t + ".html") or os.path.exists(os.path.join(ROOT, href.lstrip("/"))))
        if not ok: fail(name, f"broken internal link {href}")

print(f"checked {len(pages)} pages, {len(sm_urls)} sitemap URLs")
if fails:
    print("FAIL:"); print("\n".join(fails)); sys.exit(1)
print("PASS — all checks clean")
