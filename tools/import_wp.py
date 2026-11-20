#!/usr/bin/env python3
"""WordPress エクスポートXMLから、公開ページ・公開投稿だけを data/ に取り込む。
使い方: python3 -I tools/import_wp.py <XMLのパス>
- 非公開（private）、パスワード付き、下書きは取り込まない。XML自体はリポジトリに置かない。
- 旧テーマ専用の記号（[call_php] など）は「（準備中）」に置き換える。画像・iframe・script は取り込まない。"""
import sys, re, json, pathlib, html, xml.etree.ElementTree as ET
from html.parser import HTMLParser
ROOT = pathlib.Path(__file__).resolve().parent.parent
ns = {'wp': 'http://wordpress.org/export/1.2/', 'content': 'http://purl.org/rss/1.0/modules/content/'}
# 旧スラッグ → 新スラッグ（ホームは別途、手で作る）
SLUG = {'school': 'about', 'dental-hygienist': 'dental-hygienist', 'flow': 'flow', 'employment': 'career', 'admission': 'admission',
        'curriculum': 'curriculum', 'access': 'access', 'contact': 'contact', 'opencampus-contact': 'opencampus',
        'document-request': 'document-request', 'school-tour': 'school-tour', 'document': 'document', 'reunion_mail': 'alumni',
        'equipment': 'facilities', 'interview': 'interview', 'faq': 'faq', 'page-2465': 'dormitory', 'page-2482': 'results'}
