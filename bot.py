import os
import requests
import random
import json
import feedparser
import re
import logging
from datetime import date
from urllib.parse import urlparse, urlunparse
from pathlib import Path
from PIL import Image
import io
import time

# =========================
# إعداد التسجيل (logging)
# =========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================
# Environment Variables
# =========================
FB_PAGE_ID           = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY         = os.getenv("NEWS_API_KEY")          # ✅ جديد
UNSPLASH_ACCESS_KEY  = os.getenv("UNSPLASH_ACCESS_KEY")   # ✅ مصلح
PEXELS_API_KEY       = os.getenv("PEXELS_API_KEY")        # ✅ احتياطي
MODEL_NAME           = "gemini-2.5-flash"

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise EnvironmentError(
        "❌ متغيرات البيئة المطلوبة غير موجودة: "
        "FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY"
    )

# =========================
# الثوابت والمسارات
# =========================
TEMP_IMAGE       = Path("temp_image.jpg")
POSTED_FILE      = Path("posted_news.json")
SOURCES_STATE    = Path("sources_state.json")
USED_IMAGES_FILE = Path("used_images.json")

MAX_IMAGE_WIDTH = 1200
MAX_POST_LENGTH = 1800

# =========================
# Session مشتركة لجميع الطلبات
# =========================
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    )
})

# =========================
# أدوات مساعدة: تحميل / حفظ JSON
# =========================
def _load_json(path: Path, default):
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"خطأ في تحميل {path.name}: {e}")
    return default

def _save_json(path: Path, data):
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ {path.name}: {e}")

