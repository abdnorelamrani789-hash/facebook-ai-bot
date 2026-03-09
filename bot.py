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
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise EnvironmentError("❌ متغيرات البيئة المطلوبة غير موجودة: FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY")

# =========================
# الثوابت والمسارات
# =========================
TEMP_IMAGE       = Path("temp_image.jpg")
POSTED_FILE      = Path("posted_news.json")
SOURCES_STATE    = Path("sources_state.json")
USED_IMAGES_FILE = Path("used_images.json")

MAX_IMAGE_WIDTH = 1200
MAX_POST_LENGTH = 2000  # حد أمان للمنشور (الحد الحقيقي لفيسبوك هو 63206 حرف)

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
# مصادر الأخبار (28 مصدراً بدون تكرار)
# =========================
NEWS_SOURCES = [
    # المصادر الأجنبية
    {"name": "The Verge",        "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "TechCrunch",       "url": "https://techcrunch.com/feed/"},
    {"name": "Wired",            "url": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica",     "url": "https://arstechnica.com/feed/"},
    {"name": "Engadget",         "url": "https://www.engadget.com/rss.xml"},
    {"name": "Android Authority","url": "https://www.androidauthority.com/feed/"},
    {"name": "CNET",             "url": "https://www.cnet.com/rss/news/"},
    {"name": "Tom's Hardware",   "url": "https://www.tomshardware.com/feeds/all"},
    {"name": "Android Police",   "url": "https://www.androidpolice.com/feed/"},
    {"name": "9to5Mac",          "url": "https://9to5mac.com/feed/"},
    {"name": "GSMArena",         "url": "https://www.gsmarena.com/rss-news-reviews.php3"},
    {"name": "XDA Developers",   "url": "https://www.xda-developers.com/feed/"},
    {"name": "The Next Web",     "url": "https://thenextweb.com/feed/"},
    {"name": "Mashable",         "url": "https://mashable.com/feed/"},
    {"name": "VentureBeat",      "url": "https://venturebeat.com/feed/"},
    {"name": "PC Gamer",         "url": "https://www.pcgamer.com/feed/"},
    {"name": "MacRumors",        "url": "https://www.macrumors.com/macrumors.xml"},
    {"name": "Slashdot",         "url": "https://rss.slashdot.org/Slashdot/slashdotMain"},
    {"name": "Digital Trends",   "url": "https://www.digitaltrends.com/feed/"},
    # المصادر العربية (بدون تكرار)
    {"name": "عرب هاردوير",                    "url": "https://www.arabhardware.net/feed"},
    {"name": "البوابة التقنية AIT",            "url": "https://aitnews.com/feed/"},
    {"name": "تيك 24",                         "url": "https://tech24.ma/feed/"},
    {"name": "عالم التقنية",                   "url": "https://www.tech-wd.com/wd/feed"},
    {"name": "سكاي نيوز عربية - تكنولوجيا",   "url": "https://www.skynewsarabia.com/technology/rss"},
    {"name": "الجزيرة نت - تكنولوجيا",        "url": "https://www.aljazeera.net/aljazeerarss/ae187c16-07be-4806-9602-4836b3fdbf06/62763653-6fe3-4c20-afd9-a12880b0a76c"},
    {"name": "بي بي سي عربي - تكنولوجيا",    "url": "https://www.bbc.com/arabic/technology/feed.xml"},
    {"name": "DW عربية - تكنولوجيا",          "url": "https://rss.dw.com/ar/rss-tech"},
    {"name": "رويترز عربي - تكنولوجيا",       "url": "https://feeds.reuters.com/reuters/technologyNews"},
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
        "https://images.pexels.com/photos/275033/pexels-photo-275033.jpeg",
        "https://images.pexels.com/photos/3165335/pexels-photo-3165335.jpeg",
        "https://images.pexels.com/photos/3943746/pexels-photo-3943746.jpeg",
        "https://images.pexels.com/photos/821738/pexels-photo-821738.jpeg",
    ],
    "AI": [
        "https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg",
        "https://images.pexels.com/photos/256381/pexels-photo-256381.jpeg",
        "https://images.pexels.com/photos/3861972/pexels-photo-3861972.jpeg",
        "https://images.pexels.com/photos/8386440/pexels-photo-8386440.jpeg",
        "https://images.pexels.com/photos/1181244/pexels-photo-1181244.jpeg",
        "https://images.pexels.com/photos/5380797/pexels-photo-5380797.jpeg",
        "https://images.pexels.com/photos/2058120/pexels-photo-2058120.jpeg",
        "https://images.pexels.com/photos/8386438/pexels-photo-8386438.jpeg",
    ],
    "tech": [
        "https://images.pexels.com/photos/574071/pexels-photo-574071.jpeg",
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg",
        "https://images.pexels.com/photos/270637/pexels-photo-270637.jpeg",
        "https://images.pexels.com/photos/325185/pexels-photo-325185.jpeg",
        "https://images.pexels.com/photos/459653/pexels-photo-459653.jpeg",
        "https://images.pexels.com/photos/2588753/pexels-photo-2588753.jpeg",
        "https://images.pexels.com/photos/3861971/pexels-photo-3861971.jpeg",
        "https://images.pexels.com/photos/2058121/pexels-photo-2058121.jpeg",
    ],
    "science": [
        "https://images.pexels.com/photos/247431/pexels-photo-247431.jpeg",
        "https://images.pexels.com/photos/326709/pexels-photo-326709.jpeg",
        "https://images.pexels.com/photos/1072824/pexels-photo-1072824.jpeg",
        "https://images.pexels.com/photos/236047/pexels-photo-236047.jpeg",
        "https://images.pexels.com/photos/2894944/pexels-photo-2894944.jpeg",
        "https://images.pexels.com/photos/669015/pexels-photo-669015.jpeg",
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
    if any(k in lower for k in ["elephant", "ghost", "wildlife", "animal", "nature", "forest",
                                  "discovery", "research", "scientist", "science", "ecology", "conservation"]):
        return "science"
    if any(k in lower for k in ["iphone", "samsung", "apple", "macbook", "android", "pixel",
                                  "tech", "smartphone"]):
        return "tech"
    return "default"

# =========================
# جلب خبر واحد من مصدر متاح
# =========================
def get_news() -> tuple[list, str | None]:
    state = load_sources_state()
    available = get_available_sources(NEWS_SOURCES, state)

    if not available:
        logger.warning("⚠️ جميع المصادر استُخدمت اليوم. لا يوجد مصدر متاح.")
        return [], None

    random.shuffle(available)
    posted_links = load_posted_news()

    for source in available:
        logger.info(f"🔍 جاري البحث في: {source['name']}")
        try:
            resp = SESSION.get(source["url"], timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.error(f"❌ فشل جلب RSS من {source['name']}: {e}")
            continue

        if feed.bozo and not feed.entries:
            logger.warning(f"⚠️ تغذية RSS فاسدة لـ {source['name']}: {feed.bozo_exception}")
            continue

        for entry in feed.entries:
            if not getattr(entry, 'link', None):
                continue

            norm_link = normalize_link(entry.link)
            if norm_link in posted_links:
                continue

            content = (
                entry.get('content', [{}])[0].get('value', '')
                or entry.get('summary', '')
            )
            image_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
            image = image_match.group(1) if image_match else ""

            logger.info(f"✅ تم العثور على خبر جديد من {source['name']}")
            return [{
                "title":     entry.title,
                "link":      entry.link,
                "norm_link": norm_link,
                "image":     image,
                "source":    source["name"],
            }], source["name"]

    logger.info("❌ لم يُعثر على أي خبر جديد في المصادر المتاحة.")
    return [], None

# =========================
# تحميل الصورة + تغيير حجمها إذا لزم
# =========================
def download_and_resize_image(url: str) -> bool:
    try:
        res = SESSION.get(url, timeout=30)
        if res.status_code != 200 or "image" not in res.headers.get("Content-Type", ""):
            return False

        img = Image.open(io.BytesIO(res.content))

        # تحويل PNG/RGBA إلى RGB لحفظها كـ JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if img.width > MAX_IMAGE_WIDTH:
            orig_w, orig_h = img.width, img.height
            ratio      = MAX_IMAGE_WIDTH / orig_w
            new_height = int(orig_h * ratio)
            img = img.resize((MAX_IMAGE_WIDTH, new_height), Image.LANCZOS)
            logger.info(f"🖼️ تم تغيير حجم الصورة من {orig_w}x{orig_h} إلى {img.width}x{img.height}")

        img.save(TEMP_IMAGE, "JPEG", quality=85, optimize=True)
        return True

    except Exception as e:
        logger.error(f"خطأ في تحميل/تغيير حجم الصورة: {e}")
        return False

def validate_image() -> bool:
    try:
        with TEMP_IMAGE.open("rb") as f:
            header = f.read(4)
        return header[:3] == b"\xff\xd8\xff" or header[:4] == b"\x89PNG"
    except Exception:
        return False

# =========================
# جلب صورة من Unsplash (مجاني، لا يتطلب مفتاح)
# =========================
def get_unsplash_image(title: str, used_images: set) -> str | None:
    query = re.sub(r'[^\w\s]', '', title)[:80].strip().replace(' ', '+')
    url   = f"https://source.unsplash.com/1200x630/?{query}"
    try:
        res = SESSION.get(url, timeout=15, allow_redirects=True)
        if res.status_code == 200 and "image" in res.headers.get("Content-Type", ""):
            final_url = res.url
            if final_url not in used_images:
                return final_url
    except Exception as e:
        logger.error(f"Unsplash Error: {e}")
    return None

# =========================
# بحث في Google Images كخيار احتياطي
# =========================
def get_google_image(title: str, used_images: set) -> str | None:
    query = re.sub(r'[^\w\s]', '', title)[:100].strip().replace(' ', '+')
    url   = f"https://www.google.com/search?tbm=isch&q={query}"
    try:
        res     = SESSION.get(url, timeout=15)
        matches = re.findall(r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)', res.text, re.IGNORECASE)
        valid   = [m for m in matches if len(m) > 40 and "google" not in m.lower() and "logo" not in m.lower()]
        if not valid:
            return None
        new = [m for m in valid if m not in used_images]
        return random.choice(new if new else valid)
    except Exception as e:
        logger.error(f"Google Images Error: {e}")
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
أنت كاتب محتوى تقني محترف ومؤثر، تكتب بصفحة "تقنية بالدارجة" التي تخاطب الشباب المغربي. مهمتك هي كتابة منشور جذاب واحترافي بالدارجة المغربية حول الخبر التالي:

الخبر: "{title}"

### **تعليمات صارمة للمنشور:**

1. **اللغة والأسلوب**:
   - استخدم دارجة مغربية سليمة 100%، خالية من الأخطاء الإملائية والنحوية.
   - تجنب الترجمة الحرفية من الفصحى أو الإنجليزية.
   - استعمل تعابير مغربية أصيلة بحيت يبان المنشور كأنو كتبو إنسان مغربي حقيقي (مثلاً: "هاد الشي", "واش كتعرف", "أشنو الرأي ديالكم").
   - دوز على المصطلحات التقنية بالإنجليزية (مثل iPhone, AI, update) ولكن فسياق مفهوم.

2. **الهيكل المطلوب (ضروري اتباعو)**:
   - **مقدمة قوية (سطر واحد)**: جملة تشويقية ولا سؤال يثير الفضول.
   - **شرح الخبر (نقطتين أو ثلاث)**:
     * قسم الشرح لعناوين فرعية بحال "🔹 النقطة الأولى:" و "🔹 النقطة الثانية:".
     * كل نقطة تكون بين 30 و 50 كلمة.
   - **التأثير على المستخدم المغربي (فقرة قصيرة)**.
   - **رأي شخصي (جملة أو جملتين)**.
   - **سؤال تفاعلي**: سؤال مفتوح يحفز المتابعين على التعليق.
   - **الهاشتاجات**: سطر منفصل فيه 4-5 هاشتاجات متنوعة.

3. **الإيموجي**: استخدم من 4 إلى 6 إيموجيات مناسبة وموزعة بذكاء.

4. **الطول**: بين 1500 و 2000 حرف (بما فيه المسافات). لا تتجاوز 2000 حرف.

5. **الجودة**: نص سلس وسهل القراءة، بدون حشو أو تكرار.

**اكتب المنشور مباشرة من دون أي مقدمات إضافية.**
"""

    headers  = {"Content-Type": "application/json"}
    payload  = {"contents": [{"parts": [{"text": prompt}]}]}
    delay    = 30

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

            # قطع النص عند آخر فراغ بدلاً من قطعه في منتصف كلمة
            if len(post_text) > MAX_POST_LENGTH:
                logger.warning(f"⚠️ النص طويل ({len(post_text)} حرف)، سيتم تقليمه بذكاء.")
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
                data    = {"caption": message, "access_token": FB_PAGE_ACCESS_TOKEN},
                files   = {"source": ("post.jpg", img_file, "image/jpeg")},
                timeout = 30,
            )
        return res.json()
    except Exception as e:
        logger.error(f"❌ Facebook API Error: {e}")
        return None

# =========================
# الدالة الرئيسية
# =========================
def main():
    posted_news = load_posted_news()
    articles, source_name = get_news()

    if not articles:
        logger.info("لا توجد أخبار جديدة للنشر.")
        return

    article = articles[0]
    logger.info(f"📝 معالجة: {article['title']} (من {article['source']})")

    used_images = load_used_images()
    image_ok    = False

    # 1. صورة الخبر الأصلية
    if article.get("image"):
        logger.info("🖼️ تجربة صورة الخبر الأصلية...")
        image_ok = download_and_resize_image(article["image"]) and validate_image()
        if image_ok:
            logger.info("✅ تم استخدام صورة الخبر الأصلية")

    # 2. Unsplash (مجاني وموثوق)
    if not image_ok:
        logger.info("🔍 البحث عن صورة عبر Unsplash...")
        unsplash_url = get_unsplash_image(article["title"], used_images)
        if unsplash_url:
            image_ok = download_and_resize_image(unsplash_url) and validate_image()
            if image_ok:
                logger.info("✅ تم استخدام صورة من Unsplash")
                used_images.add(unsplash_url)
                save_used_images(used_images)

    # 3. Google Images كخيار ثانٍ
    if not image_ok:
        logger.info("🔍 البحث عن صورة عبر Google Images...")
        google_url = get_google_image(article["title"], used_images)
        if google_url:
            image_ok = download_and_resize_image(google_url) and validate_image()
            if image_ok:
                logger.info("✅ تم استخدام صورة من Google Images")
                used_images.add(google_url)
                save_used_images(used_images)

    # 4. الصورة الاحتياطية من المكتبة المحلية
    if not image_ok:
        topic  = get_topic(article["title"])
        backup = random.choice(IMAGE_LIBRARY.get(topic, IMAGE_LIBRARY["default"]))
        logger.info(f"🖼️ استخدام صورة احتياطية لموضوع '{topic}'")
        image_ok = download_and_resize_image(backup) and validate_image()
        if not image_ok:
            logger.error("❌ فشل تحميل أي صورة. تخطي الخبر.")
            return

    # توليد المنشور
    post_text = generate_post(article["title"])
    if not post_text:
        logger.error("❌ فشل توليد المنشور.")
        return

    # النشر على فيسبوك
    logger.info("🚀 جاري النشر على فيسبوك...")
    result = post_to_facebook(post_text)

    if result and "id" in result:
        logger.info(f"✅ تم النشر بنجاح! المعرف: {result['id']}")
        # حفظ الخبر كمنشور
        posted_news.add(article["norm_link"])
        save_posted_news(posted_news)
        # تحديث حالة المصدر
        if source_name:
            state = load_sources_state()
            mark_source_used(source_name, state)
            logger.info(f"📅 تم تحديث حالة المصدر '{source_name}'")
    else:
        logger.error(f"❌ فشل النشر على فيسبوك: {result}")

    # حذف الصورة المؤقتة
    try:
        TEMP_IMAGE.unlink(missing_ok=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()