# 旧サイトの画像 → 新サイトで使う画像（ユーザーから受領したもののみ）。ここにない画像は取り込まない。
IMGMAP = {  # 旧パス: (新パス, alt, 幅, 高さ, class)
    'images/dental-hygn/job_img01.jpg': ('assets/images/dental-hygienist/job-prevention.jpg', '歯科予防処置の実習の様子', 500, 417, 'photo'),
    'images/dental-hygn/job_img02.jpg': ('assets/images/dental-hygienist/job-assistant.jpg', '歯科診療補助の実習の様子', 500, 417, 'photo'),
    'images/dental-hygn/job_img03.jpg': ('assets/images/dental-hygienist/job-guidance.jpg', '歯科保健指導の実習の様子', 500, 417, 'photo'),
    'images/dental-hygn/job_img04.jpg': ('assets/images/dental-hygienist/job-oralcare.jpg', '口腔健康管理の実習の様子', 500, 417, 'photo'),
    # 「卒業までの流れ」。対応は、旧サイトの並び順（flow_02t〜05t）からの推定。要確認。
    'images/admission/flow_05t.jpg': ('assets/images/flow/year1.jpg', '1年次の授業の様子', 320, 214, 'photo small'),
    'images/admission/flow_02t.jpg': ('assets/images/flow/year2.jpg', '2年次の実習の様子', 320, 240, 'photo small'),
    'images/admission/flow_04t.jpg': ('assets/images/flow/year3.jpg', '3年次の授業の様子', 320, 243, 'photo small'),
    'images/admission/flow_03t.jpg': ('assets/images/flow/career.jpg', '学生のグループ活動の様子', 320, 240, 'photo small'),
    'images/dental-hyg_img02.png': ('assets/images/flow/school-life.webp', '学校行事（ボウリング大会・修学旅行・スポーツ大会）の様子', 1000, 500, 'photo'),
    # 「就職について」の卒業生インタビュー。対応は、内容（久留米）からの推定。要確認。img04・sub04（オーストラリア勤務）は、旧サイトでコメントアウトされ非表示のため、載せない。
    'images/realvoice/rl_vo_sub12.png': ('assets/images/career/voice2-workplace.png', '卒業生の勤務先の様子（久留米市内）', 360, 178, 'photo small'),
    'images/realvoice/rl_vo_img12.jpg': ('assets/images/career/voice2-portrait.jpg', '歯科衛生士の卒業生', 407, 423, 'photo small'),
    'images/access/access.png': ('assets/images/access/access.png', '最寄駅から学校までのアクセス図（詳細は下の文章をご覧ください）', 602, 282, 'photo'),
    'images/canpus_image1.png': ('assets/images/opencampus/opencampus.webp', 'オープンキャンパスの様子', 1002, 387, 'photo'),
    # 学校案内と歯科衛生士についての、両方で使う画像
    'images/dental-hyg_img01.png': ('assets/images/shared/dental-hygienist-collage.webp', '卒業生の戴帽式、学校行事、実習の様子を集めた写真', 1000, 500, 'photo'),
    'images/dental-hygn/whats_img01.jpg': ('assets/images/shared/students-suits.jpg', 'スーツ姿の本校の学生', 480, 400, 'photo med'),
    # 学校案内。「学校の特長」の写真は、旧サイトの本文の並び順（01〜04）と、受領した順が一致するものと推定。要確認。
    'images/school/dr_photo.jpg': ('assets/images/about/principal.jpg', '学校長 首藤 俊介', 400, 480, 'photo principal'),
    'images/school/school_point_img01.jpg': ('assets/images/about/point-01.jpg', '歯科用の器具（ミラーとピンセット）', 480, 380, 'photo med'),
    'images/school/school_point_img02.jpg': ('assets/images/about/point-02.jpg', '歯の記録を書き込む実習の様子', 480, 380, 'photo med'),
    'images/school/school_point_img03.jpg': ('assets/images/about/point-03.jpg', '教科書を見ながら学ぶ学生', 480, 380, 'photo med'),
    'images/school/school_point_img04.jpg': ('assets/images/about/point-04.jpg', '介護実習の様子', 480, 380, 'photo med'),
    'images/school/point_02.svg': ('assets/images/about/stat-offers.svg', '新卒有効求人倍率 20.5倍（平成28年 全衛協調査）', 400, 138, 'stat'),
    'images/school/point_01.svg': ('assets/images/about/stat-employment.svg', '卒業後の進路決定率 100%', 400, 138, 'stat'),
    # 女子指定寮のチラシ（外部広告）。旧サイトでは、本文でなくアイキャッチ・ギャラリー側にあった可能性があるため、APPEND で置く。
}
# ページ末尾に足す文章（旧サイトの iframe の地図は、外部読み込みになるため、リンクに替える）
APPEND = {'results': '''<section><p><img class="photo" src="{{R}}assets/images/results/2026-11.webp" alt="令和9年度入学生 学校推薦型選抜（高校推薦）・総合型選抜（3回） 入学試験結果。合格番号は、1201、2301、2303。" loading="lazy" width="2000" height="1125"></p>
<h3>令和9年度入学生 学校推薦型選抜（高校推薦）・総合型選抜（3回） 入学試験結果</h3>
<p>合格番号：1201、2301、2303</p></section>''', 'dormitory': '''<section><p><a href="{{R}}assets/images/dormitory/villa-mary-flyer.jpg"><img class="photo flyer" src="{{R}}assets/images/dormitory/villa-mary-flyer.jpg" alt="女子指定寮 Villa Mary（ヴィラマリア）のチラシ。内容は、下の文章をご覧ください。" loading="lazy" width="1414" height="2000"></a></p>
<p><small>画像をクリックすると、大きく表示されます。（2024年のチラシです。最新の内容は、管理会社へお問い合わせください。）</small></p></section>
<section><h3>チラシの内容（文字での案内）</h3>
<table class="info">
<tr><th>寮名</th><td>Villa Mary（ヴィラマリア）</td></tr>
<tr><th>所在地</th><td>福岡県久留米市日吉町29-5</td></tr>
<tr><th>交通</th><td>学校まで徒歩約12分／西鉄久留米駅まで徒歩5分／福岡（天神）まで電車で約30分</td></tr>
<tr><th>家賃（月額）</th><td>41,500円（夕食付・平日のみ）／34,000円（食事なし）</td></tr>
<tr><th>建物・設備</th><td>SRC（鉄骨鉄筋コンクリート）13階建、オートロック、防犯カメラ、24時間機械警備体制（ALSOK）、駐輪場あり、インターネット利用可、男性の出入り禁止、風呂・トイレ別</td></tr>
<tr><th>備え付けの家具・家電</th><td>冷蔵庫、洗濯機、電子レンジ、照明、テーブル、ベッド、エアコン</td></tr>
<tr><th>見学・お問い合わせ</th><td>西日本産業（株）　TEL 0942-39-3211　福岡県久留米市花畑3丁目3-3（定休日：毎週水曜日）。モデルルームの見学ができます。</td></tr>
</table>
<p>【この物件は、本校が所有している寮ではありません。管理会社へ委託している寮になります。】</p></section>''', 'access': '''<section><h3>最寄駅・空港からのアクセス（図の内容）</h3><ul>
<li>福岡空港 → 久留米インター：45分 → 学校：車で15分</li>
<li>JR鹿児島本線 博多駅 → JR久留米駅：特急で30分 → 学校：徒歩20分、車で5分</li>
<li>西鉄大牟田線 福岡（天神）駅 → 西鉄久留米駅：特急で30分 → 学校：徒歩20分、車で5分</li>
<li>西鉄大牟田線 大牟田駅 → 西鉄久留米駅：特急で30分</li>
<li>西鉄櫛原駅 → 学校：徒歩10分</li></ul>
<p><a class="btn" href="https://www.google.com/maps/search/?api=1&amp;query=%E7%A6%8F%E5%B2%A1%E7%9C%8C%E4%B9%85%E7%95%99%E7%B1%B3%E5%B8%82%E6%A0%9F%E5%8E%9F%E7%94%BA98" target="_blank" rel="noopener noreferrer">Googleマップで見る</a></p></section>'''}
NEWS_APPEND = {'3022': '''<p><a href="{{R}}assets/images/news/parking-map-2026.webp"><img class="photo" src="{{R}}assets/images/news/parking-map-2026.webp" alt="本校駐車場の案内図。駐車場は①②の2か所。詳しくは下の文章をご覧ください。" loading="lazy" width="2000" height="1414"></a></p>
<ul><li>お車でお越しの際には、駐車場がありますので、お気をつけてご来校ください。</li>
<li>道幅が狭いので、ご注意ください。</li>
<li>7:00〜9:00、16:00〜18:00 の時間帯は、図の赤い矢印の向きのみの一方通行です。</li></ul>'''}
TITLES = {'page-2465': '女子指定寮のご案内'}  # 旧サイトの管理用の名前（外部広告（女子寮））を、公開向けの見出しに替える
KEEP = {'p','h2','h3','h4','h5','ul','ol','li','table','thead','tbody','tr','th','td','a','strong','b','em','br','dl','dt','dd','blockquote'}
DROP = {'script','style','iframe','img','form','input','button','select','textarea','svg','noscript','video','audio'}
PENDING = '<p class="pending">（準備中）この部分は、新サイトで作り直します。</p>'