# =========================
# تطبيع الروابط
# =========================
def normalize_link(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', '')).rstrip('/')

# =========================
# إدارة الأخبار المنشورة
# =========================
def load_posted_news() -> set:
    data = _load_json(POSTED_FILE, {})
    if isinstance(data, list):
        return {normalize_link(link) for link in data if isinstance(link, str)}
    elif isinstance(data, dict):
        return {normalize_link(k) for k in data}
    return set()

def save_posted_news(posted: set):
    _save_json(POSTED_FILE, list(posted))

# =========================
# إدارة حالة المصادر
# =========================
def load_sources_state() -> dict:
    return _load_json(SOURCES_STATE, {})

def save_sources_state(state: dict):
    _save_json(SOURCES_STATE, state)

def get_available_sources(sources: list, state: dict) -> list:
    today = date.today().isoformat()
    return [src for src in sources if state.get(src["name"]) != today]

def mark_source_used(source_name: str, state: dict):
    state[source_name] = date.today().isoformat()
    save_sources_state(state)

# =========================
# إدارة الصور المستخدمة
# =========================
def load_used_images() -> set:
    return set(_load_json(USED_IMAGES_FILE, []))

def save_used_images(used: set):
    _save_json(USED_IMAGES_FILE, list(used))

# =========================
# مصادر الأخبار RSS (احتياطي)
# =========================
NEWS_SOURCES = [
    # المصادر الأجنبية
    {"name": "The Verge",         "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "TechCrunch",        "url": "https://techcrunch.com/feed/"},
    {"name": "Wired",             "url": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica",      "url": "https://arstechnica.com/feed/"},
    {"name": "Engadget",          "url": "https://www.engadget.com/rss.xml"},
    {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/"},
    {"name": "CNET",              "url": "https://www.cnet.com/rss/news/"},
    {"name": "Tom's Hardware",    "url": "https://www.tomshardware.com/feeds/all"},
    {"name": "Android Police",    "url": "https://www.androidpolice.com/feed/"},
    {"name": "9to5Mac",           "url": "https://9to5mac.com/feed/"},
    {"name": "GSMArena",          "url": "https://www.gsmarena.com/rss-news-reviews.php3"},
    {"name": "XDA Developers",    "url": "https://www.xda-developers.com/feed/"},
    {"name": "The Next Web",      "url": "https://thenextweb.com/feed/"},
    {"name": "Mashable",          "url": "https://mashable.com/feed/"},
    {"name": "VentureBeat",       "url": "https://venturebeat.com/feed/"},
    {"name": "MacRumors",         "url": "https://www.macrumors.com/macrumors.xml"},
    {"name": "Digital Trends",    "url": "https://www.digitaltrends.com/feed/"},
    # المصادر العربية
    {"name": "عرب هاردوير",                  "url": "https://www.arabhardware.net/feed"},
    {"name": "البوابة التقنية AIT",          "url": "https://aitnews.com/feed/"},
    {"name": "تيك 24",                       "url": "https://tech24.ma/feed/"},
    {"name": "عالم التقنية",                 "url": "https://www.tech-wd.com/wd/feed"},
    {"name": "سكاي نيوز عربية - تكنولوجيا", "url": "https://www.skynewsarabia.com/technology/rss"},
    {"name": "الجزيرة نت - تكنولوجيا",      "url": "https://www.aljazeera.net/aljazeerarss/ae187c16-07be-4806-9602-4836b3fdbf06/62763653-6fe3-4c20-afd9-a12880b0a76c"},
    {"name": "بي بي سي عربي - تكنولوجيا",  "url": "https://www.bbc.com/arabic/technology/feed.xml"},
    {"name": "DW عربية - تكنولوجيا",        "url": "https://rss.dw.com/ar/rss-tech"},
]

# =========================
# مكتبة الصور الاحتياطية
# =========================
IMAGE_LIBRARY = {
    "gaming": [
        "https://images.pexels.com/photos/442580/pexels-photo-442580.jpeg",
        "https://images.pexels.com/photos/163064/play-station-ps4-controller-game-163064.jpeg",
        "https://images.pexels.com/photos/1591060/pexels-photo-1591060.jpeg",
        "https://images.pexels.com/photos/210745/pexels-photo-210745.jpeg",
        "https://images.pexels.com/photos/3165335/pexels-photo-3165335.jpeg",
    ],
    "AI": [
        "https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg",
        "https://images.pexels.com/photos/3861972/pexels-photo-3861972.jpeg",
        "https://images.pexels.com/photos/8386440/pexels-photo-8386440.jpeg",
        "https://images.pexels.com/photos/5380797/pexels-photo-5380797.jpeg",
        "https://images.pexels.com/photos/8386438/pexels-photo-8386438.jpeg",
    ],
    "tech": [
        "https://images.pexels.com/photos/574071/pexels-photo-574071.jpeg",
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg",
        "https://images.pexels.com/photos/325185/pexels-photo-325185.jpeg",
        "https://images.pexels.com/photos/3861971/pexels-photo-3861971.jpeg",
    ],
    "science": [
        "https://images.pexels.com/photos/247431/pexels-photo-247431.jpeg",
        "https://images.pexels.com/photos/326709/pexels-photo-326709.jpeg",
        "https://images.pexels.com/photos/2894944/pexels-photo-2894944.jpeg",
    ],
    "default": [
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg",
        "https://images.pexels.com/photos/574071/pexels-photo-574071.jpeg",
        "https://images.pexels.com/photos/325185/pexels-photo-325185.jpeg",
        "https://images.pexels.com/photos/270637/pexels-photo-270637.jpeg",
    ]
}

# =========================
# تحديد موضوع الخبر
# =========================
def get_topic(title: str) -> str:
    lower = title.lower()
    if any(k in lower for k in ["game", "playstation", "nintendo", "xbox", "sony", "gaming", "esports"]):
        return "gaming"
    if any(k in lower for k in ["ai", "artificial", "gemini", "chatgpt", "openai", "gpt", "llm", "neural"]):
        return "AI"
    if any(k in lower for k in ["science", "research", "scientist", "discovery", "space", "nasa"]):
        return "science"
    if any(k in lower for k in ["iphone", "samsung", "apple", "macbook", "android", "pixel", "smartphone"]):
        return "tech"
    return "default"

# =========================
# 1️⃣ جلب الأخبار عبر NEWS API (المصدر الرئيسي)
# =========================
def get_news_from_api(posted_links: set) -> tuple[list, str | None]:
    """
    يجلب أفضل الأخبار التقنية عبر NewsAPI.
    - مرتبة حسب الشعبية (popularity)
    - مصادر تقنية موثوقة فقط
    - يتجنب الأخبار المنشورة مسبقاً
    """
    if not NEWS_API_KEY:
        logger.warning("⚠️ NEWS_API_KEY غير موجود، سيتم تخطي NewsAPI")
        return [], None

    logger.info("📡 جلب الأخبار من NewsAPI...")

    try:
        res = SESSION.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "category": "technology",
                "language": "en",
                "pageSize": 20,          # نجلب 20 خبر ونختار الأفضل
                "sortBy":   "popularity",
                "apiKey":   NEWS_API_KEY,
            },
            timeout=15,
        )

        if res.status_code == 401:
            logger.error("❌ NEWS_API_KEY غير صالح!")
            return [], None

        if res.status_code == 426:
            logger.warning("⚠️ NewsAPI: الخطة المجانية لا تدعم هذا الطلب، جاري التبديل...")
            # الخطة المجانية تدعم /everything بدل /top-headlines
            res = SESSION.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        "technology OR AI OR smartphone",
                    "language": "en",
                    "pageSize": 20,
                    "sortBy":   "publishedAt",  # الأحدث أولاً
                    "apiKey":   NEWS_API_KEY,
                },
                timeout=15,
            )

        res.raise_for_status()
        articles = res.json().get("articles", [])

        if not articles:
            logger.warning("⚠️ NewsAPI: لا توجد نتائج")
            return [], None

        # فلتر الأخبار المنشورة مسبقاً والأخبار بدون محتوى
        new_articles = []
        for article in articles:
            if not article.get("url") or not article.get("title"):
                continue
            if article["title"] == "[Removed]":
                continue
            norm = normalize_link(article["url"])
            if norm in posted_links:
                continue
            new_articles.append({
                "title":     article["title"],
                "link":      article["url"],
                "norm_link": norm,
                "image":     article.get("urlToImage", ""),
                "source":    f"NewsAPI - {article['source']['name']}",
            })

        if not new_articles:
            logger.info("⚠️ NewsAPI: كل الأخبار منشورة مسبقاً")
            return [], None

        # اختر الأفضل عشوائياً من أول 5
        chosen = random.choice(new_articles[:5])
        logger.info(f"✅ NewsAPI: تم اختيار '{chosen['title'][:60]}...'")
        return [chosen], "NewsAPI"

    except requests.exceptions.Timeout:
        logger.error("❌ NewsAPI Timeout")
    except Exception as e:
        logger.error(f"❌ NewsAPI Error: {e}")

    return [], None


