#!/usr/bin/env python3
"""生成済みサイトの静的な点検（標準ライブラリ＋Pillow＋pypdf）。
使い方: python3 tools/check_site.py          （先に python3 tools/build.py を実行）
終了コード: 重大な問題があれば 1。"""
import re, sys, pathlib, json, html, os
from html.parser import HTMLParser
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {'.git', 'templates', 'tools', 'data', 'docs', '.github', 'node_modules'}
problems = defaultdict(list)    # 重大
warnings = defaultdict(list)    # 注意

def add(kind, level, msg):
    (problems if level == 'ERR' else warnings)[kind].append(msg)

pages = [p for p in ROOT.rglob('*.html') if not (set(p.relative_to(ROOT).parts) & SKIP_DIRS)]

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags = []; self.ids = Counter(); self.title = ''; self._t = False
        self.h = []; self.imgs = []; self.links = []; self.meta = {}; self.canon = ''; self._h = None; self.hbuf = ''
        self.ext_scripts = []; self.ext_css = []; self.empty_links = 0; self._a = None; self.abuf = ''; self.iframes = []
    def handle_starttag(self, t, a):
        a = dict(a)
        if 'id' in a: self.ids[a['id']] += 1
        if t == 'title': self._t = True
        if t in ('h1','h2','h3','h4','h5','h6'): self._h = t; self.hbuf = ''
        if t == 'img':
            self.imgs.append(a)
            if self._a is not None: self.abuf += a.get('alt', '')
        if t == 'a':
            self.links.append(a); self._a = a; self.abuf = ''
        if t == 'meta' and a.get('name'): self.meta[a['name']] = a.get('content', '')
        if t == 'link' and a.get('rel') == 'canonical': self.canon = a.get('href', '')
        if t == 'link' and a.get('rel') == 'stylesheet' and (a.get('href', '').startswith('http')): self.ext_css.append(a['href'])
        if t == 'script' and a.get('src', '').startswith('http'): self.ext_scripts.append(a['src'])
        if t == 'iframe': self.iframes.append(a.get('src', ''))
    def handle_endtag(self, t):
        if t == 'title': self._t = False
        if t == self._h: self.h.append((t, self.hbuf.strip())); self._h = None
        if t == 'a' and self._a is not None:
            if not self.abuf.strip() and not self._a.get('aria-label'): self.empty_links += 1
            self._a = None
    def handle_data(self, d):
        if self._t: self.title += d
        if self._h: self.hbuf += d
        if self._a is not None: self.abuf += d

def rel(p): return str(p.relative_to(ROOT))