class Clean(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=True); self.out = []; self.skip = 0; self.stack = []
    def handle_starttag(self, t, a):
        if t == 'img':
            m = IMGMAP.get(dict(a).get('src') or '')
            if m and not self.skip: self.out.append('<img class="%s" src="{{R}}%s" alt="%s" loading="lazy" width="%d" height="%d">' % (m[4], m[0], m[1], m[2], m[3]))
            return
        if t in DROP: self.skip += 1 if t not in ('img','input') else 0; return
        if self.skip: return
        if t == 'h1': t = 'h2'
        if t in KEEP:
            at = ''
            if t == 'a':
                h = dict(a).get('href') or ''
                if h.startswith(('http://', 'https://', 'mailto:', 'tel:')) or h.startswith('[hurl]'):
                    at = ' href="%s"' % html.escape(fixlink(h)) + (' target="_blank" rel="noopener noreferrer"' if h.startswith('http') and 'kurume-dental.or.jp' not in h else '')
            self.out.append('<%s%s>' % (t, at)); self.stack.append(t) if t not in ('br',) else None
    def handle_endtag(self, t):
        if t in DROP: self.skip = max(0, self.skip - 1) if t not in ('img','input') else self.skip; return
        if self.skip: return
        if t == 'h1': t = 'h2'
        if t in KEEP and t != 'br': self.out.append('</%s>' % t)
    def handle_startendtag(self, t, a):
        if t == 'br' and not self.skip: self.out.append('<br>')
    def handle_data(self, d):
        if not self.skip: self.out.append(re.sub(r'\n\s*\n', '<br><br>', html.escape(d)))

LOCAL_FILES = {'2025main.pdf': 'assets/pdf/hogosha-2025-main.pdf', '2025submain.pdf': 'assets/pdf/hogosha-2025-submain.pdf', '1P-2P2025.pdf': 'assets/pdf/hogosha-2025-1p-2p.pdf', '3P-4P2025.pdf': 'assets/pdf/hogosha-2025-3p-4p.pdf', '5P-6P2025.pdf': 'assets/pdf/hogosha-2025-5p-6p.pdf', '7P-8P2025.pdf': 'assets/pdf/hogosha-2025-7p-8p.pdf', '9P-10P2025.pdf': 'assets/pdf/hogosha-2025-9p-10p.pdf', 'admission2026001.pdf': 'assets/pdf/admission-2026-essay-topics.pdf', 'ParkingMap2026ver2.png': 'assets/images/news/parking-map-2026.webp'}

def fixlink(h):
    h = h.replace('[hurl]', '')
    for k, v in LOCAL_FILES.items():
        if h.endswith('/' + k): return '{{R}}' + v
    m = re.match(r'https?://(?:www\.)?kurume-dental\.or\.jp/kdhs/?(.*)$', h)
    if m or not h.startswith(('http', 'mailto', 'tel')):
        path = (m.group(1) if m else h).strip('/').split('/')[-1]
        return '{{R}}' + SLUG.get(path, path) + '/' if path in SLUG else ('{{R}}' if not path else h)
    return h