# =========================
# 2️⃣ جلب الأخبار عبر RSS (الاحتياطي)
# =========================
def get_news_from_rss(posted_links: set) -> tuple[list, str | None]:
    """
    يجلب الأخبار من مصادر RSS عند فشل NewsAPI.
    نفس المنطق القديم لكن منظم بشكل أوضح.
    """
    state     = load_sources_state()
    available = get_available_sources(NEWS_SOURCES, state)

    if not available:
        logger.warning("⚠️ جميع مصادر RSS استُخدمت اليوم.")
        return [], None

    random.shuffle(available)

    for source in available:
        logger.info(f"🔍 RSS: البحث في {source['name']}")
        try:
            resp = SESSION.get(source["url"], timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.error(f"❌ فشل جلب RSS من {source['name']}: {e}")
            continue

        if feed.bozo and not feed.entries:
            continue

        for entry in feed.entries:
            if not getattr(entry, 'link', None):
                continue

            norm_link = normalize_link(entry.link)
            if norm_link in posted_links:
                continue

            content     = (entry.get('content', [{}])[0].get('value', '') or entry.get('summary', ''))
            image_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
            image       = image_match.group(1) if image_match else ""

            logger.info(f"✅ RSS: تم العثور على خبر جديد من {source['name']}")
            return [{
                "title":     entry.title,
                "link":      entry.link,
                "norm_link": norm_link,
                "image":     image,
                "source":    source["name"],
            }], source["name"]

    logger.info("❌ RSS: لم يُعثر على أي خبر جديد.")
    return [], None


# =========================
# الدالة الرئيسية لجلب الأخبار
# =========================
def get_news(posted_links: set) -> tuple[list, str | None]:
    """
    يجرب NewsAPI أولاً، ثم RSS كاحتياطي.
    """
    # المصدر الرئيسي: NewsAPI
    articles, source = get_news_from_api(posted_links)
    if articles:
        return articles, source

    # الاحتياطي: RSS
    logger.info("🔄 التبديل إلى مصادر RSS...")
    return get_news_from_rss(posted_links)


# =========================
# تحميل الصورة + تغيير حجمها
# =========================
def download_and_resize_image(url: str) -> bool:
    try:
        res = SESSION.get(url, timeout=30)
        if res.status_code != 200 or "image" not in res.headers.get("Content-Type", ""):
            return False

        img = Image.open(io.BytesIO(res.content))

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if img.width > MAX_IMAGE_WIDTH:
            ratio      = MAX_IMAGE_WIDTH / img.width
            new_height = int(img.height * ratio)
            img        = img.resize((MAX_IMAGE_WIDTH, new_height), Image.LANCZOS)
            logger.info(f"🖼️ تم تغيير حجم الصورة إلى {img.width}x{img.height}")

        img.save(TEMP_IMAGE, "JPEG", quality=85, optimize=True)
        return True

    except Exception as e:
        logger.error(f"خطأ في تحميل الصورة: {e}")
        return False

def validate_image() -> bool:
    try:
        with TEMP_IMAGE.open("rb") as f:
            header = f.read(4)
        return header[:3] == b"\xff\xd8\xff" or header[:4] == b"\x89PNG"
    except Exception:
        return False


# =========================
# 1️⃣ صور: Unsplash API الرسمي ✅ (مصلح)
# =========================
def get_unsplash_image(title: str, used_images: set) -> str | None:
    """
    يستخدم Unsplash API الرسمي بـ Access Key.
    المشكلة القديمة: كان يستخدم source.unsplash.com المتوقف.
    الحل: API الرسمي api.unsplash.com مع UNSPLASH_ACCESS_KEY.
    """
    if not UNSPLASH_ACCESS_KEY:
        logger.warning("⚠️ UNSPLASH_ACCESS_KEY غير موجود")
        return None

    clean_title   = re.sub(r'[^\w\s]', '', title).strip()
    search_queries = [
        " ".join(clean_title.split()[:5]),  # أول 5 كلمات
        get_topic(title),                   # موضوع الخبر
    ]

    for query in search_queries:
        if not query.strip():
            continue
        try:
            logger.info(f"🔍 Unsplash: البحث عن '{query}'")
            res = SESSION.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                params={
                    "query":       query,
                    "per_page":    15,
                    "orientation": "landscape",
                    "content_filter": "high",   # صور آمنة فقط
                },
                timeout=15,
            )

            if res.status_code == 401:
                logger.error("❌ UNSPLASH_ACCESS_KEY غير صالح!")
                return None

            if res.status_code == 403:
                logger.warning("⚠️ Unsplash: تجاوزت الحد الشهري (50 طلب/ساعة)")
                return None

            res.raise_for_status()
            results = res.json().get("results", [])

            if not results:
                logger.info(f"⚠️ Unsplash: لا نتائج لـ '{query}'")
                continue

            # فلتر الصور غير المستخدمة
            new_photos = [
                p for p in results
                if p["urls"]["regular"] not in used_images
            ]

            chosen    = random.choice(new_photos if new_photos else results)
            image_url = chosen["urls"]["regular"]  # جودة جيدة ~1080px

            logger.info(f"✅ Unsplash: تم العثور على صورة (ID: {chosen['id']})")
            return image_url

        except requests.exceptions.Timeout:
            logger.error(f"❌ Unsplash Timeout للبحث: '{query}'")
        except Exception as e:
            logger.error(f"❌ Unsplash Error: {e}")

    logger.warning("⚠️ Unsplash: فشلت جميع المحاولات")
    return None


