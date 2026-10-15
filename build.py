#!/usr/bin/env python3
"""VoiceIQ site builder.

Reads config.json, the templates, and the articles in content/posts/*.md,
and writes the finished website into the dist/ folder.

Run it with:   python build.py
Needs:         pip install markdown
"""
import base64, datetime, hashlib, html, json, math, re, shutil, sys
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote, urlparse

try:
    import markdown
except ImportError:
    sys.exit("The Markdown package is missing. Run:  pip install markdown")

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
CFG = json.loads((ROOT / "config.json").read_text("utf-8"))

SITE = CFG["site_url"].rstrip("/")            # where this site lives
APP = CFG["app_url"].rstrip("/")              # where the dashboard lives
BASE = urlparse(SITE).path.rstrip("/")        # "" on your own domain, "/landing" on github.io/landing
NAME = CFG.get("newsletter_name", "Maoni")
TAGLINE = CFG.get("newsletter_tagline", "One idea a week on turning comments into customers.")
FORM = (CFG.get("newsletter_form_url") or "").strip()
CHANNEL = (CFG.get("whatsapp_channel_url") or "").strip()
WARN = []


def is_placeholder(v):
    v = (v or "").strip()
    return (not v) or "XXXX" in v or "YOUR-DOMAIN" in v or v.startswith("[")


WA_OK = not is_placeholder(CFG.get("whatsapp_number"))
EMAIL_OK = not is_placeholder(CFG.get("support_email"))
CO_OK = not is_placeholder(CFG.get("company_name"))
WA = "https://wa.me/" + re.sub(r"\D", "", CFG.get("whatsapp_number", "")) + "?text=" + quote("Hi VoiceIQ, I have a question.")
EMAIL = CFG.get("support_email", "")
COMPANY = CFG["company_name"] if CO_OK else "VoiceIQ"
if not WA_OK: WARN.append("whatsapp_number is not set: the WhatsApp buttons are hidden")
if not EMAIL_OK: WARN.append("support_email is not set: the email links are hidden")
if not CO_OK: WARN.append("company_name is not set: the footer shows VoiceIQ")
if not FORM: WARN.append("newsletter_form_url is not set: the newsletter box shows the simple email and WhatsApp buttons instead")


def esc(s): return html.escape(str(s), quote=True)
def P(path=""): return BASE + "/" + path.lstrip("/")           # a link on this site
def U(path=""): return SITE + "/" + path.lstrip("/")           # a full address


def render(tpl, **kw):
    def sub(m):
        k = m.group(1)
        if k not in kw: raise KeyError(f"template placeholder {{{{{k}}}}} has no value")
        return str(kw[k])
    return re.sub(r"\{\{(\w+)\}\}", sub, tpl)


# ---------------------------------------------------------------- articles
def parse_post(path):
    raw = path.read_text("utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if not m:
        WARN.append(f"{path.name}: missing the --- header block, skipped"); return None
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1); meta[k.strip().lower()] = v.strip()
    for need in ("title", "date", "summary"):
        if not meta.get(need):
            WARN.append(f"{path.name}: header is missing '{need}', skipped"); return None
    if meta.get("draft", "").lower() in ("true", "yes"): return None
    try: date = datetime.date.fromisoformat(meta["date"])
    except ValueError:
        WARN.append(f"{path.name}: date must look like 2026-10-13, skipped"); return None
    body_md = m.group(2)
    words = len(re.findall(r"\w+", body_md))
    return {
        "slug": path.stem, "title": meta["title"], "summary": meta["summary"], "date": date,
        "date_h": f"{date.day} {date.strftime('%B %Y')}", "read": max(1, math.ceil(words / 200)),
        "body": markdown.markdown(body_md, extensions=["extra", "sane_lists"]),
    }


posts = [p for p in (parse_post(f) for f in sorted((ROOT / "content/posts").glob("*.md"))) if p]
posts.sort(key=lambda p: p["date"], reverse=True)


def meta_html(p): return f'<span class="meta"><span>{esc(p["date_h"])}</span><span>{p["read"]} min read</span></span>'


# ---------------------------------------------------------------- shared pieces
INLINE = "document.documentElement.classList.add('js')"
JS_HASH = base64.b64encode(hashlib.sha256(INLINE.encode()).digest()).decode()
FRAME = ""
if FORM:
    host = urlparse(FORM).netloc
    if host: FRAME = f" frame-src https://{host};"