titles = Counter(); descs = Counter(); texts = {}
for f in sorted(pages):
    src = f.read_text(encoding='utf-8'); p = P(); p.feed(src); n = rel(f)
    if f.name == '404.html': pass
    if not p.title.strip(): add('タイトル', 'ERR', n)
    titles[p.title.strip()] += 1
    d = p.meta.get('description', '')
    if not d: add('説明文（description）なし', 'WARN', n)
    descs[d] += 1
    h1 = [x for x in p.h if x[0] == 'h1']
    if len(h1) != 1: add('h1の数が1でない', 'ERR', '%s（%d個）' % (n, len(h1)))
    last = 1
    for t, txt in p.h:
        lv = int(t[1])
        if lv > last + 1: add('見出しのレベル飛び', 'WARN', '%s：%s の前に h%d がない' % (n, t, last + 1)); break
        last = lv
    for t, txt in p.h:
        if not txt: add('空の見出し', 'ERR', n)
    for k, c in p.ids.items():
        if c > 1: add('idの重複', 'ERR', '%s：%s' % (n, k))
    for im in p.imgs:
        if 'alt' not in im: add('画像にaltなし', 'ERR', '%s：%s' % (n, im.get('src')))
        elif not im['alt'].strip() and 'icon' not in im.get('src', '') and 'favicon' not in im.get('src', ''): add('altが空の画像（装飾以外）', 'WARN', '%s：%s' % (n, im.get('src')))
        if 'width' not in im or 'height' not in im: add('画像に width/height なし（表示のずれ）', 'WARN', '%s：%s' % (n, im.get('src')))
    if p.empty_links: add('文字のないリンク', 'ERR', '%s（%d個）' % (n, p.empty_links))
    if p.ext_scripts: add('外部スクリプトの読み込み', 'ERR', '%s：%s' % (n, p.ext_scripts))
    if p.ext_css: add('外部CSSの読み込み', 'ERR', '%s：%s' % (n, p.ext_css))
    if p.iframes: add('iframe（外部埋め込み）', 'WARN', '%s：%s' % (n, p.iframes))
    for a in p.links:
        h = a.get('href', '')
        if not h:
            add('hrefなしのリンク', 'ERR', n); continue
        if h.startswith('http'):
            if a.get('target') == '_blank' and 'noopener' not in a.get('rel', ''): add('target=_blank に noopener なし', 'ERR', '%s：%s' % (n, h))
            if 'kurume-dental.or.jp' in h: add('旧サイトへのリンク', 'WARN', '%s：%s' % (n, h))
            if h.startswith('http://'): add('http（暗号化なし）のリンク', 'ERR', '%s：%s' % (n, h))
    # 内部リンク・画像の存在
    for u in re.findall(r'(?:href|src)="([^"#?]+)"', src):
        if u.startswith(('http', 'mailto', 'tel', '/', 'data:')): continue
        q = (f.parent / u); q = q / 'index.html' if u.endswith('/') else q
        if not q.exists(): add('リンク・画像が見つからない', 'ERR', '%s：%s' % (n, u))
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', src, flags=re.S); t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    texts[n] = t
    for k in ('【要確認', '（準備中）', '（仮）', 'TODO', '@@'):
        c = t.count(k)
        if c: add('未完成の印が残っている：' + k, 'WARN', '%s（%d）' % (n, c))
    for m in set(re.findall(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+', t)): add('メールアドレスが本文に書かれている', 'ERR', '%s：%s' % (n, m))

for k, c in titles.items():
    if c > 1 and k: add('同じタイトルのページがある', 'WARN', '「%s」が%d件' % (k, c))
for k, c in descs.items():
    if c > 1 and k: add('同じ説明文のページがある', 'WARN', '%d件（%s…）' % (c, k[:24]))

# sitemap と robots
sm = (ROOT / 'sitemap.xml').read_text(encoding='utf-8') if (ROOT / 'sitemap.xml').exists() else ''
urls = re.findall(r'<loc>([^<]+)</loc>', sm)
site = json.loads((ROOT / 'data/site.json').read_text(encoding='utf-8'))
for f in pages:
    if f.name == '404.html': continue
    path = '/' + rel(f).replace('index.html', '')
    if not any(u.endswith(path) or u == site['origin'] + path for u in urls): add('sitemapにないページ', 'WARN', rel(f))
if not (ROOT / 'robots.txt').exists(): add('robots.txtなし', 'ERR', '')

# ファイルの容量・使われていないファイル
all_text = ''.join(p.read_text(encoding='utf-8') for p in pages) + ''.join(p.read_text(encoding='utf-8') for p in ROOT.glob('assets/css/*.css')) + ''.join(p.read_text(encoding='utf-8') for p in ROOT.glob('assets/js/*.js'))
big = []; orphan = []
for f in ROOT.joinpath('assets').rglob('*'):
    if not f.is_file(): continue
    sz = f.stat().st_size
    if sz > 600 * 1024 and f.suffix.lower() != '.pdf': big.append('%s（%dKB）' % (f.relative_to(ROOT), sz // 1024))
    if sz > 3 * 1024 * 1024: add('3MBを超えるファイル', 'WARN', '%s（%.1fMB）' % (f.relative_to(ROOT), sz / 1048576))
    r = str(f.relative_to(ROOT)); name = f.name
    if r not in all_text and name not in all_text and not name.startswith('thumb-'): orphan.append(r)
if big: add('大きい画像（600KB超）', 'WARN', '、'.join(big))
if orphan: add('どのページからも使われていないファイル', 'WARN', '、'.join(orphan))

# 画像のEXIF（位置情報・カメラ情報）とPDFのメタデータ
try:
    from PIL import Image
    for f in ROOT.joinpath('assets').rglob('*'):
        if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
            ex = Image.open(f).getexif()
            if ex: add('画像にEXIF情報が残っている', 'ERR', '%s%s' % (f.relative_to(ROOT), '（GPSあり）' if 34853 in ex else ''))
except ImportError:
    add('Pillowがないため、画像のEXIFを点検できない', 'WARN', '')
try:
    from pypdf import PdfReader
    for f in ROOT.joinpath('assets').rglob('*.pdf'):
        md = PdfReader(f).metadata or {}
        for k in ('/Author', '/Creator', '/Subject', '/Keywords'):
            if md.get(k): add('PDFに作成者などの情報が残っている', 'ERR', '%s：%s=%s' % (f.relative_to(ROOT), k, md.get(k)))
except ImportError:
    add('pypdfがないため、PDFのメタデータを点検できない', 'WARN', '')

# 本文の誤字らしい表現（旧サイトの文章に含まれていたもの）
pat = [(r'をを', '「をを」（重複）'), (r'ください下さい', '「ください下さい」（重複）'), (r'のいただ', '「のいただ…」（「の」が余分？）'),
       (r'本呼応', '「本呼応」（「本校」の誤記？）'), (r'ご覧くださいませ', ''), (r'ですます', '')]
for n, t in texts.items():
    for rx, label in pat:
        if label and re.search(rx, t): add('誤字・重複の疑い', 'WARN', '%s：%s' % (n, label))

def show(title, d):
    n = sum(len(v) for v in d.values())
    print('\n=== %s：%d件 ===' % (title, n))
    for k, v in d.items():
        print('・%s（%d）' % (k, len(v)))
        for x in v[:6]: print('    - ' + x)
        if len(v) > 6: print('    …ほか%d件' % (len(v) - 6))

print('点検したページ：%d' % len(pages))
show('重大な問題', problems); show('注意', warnings)
sys.exit(1 if problems else 0)