# =========================
# 2️⃣ صور: Pexels API ✅ (احتياطي)
# =========================
def get_pexels_image(title: str, used_images: set) -> str | None:
    """
    يستخدم Pexels كخيار احتياطي ثانٍ بعد Unsplash.
    """
    if not PEXELS_API_KEY:
        logger.warning("⚠️ PEXELS_API_KEY غير موجود")
        return None

    clean_title    = re.sub(r'[^\w\s]', '', title).strip()
    search_queries = [
        " ".join(clean_title.split()[:4]),
        get_topic(title),
    ]

    for query in search_queries:
        if not query.strip():
            continue
        try:
            logger.info(f"🔍 Pexels: البحث عن '{query}'")
            res = SESSION.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={
                    "query":       query,
                    "per_page":    15,
                    "orientation": "landscape",
                    "size":        "large",
                },
                timeout=15,
            )

            if res.status_code == 401:
                logger.error("❌ PEXELS_API_KEY غير صالح!")
                return None

            if res.status_code == 429:
                logger.warning("⚠️ Pexels: تجاوزت الحد اليومي")
                return None

            res.raise_for_status()
            photos = res.json().get("photos", [])

            if not photos:
                continue

            new_photos = [p for p in photos if p["src"]["large2x"] not in used_images]
            chosen     = random.choice(new_photos if new_photos else photos)
            image_url  = chosen["src"]["large2x"]

            logger.info(f"✅ Pexels: تم العثور على صورة (ID: {chosen['id']})")
            return image_url

        except Exception as e:
            logger.error(f"❌ Pexels Error: {e}")

    logger.warning("⚠️ Pexels: فشلت جميع المحاولات")
    return None