CSP = ("default-src 'none'; style-src 'self' 'unsafe-inline'; script-src 'self' 'sha256-%s'; font-src 'self'; "
       "img-src 'self' data:;%s base-uri 'none'; form-action 'none'; connect-src 'none'" % (JS_HASH, FRAME))

MARK = ('<svg viewBox="0 0 64 64" aria-hidden="true"><defs><radialGradient id="mk" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#C9F5DF"/>'
        '<stop offset=".55" stop-color="#2FAE74"/><stop offset="1" stop-color="#0B5A3A"/></radialGradient></defs><circle cx="32" cy="32" r="21" fill="url(#mk)"/>'
        '<path d="M6 37c8-16 15-16 26 0s18 16 26 0" fill="none" stroke="#F4B73F" stroke-width="6" stroke-linecap="round"/></svg>')
WA_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5.2 14.1c-.2.6-1.2 1.2-1.7 1.2-.4.1-1 .2-3.1-.7-2.6-1.1-4.2-3.7-4.3-3.9-.1-.2-1-1.3-1-2.5s.6-1.8.9-2.1c.2-.2.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.8 1.9c.1.2.1.3 0 .5l-.4.6c-.1.1-.2.3-.1.5.5.8 1.1 1.4 1.8 1.9.6.4 1.1.6 1.4.7.2.1.4 0 .5-.1l.6-.7c.2-.2.3-.2.5-.1l1.8.9c.2.1.4.2.4.3.1.2.1.8-.1 1.4z"/></svg>')


