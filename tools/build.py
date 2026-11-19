#!/usr/bin/env python3
"""静的サイトの生成。data/ と templates/ から HTML・sitemap.xml・robots.txt・404.html を作る。
使い方: python3 tools/build.py（Python標準ライブラリのみ）"""
import json, html, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
site = json.loads((ROOT/'data/site.json').read_text(encoding='utf-8'))
pages = json.loads((ROOT/'data/pages.json').read_text(encoding='utf-8'))
_imp = ROOT/'data/imported_pages.json'
if _imp.exists(): pages += json.loads(_imp.read_text(encoding='utf-8'))
news = json.loads((ROOT/'data/news.json').read_text(encoding='utf-8')) if (ROOT/'data/news.json').exists() else []
tpl = lambda n: (ROOT/'templates'/n).read_text(encoding='utf-8')
YEAR = str(datetime.date.today().year)
e = html.escape

def news_html(R, limit=5):
    if not news: return '<p>お知らせはありません。</p>'
    return '<ul class="news">' + ''.join('<li><span>%s</span> <a href="%snews/%s/">%s</a></li>' % (n['date'].replace('-', '.'), R, n['id'], e(n['title'])) for n in news[:limit]) + '</ul>'

def render(slug, title, lead, body, depth, canon_path):
    R = '../' * depth
    nav = ''.join('<a href="%s%s/"%s>%s</a>' % (R, s, ' aria-current="page"' if s == slug else '', e(t)) for s, t in site['nav'])
    page = tpl('header.html') + body + tpl('footer.html')
    page = page.replace('{{NEWS}}', news_html(R))
    full = site['name_ja'] if not slug else '%s | %s' % (title, site['name_ja'])
    rep = {'{{TITLE}}': e(full), '{{DESC}}': e(site['description']), '{{CANON}}': site['origin'] + canon_path,
           '{{NAV}}': nav, '{{FNAV}}': ' / '.join('<a href="%s%s/">%s</a>' % (R, s, e(n)) for s, n in site.get('footer_nav', [])), '{{NAME_JA}}': e(site['name_ja']), '{{NAME_EN}}': e(site['name_en']),
           '{{H1}}': e(title if slug else site['name_en']), '{{LEAD}}': e(lead), '{{ADDRESS}}': e(site['address']),
           '{{TEL}}': e(site['tel']), '{{YEAR}}': YEAR, '{{R}}': R}
    for k, v in rep.items():
        page = page.replace(k, v)
    return page

def write(rel, text):
    f = ROOT / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text, encoding='utf-8')

urls = []
for p in pages:
    s = p['slug']; depth = 1 if s else 0
    write((s + '/index.html') if s else 'index.html', render(s, p['title'], p['lead'], p['body'], depth, '/' + (s + '/' if s else '')))
    urls.append(site['origin'] + '/' + (s + '/' if s else ''))

# お知らせ（一覧と各記事）
write('news/index.html', render('news', 'お知らせ', '', '<section>' + news_html('../', 100) + '</section>', 1, '/news/'))
urls.append(site['origin'] + '/news/')
for n in news:
    write('news/%s/index.html' % n['id'], render('news', n['title'], n['date'].replace('-', '.'), '<section>%s</section>' % n['body'], 2, '/news/%s/' % n['id']))
    urls.append(site['origin'] + '/news/%s/' % n['id'])

# 404（どの階層からでも表示できるよう、サイトの根元を絶対パスで指す）
bp = site['base_path']
nf = render('404', 'ページが見つかりません', 'お探しのページは、移動または削除された可能性があります。',
            '<p><a class="btn" href="{{R}}">トップページへ戻る</a></p>', 0, '/404.html')
nf = nf.replace('href="assets/', 'href="%s/assets/' % bp).replace('src="assets/', 'src="%s/assets/' % bp)
nf = nf.replace('href="favicon', 'href="%s/favicon' % bp).replace('src="favicon', 'src="%s/favicon' % bp)
nf = nf.replace('href="about/', 'href="%s/about/' % bp)
for s, _ in site['nav']:
    nf = nf.replace('href="%s/"' % s, 'href="%s/%s/"' % (bp, s))
nf = nf.replace('href=""', 'href="%s/"' % bp).replace('href="privacy/"', 'href="%s/privacy/"' % bp)
write('404.html', nf)

write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      + ''.join('<url><loc>%s</loc></url>\n' % u for u in urls) + '</urlset>\n')
write('robots.txt', 'User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n' % site['origin'])
print('生成しました：%d ページ' % len(urls))