# =========================
# توليد المنشور عبر Gemini
# =========================
def generate_post(title: str) -> str | None:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    )

    prompt = f"""
أنت "سمير" — كاتب محتوى تقني مغربي شاب، عندك 28 عام، تسكن فكاسابلانكا، متحمس للتكنولوجيا وكتشارك متابعيك أحدث الأخبار التقنية بأسلوب حيوي وعفوي.

الخبر: "{title}"

━━━━━━━━━━━━━━━━━━━━━━
🎯 مهمتك: اكتب منشور فيسبوك واحد بالدارجة المغربية
━━━━━━━━━━━━━━━━━━━━━━

## اللغة والشخصية:
- دارجة مغربية طبيعية 100% — مش مترجمة من الفصحى
- تحكي بحال صاحب كيحكي لصاحبو: بدون تكلف ولا رسمية زائدة
- المصطلحات التقنية تبقى بالإنجليزية (AI، update، launch، specs) مدمجة بشكل طبيعي
- تعابير مغربية أصيلة مثل: "هاد الشي خايب/زوين"، "كنقلب عليها"، "راه واضح"، "أش كتگول"، "بصح..."، "واخا..."
- تجنب: الفصحى المتصنعة، الترجمة الحرفية، الأسلوب الإذاعي

## الهيكل الإلزامي (اتبع هاد الترتيب بالضبط):

**[HOOK]** — سطر واحد فقط، يخلي الواحد يوقف التمرير:
→ إما سؤال مثير: "واش خبرتي بلي..."
→ إما إعلان مفاجئ: "راه وقع! [الشيء الكبير]..."
→ إما رأي جريء: "هاد الـ [شيء] غيبدل كلشي..."

**[CONTEXT]** — جملتين أو 3 تشرح الخبر ببساطة، بدون تعقيد

**[DETAILS]** — نقطتين أو 3 بهاد الشكل:
⚡ [عنوان قصير]: شرح مختصر 20-30 كلمة
⚡ [عنوان قصير]: شرح مختصر 20-30 كلمة
⚡ [عنوان قصير]: شرح مختصر 20-30 كلمة (اختياري)

**[IMPACT]** — جملة أو جملتين: شنو معناه هاد الخبر للمغاربة تحديداً

**[OPINION]** — رأيك الشخصي كـ"سمير": صريح، مباشر، مش محايد
مثال: "أنا شخصياً كنشوف بلي..." أو "بصح الصراحة..."

**[CTA]** — سؤال تفاعلي واحد قوي يحفز التعليق:
→ مش سؤال عام، سؤال متعلق بالخبر مباشرة
→ مثال: "أنتم واش غتشريو [المنتج] ولا كتستنيو [البديل]؟"

**[HASHTAGS]** — سطر منفصل: 5 هاشتاجات (مزيج عربي وإنجليزي)
→ مثال: #تقنية_بالدارجة #المغرب_التقني #TechNews #AI #تكنولوجيا

## قواعد الإيموجي:
- 5 إلى 7 إيموجيات موزعة بذكاء على المنشور
- مش كلها في آخر السطر — وزعها في البداية والوسط والنهاية
- استعمل إيموجيات تعبر عن المحتوى مش ديكور فقط

## الطول والجودة:
- بين 1200 و 1800 حرف — مش أقل ومش أكثر
- كل جملة لازم تضيف قيمة — حذف أي حشو أو تكرار
- القراءة تاخد مش أكثر من 45 ثانية

## ❌ ممنوع تماماً:
- مقدمات من بحال "بسم الله" أو "السلام عليكم أصدقاء"
- عبارات تسويقية فارغة: "ثورة حقيقية"، "تغيير جذري"، "لا مثيل له"
- تكرار عنوان الخبر كما هو
- أي markdown أو نجوم (**) في النص النهائي

اكتب المنشور مباشرة الآن — ابدأ بالـ HOOK مباشرة بدون أي مقدمة:
"""

    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    delay   = 30

    for attempt in range(1, 4):
        try:
            logger.info(f"📡 محاولة توليد المنشور {attempt}/3...")
            res = SESSION.post(url, json=payload, headers=headers, timeout=60)

            if res.status_code == 429:
                logger.warning(f"⚠️ Gemini 429 - انتظار {delay}ث...")
                time.sleep(delay)
                delay *= 2
                continue

            res.raise_for_status()
            post_text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # تنظيف Markdown
            post_text = re.sub(r'^\s*\*\s+',    '🔹 ', post_text, flags=re.MULTILINE)
            post_text = re.sub(r'\n\s*\*\s+',   '\n🔹 ', post_text)
            post_text = re.sub(r'\*\*(.*?)\*\*', r'\1', post_text)
            post_text = re.sub(r'\*(.*?)\*',     r'\1', post_text)

            if len(post_text) > MAX_POST_LENGTH:
                logger.warning(f"⚠️ النص طويل ({len(post_text)} حرف)، سيتم تقليمه.")
                post_text = post_text[:MAX_POST_LENGTH].rsplit(' ', 1)[0] + "..."

            logger.info("✅ تم توليد المنشور بنجاح")
            return post_text

        except requests.exceptions.Timeout:
            logger.error(f"❌ Gemini Timeout (محاولة {attempt})")
        except Exception as e:
            logger.error(f"❌ Gemini Error (محاولة {attempt}): {e}")

        if attempt < 3:
            logger.warning(f"⚠️ إعادة المحاولة بعد {delay}ث...")
            time.sleep(delay)
            delay *= 2

    logger.error("❌ فشلت جميع المحاولات مع Gemini.")
    return None