def head(title, desc, path, og_type="website", jsonld=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{esc(CSP)}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#062A1B">
<link rel="canonical" href="{esc(U(path))}">
<link rel="icon" href="{P('favicon.svg')}" type="image/svg+xml">
<link rel="icon" href="{P('favicon-32.png')}" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{P('apple-touch-icon.png')}">
<link rel="alternate" type="application/rss+xml" title="{esc(NAME)} by VoiceIQ" href="{P('insights/feed.xml')}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="VoiceIQ">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(U(path))}">
<meta property="og:image" content="{esc(U('og-image.png'))}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" href="{P('fonts/bricolage-grotesque-latin-800-normal.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{P('fonts/bricolage-grotesque-latin-400-normal.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{P('css/site.css')}">
<script>{INLINE}</script>
{jsonld}
</head>
<body>
"""


def header(home):
    a = (lambda h: h) if home else (lambda h: P("") + h)
    links = [("What you get", a("#get")), ("Try it", a("#try")), ("Who it is for", a("#who")), ("Pricing", a("#pricing")), ("Insights", P("insights/")), ("Questions", a("#faq"))]
    nav = "".join(f'<a href="{h}">{t}</a>' for t, h in links)
    menu = "".join(f'<a href="{h}">{t}</a>' for t, h in links)
    return f"""<div class="progress" aria-hidden="true"></div>
<a class="skip" href="#main">Skip to the content</a>
<header class="site-head">
  <div class="wrap bar">
    <a class="brand" href="{P('')}" aria-label="VoiceIQ home">{MARK}VoiceIQ</a>
    <nav class="nav" aria-label="Main">{nav}</nav>
    <div class="bar-cta"><a href="{APP}/">Sign in</a><a class="btn btn-gold" href="{APP}/">Start free</a></div>
    <details class="menu"><summary>Menu</summary><div class="menu-list">{menu}<a href="{APP}/">Sign in</a><a class="btn btn-gold" href="{APP}/">Start free</a></div></details>
  </div>
</header>
"""


def footer():
    follow = []
    if CHANNEL: follow.append(f'<li><a href="{esc(CHANNEL)}" rel="noopener">WhatsApp channel</a></li>')
    if WA_OK: follow.append(f'<li><a href="{esc(WA)}" rel="noopener">Chat on WhatsApp</a></li>')
    follow.append(f'<li><a href="{P("insights/feed.xml")}">RSS feed</a></li>')
    company = [f'<li><a href="{APP}/privacy.html">Privacy</a></li>', f'<li><a href="{APP}/terms.html">Terms</a></li>', f'<li><a href="{APP}/data-deletion.html">Delete your data</a></li>']
    if EMAIL_OK: company.append(f'<li><a href="mailto:{esc(EMAIL)}">{esc(EMAIL)}</a></li>')
    sticky = f'<a class="btn wa" href="{esc(WA)}" aria-label="Chat on WhatsApp" rel="noopener">{WA_ICON}</a>' if WA_OK else ""
    float_ = f'<a class="wa-float" href="{esc(WA)}" aria-label="Chat with us on WhatsApp" rel="noopener">{WA_ICON}</a>' if WA_OK else ""
    return f"""<footer>
  <div class="wrap">
    <div class="foot">
      <div><a class="brand" href="{P('')}" style="font-size:1.25rem">{MARK.replace('id="mk"','id="mk2"').replace('url(#mk)','url(#mk2)')}VoiceIQ</a><p style="margin-top:12px;max-width:22em">Hear every voice. Act on what matters. Made in Kenya.</p></div>
      <div><h2>Product</h2><ul><li><a href="{P('')}#get">What you get</a></li><li><a href="{P('')}#pricing">Pricing</a></li><li><a href="{P('insights/')}">Insights</a></li><li><a href="{APP}/">Sign in</a></li></ul></div>
      <div><h2>Company</h2><ul>{''.join(company)}</ul></div>
      <div><h2>Follow</h2><ul>{''.join(follow)}</ul></div>
    </div>
    <div class="legal"><span>&copy; 2026 {esc(COMPANY)}</span><span>Made in Kenya</span></div>
  </div>
</footer>
<div class="sticky-cta"><a class="btn btn-gold" href="{APP}/">Start free</a>{sticky}</div>
{float_}
<script src="{P('js/site.js')}" defer></script>
</body>
</html>
"""


def newsletter():
    if FORM:
        return (f'<div class="nl"><iframe src="{esc(FORM)}" title="Subscribe to {esc(NAME)}" loading="lazy"></iframe>'
                f'<p class="fine">Free. Unsubscribe at any time. See our <a href="{APP}/privacy.html" style="font-weight:600">privacy policy</a>.</p></div>')
    buttons = []
    if EMAIL_OK:
        subj = quote(f"Subscribe me to {NAME}")
        body = quote(f"Please add me to the {NAME} newsletter. I agree to receive emails and I can unsubscribe at any time.")
        buttons.append(f'<a class="btn btn-ink" href="mailto:{esc(EMAIL)}?subject={subj}&amp;body={body}">Get it by email</a>')
    if CHANNEL: buttons.append(f'<a class="btn btn-line-ink" href="{esc(CHANNEL)}" rel="noopener">Follow on WhatsApp</a>')
    if buttons:
        return (f'<div class="nl"><p><b>Get {esc(NAME)} free.</b> Choose how you want to read it.</p><div class="cta-row">{"".join(buttons)}</div>'
                f'<p class="fine">Free. Unsubscribe or leave at any time. See our <a href="{APP}/privacy.html" style="font-weight:600">privacy policy</a>.</p></div>')
    return f'<div class="nl"><p><b>{esc(NAME)} is opening soon.</b> In the meantime, read the articles and start free.</p><div class="cta-row"><a class="btn btn-ink" href="{APP}/">Start free</a></div></div>'


# ---------------------------------------------------------------- landing page content
WALL1 = [("Bei ni ngapi? Mko wapi Kisumu?", "buy", "Ready to buy", "sw"), ("Do you cater for weddings? We are 150 people.", "buy", "Ready to buy", "en"),
         ("Hongera! Chapati zenu ni tamu sana.", "good", "Praise", "sw"), ("Mnapatikana Eldoret?", "ask", "Question", "sw"),
         ("Naomba namba yenu, nataka kuagiza.", "buy", "Ready to buy", "sw"), ("Best nyama choma in town, period.", "good", "Praise", "en"),
         ("Do you deliver to Kitengela?", "ask", "Question", "en"), ("Nipe bei ya kilo tano.", "buy", "Ready to buy", "sw")]
WALL2 = [("Delivery took 2 hours and the food was cold.", "bad", "Problem", "en"), ("Nimeagiza jana bado sijapata. Mko serious?", "bad", "Problem", "sw"),
         ("Why did the price go up again?", "bad", "Problem", "en"), ("Asanteni kwa huduma nzuri leo.", "good", "Praise", "sw"),
         ("Nobody replies in inbox, please check.", "bad", "Problem", "en"), ("Mna offer ya weekend?", "ask", "Question", "sw"),
         ("Wrong order again. This is the third time.", "bad", "Problem", "en"), ("Staff were so rude at the counter.", "bad", "Problem", "en")]


def wall(items, rev=False):
    one = "".join(f'<span class="wc"><span lang="{l}">{esc(t)}</span><span class="tag t-{k}">{lab}</span></span>' for t, k, lab, l in items)
    dup = one.replace('<span class="wc">', '<span class="wc" aria-hidden="true">')
    return f'<div class="wall-row{" rev" if rev else ""}">{one}{dup}</div>'


DEMO = [
    {"text": "Bei ni ngapi? Mko wapi Kisumu?", "lang": "sw", "tag": "buy", "label": "Ready to buy",
     "why": "Asks the price and the location in one line. Both are buying questions.", "next": "Reply within the hour with the price and where you are.",
     "reply": "Karibu! Tuko Kisumu mjini. Tutakutumia bei sasa hivi, tuandikie nambari yako.", "replyLang": "sw"},
    {"text": "Do you cater for weddings? We are 150 people in November.", "lang": "en", "tag": "buy", "label": "Ready to buy",
     "why": "A large order with a date and a head count. This is a hot lead.", "next": "Call today, and send a quote with the date confirmed.",
     "reply": "Yes, we cater for weddings of any size. Send us the date and your number and we will call you today.", "replyLang": "en"},
    {"text": "Nimeagiza jana bado sijapata. Mko serious?", "lang": "sw", "tag": "bad", "label": "Problem",
     "why": "An order that has not arrived, and growing frustration. Likely to become a public complaint.", "next": "Reply first today. Find the order, then update them.",
     "reply": "Pole sana kwa usumbufu. Tafadhali tutumie namba ya oda, tutaangalia sasa hivi.", "replyLang": "sw"},
    {"text": "Delivery took 2 hours and the food was cold.", "lang": "en", "tag": "bad", "label": "Problem",
     "why": "A complaint about speed and temperature. Counted with similar comments under delivery.", "next": "Apologise in public, offer a fix, and track delivery times.",
     "reply": "Sorry about that. We are fixing our delivery times. Please send us your order number and we will make it right.", "replyLang": "en"},
    {"text": "Mnapatikana Eldoret?", "lang": "sw", "tag": "ask", "label": "Question",
     "why": "Asks whether you serve a new town. One person asking is a hint, many asking is demand.", "next": "Answer clearly, and keep count of every town people ask about.",
     "reply": "Kwa sasa hatuko Eldoret, lakini tunafikisha oda. Tuambie ulipo.", "replyLang": "sw"},
    {"text": "Hongera! Chapati zenu ni tamu sana.", "lang": "sw", "tag": "good", "label": "Praise",
     "why": "Warm praise for a product. Good material for a thank-you and a share.", "next": "Thank them, and ask them to tell a friend or leave a review.",
     "reply": "Asante sana! Karibu tena. Ukiwaambia marafiki zako, tutashukuru sana.", "replyLang": "sw"},
]


def landing():
    d0 = DEMO[0]
    latest = "".join(
        f'<li><a href="{P("insights/" + p["slug"] + "/")}"><span class="t">{esc(p["title"])}</span><span class="s">{esc(p["summary"])}</span>{meta_html(p)}</a></li>'
        for p in posts[:3]) or "<li><p>Articles are on the way.</p></li>"
    picks = "".join(f'<button type="button" class="pick" aria-pressed="{"true" if i == 0 else "false"}" lang="{x["lang"]}">{esc(x["text"])}</button>' for i, x in enumerate(DEMO))
    tl = TAGLINE[0].lower() + TAGLINE[1:]
    body = render((ROOT / "templates/landing.html").read_text("utf-8"),
        app=APP, base=BASE, wall1=wall(WALL1), wall2=wall(WALL2, True), demo_picks=picks, demo_json=json.dumps(DEMO, ensure_ascii=False).replace("</", "<\\/"),
        d0_text=esc(d0["text"]), d0_lang=d0["lang"], d0_tag=d0["tag"], d0_label=d0["label"], d0_why=esc(d0["why"]), d0_next=esc(d0["next"]),
        d0_reply=esc(d0["reply"]), d0_replylang=d0["replyLang"], newsletter=newsletter(), latest_posts=latest, nl_name=esc(NAME), nl_tagline_lc=esc(tl),
        wa_btn=(f'<a class="btn btn-line-d" href="{esc(WA)}" rel="noopener">Talk to us on WhatsApp</a>' if WA_OK else ""),
        faq_contact=("Anything else, message us on WhatsApp." if WA_OK else "Anything else, write to us."))
    ld = {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "VoiceIQ", "applicationCategory": "BusinessApplication", "operatingSystem": "Web",
          "description": "Comment intelligence for Kenya. Reads customer comments in English, Kiswahili and Sheng and shows who is ready to buy, what is going wrong and what to do next.",
          "offers": [{"@type": "Offer", "name": "Monthly Standard", "price": "7000", "priceCurrency": "KES"}, {"@type": "Offer", "name": "Monthly Pro", "price": "15000", "priceCurrency": "KES"},
                     {"@type": "Offer", "name": "Single analysis", "price": "2000", "priceCurrency": "KES"}]}
    return (head("VoiceIQ: turn customer comments into customers, fixes and next steps",
                 "Paste your Facebook, TikTok, YouTube or Google comments. VoiceIQ reads English, Kiswahili and Sheng and shows who will buy, what is wrong and what to do.",
                 "", jsonld=f'<script type="application/ld+json">{json.dumps(ld)}</script>') + header(True) + body + footer())


def post_rows(items, cls=""):
    return "".join(f'<li><a href="{P("insights/" + p["slug"] + "/")}"><span class="t">{esc(p["title"])}</span><span class="s">{esc(p["summary"])}</span>{meta_html(p)}</a></li>' for p in items)


def write(rel, text):
    f = DIST / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text, "utf-8")


# ---------------------------------------------------------------- build
if DIST.exists(): shutil.rmtree(DIST)
shutil.copytree(ROOT / "static", DIST)
(DIST / ".nojekyll").write_text("")
write("index.html", landing())

# insights list
if posts:
    f0 = posts[0]
    feature = (f'<a class="feature" href="{P("insights/" + f0["slug"] + "/")}"><span class="t">{esc(f0["title"])}</span><span class="s">{esc(f0["summary"])}</span>{meta_html(f0)}</a>')
    rows = post_rows(posts[1:])
else:
    feature, rows = '<p class="lead muted-l">The first articles are on the way.</p>', ""
write("insights/index.html", head(f"Insights: practical ideas on turning comments into customers | VoiceIQ", "Practical articles for Kenyan businesses, leaders, churches, schools and agencies on turning comments into customers.", "insights/")
      + header(False) + render((ROOT / "templates/insights.html").read_text("utf-8"), base=BASE, nl_name=esc(NAME), nl_tagline=esc(TAGLINE), feature=feature, rows=rows, newsletter=newsletter()) + footer())

# every article
tpl = (ROOT / "templates/post.html").read_text("utf-8")
for p in posts:
    path = f"insights/{p['slug']}/"
    others = [x for x in posts if x is not p][:2]
    more = (f'<section class="sec sec-alt"><div class="wrap"><h2>Keep reading</h2><ul class="plist" style="margin-top:24px">{post_rows(others)}</ul></div></section>' if others else "")
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": p["title"], "description": p["summary"], "datePublished": p["date"].isoformat(),
          "mainEntityOfPage": U(path), "image": U("og-image.png"), "publisher": {"@type": "Organization", "name": "VoiceIQ"}}
    page = (head(f'{p["title"]} | VoiceIQ', p["summary"], path, og_type="article", jsonld=f'<script type="application/ld+json">{json.dumps(ld)}</script>') + header(False)
            + render(tpl, base=BASE, app=APP, title=esc(p["title"]), summary=esc(p["summary"]), date_h=esc(p["date_h"]), read=p["read"], body=p["body"],
                     share=quote(f'{p["title"]} {U(path)}'), nl_name=esc(NAME), nl_tagline=esc(TAGLINE), newsletter=newsletter(), more=more) + footer())
    write(path + "index.html", page)

# 404, feed, sitemap, robots
write("404.html", head("Page not found | VoiceIQ", "That page is not here.", "404.html") + header(False) + render((ROOT / "templates/notfound.html").read_text("utf-8"), base=BASE) + footer())
items = "".join(
    f'<item><title>{esc(p["title"])}</title><link>{esc(U("insights/" + p["slug"] + "/"))}</link><guid>{esc(U("insights/" + p["slug"] + "/"))}</guid>'
    f'<pubDate>{format_datetime(datetime.datetime(p["date"].year, p["date"].month, p["date"].day, 8, 0, tzinfo=datetime.timezone.utc))}</pubDate><description>{esc(p["summary"])}</description></item>'
    for p in posts)
write("insights/feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{esc(NAME)} by VoiceIQ</title><link>{esc(U("insights/"))}</link><description>{esc(TAGLINE)}</description><language>en</language>{items}</channel></rss>')
urls = [(U(""), None), (U("insights/"), None)] + [(U(f"insights/{p['slug']}/"), p["date"].isoformat()) for p in posts]
write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
      + "".join(f"<url><loc>{esc(u)}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>" for u, d in urls) + "</urlset>")
write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {U('sitemap.xml')}\n")

print(f"Built {len(posts)} article(s) into {DIST}")
for w in WARN: print("  note:", w)