# NextGEN Gallery（[ngg ... ids="N"]）→ 受領した写真のギャラリー。ids と受領したフォルダの対応（旧サイトの本文の並び順と、ZIPの名前の番号が一致）
NGG = {'1': ('shinsatsu', '診察室'), '3': ('hall', '多目的大ホール'), '4': ('library', '2F図書室'), '5': ('kiso', '4F基礎実習室'), '6': ('shinkan', '新館教室')}

def gallery_html(gid):
    from PIL import Image
    d, name = NGG[gid]; base = ROOT / 'assets/images/facilities' / d
    items = []
    for f in sorted(base.glob('[0-9][0-9].jpg')):
        w, h = Image.open(f).size; t = Image.open(base / ('thumb-' + f.name)).size
        items.append('<a href="{{R}}assets/images/facilities/%s/%s"><img src="{{R}}assets/images/facilities/%s/thumb-%s" alt="%sの様子（%s）" loading="lazy" width="%d" height="%d"></a>'
                     % (d, f.name, d, f.name, name, f.stem.lstrip('0'), t[0], t[1]))
    return '<div class="gallery">%s</div>' % ''.join(items)

def clean(src):
    galleries = {}
    def _g(m):
        k = '@@GALLERY%s@@' % m.group(1)
        if m.group(1) in NGG: galleries[k] = gallery_html(m.group(1)); return k
        return m.group(0)
    src = re.sub(r'\[ngg[^\]]*?ids="(\d+)"[^\]]*\]', _g, src)
    src = re.sub(r"\[call_php[^\]]*\]", '@@PENDING@@', src)
    src = re.sub(r"\[(?:ngg|contact-form-7|gallery|[a-z_]+)[^\]]*\]", '@@PENDING@@', src)
    c = Clean(); c.feed(src); out = ''.join(c.out).replace('@@PENDING@@', PENDING)
    for k, v in galleries.items(): out = out.replace(k, v)
    out = re.sub(r'<(\w+)>\s*</\1>', '', out)                      # 空タグ
    out = re.sub(r'<p>\s*(<p class="pending">.*?</p>)\s*</p>', r'\1', out, flags=re.S)
    if '<li>' not in out: out = re.sub(r'</?(ul|ol)>', '', out)
    out = re.sub(r'(?:<br>\s*){3,}', '<br><br>', out)
    out = re.sub(r'<p>\s*(<br>\s*)*</p>', '', out)
    out = re.sub(r'<(ul|ol)>((?:(?!<li>).)*?)</\1>', r'<p>\2</p>', out, flags=re.S)  # li のない ul
    # 文字のみ（ブロックタグなし）の塊を段落に
    if not re.search(r'<(p|h\d|ul|ol|table|dl)\b', out): out = '<p>%s</p>' % out
    return out.strip()

def main(path):
    ch = ET.parse(path).getroot().find('channel'); g = lambda i, k: i.findtext(k, namespaces=ns)
    pages, news = [], []
    for i in ch.findall('item'):
        t, st, pw = g(i, 'wp:post_type'), g(i, 'wp:status'), g(i, 'wp:post_password')
        if st != 'publish' or pw: continue
        title, body = (i.findtext('title') or '').strip(), g(i, 'content:encoded') or ''
        title = TITLES.get(g(i, 'wp:post_name'), title)
        if t == 'page' and g(i, 'wp:post_name') in SLUG:
            pages.append({'slug': SLUG[g(i, 'wp:post_name')], 'title': title, 'lead': '', 'body': '<section>%s</section>' % clean(body) + APPEND.get(SLUG[g(i, 'wp:post_name')], ''), 'old_slug': g(i, 'wp:post_name')})
        elif t == 'post':
            news.append({'date': g(i, 'wp:post_date')[:10], 'title': title, 'body': clean(body) + NEWS_APPEND.get(g(i, 'wp:post_id'), ''), 'id': g(i, 'wp:post_id')})
    order = list(SLUG.values()); pages.sort(key=lambda p: order.index(p['slug'])); news.sort(key=lambda n: n['date'], reverse=True)
    (ROOT/'data/imported_pages.json').write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding='utf-8')
    (ROOT/'data/news.json').write_text(json.dumps(news, ensure_ascii=False, indent=1), encoding='utf-8')
    print('ページ %d 件、お知らせ %d 件' % (len(pages), len(news)))
main(sys.argv[1])