# =========================
# النشر على فيسبوك
# =========================
def post_to_facebook(message: str) -> dict | None:
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    try:
        with TEMP_IMAGE.open("rb") as img_file:
            res = SESSION.post(
                fb_url,
                data  = {"caption": message, "access_token": FB_PAGE_ACCESS_TOKEN},
                files = {"source": ("post.jpg", img_file, "image/jpeg")},
                timeout=30,
            )
        return res.json()
    except Exception as e:
        logger.error(f"❌ Facebook API Error: {e}")
        return None


# =========================
# الدالة الرئيسية
# =========================
def main():
    logger.info("=" * 50)
    logger.info("🚀 بدء دورة النشر")
    logger.info("=" * 50)

    posted_news = load_posted_news()

    # ── جلب الأخبار (NewsAPI → RSS) ──────────────────
    articles, source_name = get_news(posted_news)

    if not articles:
        logger.info("❌ لا توجد أخبار جديدة للنشر.")
        return

    article = articles[0]
    logger.info(f"📝 الخبر المختار: {article['title'][:70]}...")
    logger.info(f"📰 المصدر: {article['source']}")

    # ── جلب الصورة (4 مستويات) ───────────────────────
    used_images = load_used_images()
    image_ok    = False

    # 1️⃣ صورة الخبر الأصلية
    if article.get("image"):
        logger.info("🖼️  [1/4] تجربة صورة الخبر الأصلية...")
        image_ok = download_and_resize_image(article["image"]) and validate_image()
        if image_ok:
            logger.info("✅ تم استخدام صورة الخبر الأصلية")

    # 2️⃣ Unsplash API الرسمي
    if not image_ok:
        logger.info("🔍 [2/4] البحث عبر Unsplash API...")
        url = get_unsplash_image(article["title"], used_images)
        if url:
            image_ok = download_and_resize_image(url) and validate_image()
            if image_ok:
                logger.info("✅ تم استخدام صورة من Unsplash")
                used_images.add(url)
                save_used_images(used_images)

    # 3️⃣ Pexels API
    if not image_ok:
        logger.info("🔍 [3/4] البحث عبر Pexels API...")
        url = get_pexels_image(article["title"], used_images)
        if url:
            image_ok = download_and_resize_image(url) and validate_image()
            if image_ok:
                logger.info("✅ تم استخدام صورة من Pexels")
                used_images.add(url)
                save_used_images(used_images)

    # 4️⃣ المكتبة الاحتياطية
    if not image_ok:
        topic  = get_topic(article["title"])
        backup = random.choice(IMAGE_LIBRARY.get(topic, IMAGE_LIBRARY["default"]))
        logger.info(f"🖼️  [4/4] استخدام صورة احتياطية (موضوع: {topic})")
        image_ok = download_and_resize_image(backup) and validate_image()
        if not image_ok:
            logger.error("❌ فشل تحميل أي صورة. إيقاف.")
            return

    # ── توليد المنشور ────────────────────────────────
    post_text = generate_post(article["title"])
    if not post_text:
        logger.error("❌ فشل توليد المنشور.")
        return

    # ── النشر على فيسبوك ─────────────────────────────
    logger.info("🚀 جاري النشر على فيسبوك...")
    result = post_to_facebook(post_text)

    if result and "id" in result:
        logger.info(f"✅ تم النشر بنجاح! المعرف: {result['id']}")

        # حفظ الخبر كمنشور
        posted_news.add(article["norm_link"])
        save_posted_news(posted_news)

        # تحديث حالة المصدر (للـ RSS فقط)
        if source_name and source_name != "NewsAPI":
            state = load_sources_state()
            mark_source_used(source_name, state)
            logger.info(f"📅 تم تحديث حالة المصدر: {source_name}")
    else:
        logger.error(f"❌ فشل النشر على فيسبوك: {result}")

    # ── تنظيف الملفات المؤقتة ────────────────────────
    try:
        TEMP_IMAGE.unlink(missing_ok=True)
        logger.info("🧹 تم حذف الصورة المؤقتة")
    except Exception:
        pass

    logger.info("=" * 50)
    logger.info("🏁 انتهت دورة النشر")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()

