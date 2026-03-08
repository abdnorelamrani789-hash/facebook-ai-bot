import os
import requests
import random
import json
import feedparser
import re
import logging
from datetime import date
from urllib.parse import urlparse, urlunparse
from PIL import Image
import io

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
    raise Exception("Missing required environment variables")

TEMP_IMAGE = "temp_image.jpg"
POSTED_FILE = "posted_news.json"
SOURCES_STATE_FILE = "sources_state.json"
USED_IMAGES_FILE = "used_images.json"
MAX_IMAGE_WIDTH = 1200  # أقصى عرض للصورة
MAX_POST_LENGTH = 2000  # أقصى طول للمنشور (عدد الحروف)

# =========================
# تطبيع الروابط + تحميل posted_news
# =========================
def normalize_link(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', '')).rstrip('/')
    return clean

def load_posted_news():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {normalize_link(link): True for link in data if isinstance(link, str)}
            elif isinstance(data, dict):
                return {normalize_link(k): v for k, v in data.items()}
        except Exception as e:
            logger.error(f"Error loading posted news: {e}")
    return {}

def save_posted_news(posted):
    try:
        with open(POSTED_FILE, "w", encoding="utf-8") as f:
            json.dump(posted, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving posted news: {e}")

# =========================
# إدارة حالة المصادر (آخر استخدام)
# =========================
def load_sources_state():
    if os.path.exists(SOURCES_STATE_FILE):
        try:
            with open(SOURCES_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading sources state: {e}")
    return {}

def save_sources_state(state):
    try:
        with open(SOURCES_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving sources state: {e}")

def get_available_sources(sources, state):
    today = date.today().isoformat()
    available = []
    for src in sources:
        last_used = state.get(src["name"])
        if last_used != today:
            available.append(src)
    return available

def mark_source_used(source_name, state):
    today = date.today().isoformat()
    state[source_name] = today
    save_sources_state(state)

# =========================
# إدارة الصور المستخدمة (لتجنب التكرار)
# =========================
def load_used_images():
    if os.path.exists(USED_IMAGES_FILE):
        try:
            with open(USED_IMAGES_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            logger.error(f"Error loading used images: {e}")
    return set()

def save_used_images(used_set):
    try:
        with open(USED_IMAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(list(used_set), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving used images: {e}")

# =========================
# مصادر الأخبار (30 مصدر محدثة ومستقرة)
# =========================
NEWS_SOURCES = [
    # المصادر الأجنبية الموثوقة
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica", "url": "https://arstechnica.com/feed/"},
    {"name": "Engadget", "url": "https://www.engadget.com/rss.xml"},
    {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/"},
    {"name": "CNET", "url": "https://www.cnet.com/rss/news/"},
    {"name": "Tom's Hardware", "url": "https://www.tomshardware.com/feeds/all"},
    {"name": "Android Police", "url": "https://www.androidpolice.com/feed/"},
    {"name": "9to5Mac", "url": "https://9to5mac.com/feed/"},
    {"name": "GSMArena", "url": "https://www.gsmarena.com/rss-news-reviews.php3"},
    {"name": "XDA Developers", "url": "https://www.xda-developers.com/feed/"},
    {"name": "The Next Web", "url": "https://thenextweb.com/feed/"},
    {"name": "Mashable", "url": "https://mashable.com/feed/"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/"},
    {"name": "PC Gamer", "url": "https://www.pcgamer.com/feed/"},
    {"name": "MacRumors", "url": "https://www.macrumors.com/macrumors.xml"},
    {"name": "Slashdot", "url": "https://rss.slashdot.org/Slashdot/slashdotMain"},
    {"name": "Digital Trends", "url": "https://www.digitaltrends.com/feed/"},
    # المصادر العربية الموثوقة
    {"name": "عرب هاردوير", "url": "https://www.arabhardware.net/feed"},
    {"name": "البوابة التقنية AIT", "url": "https://aitnews.com/feed/"},
    {"name": "تيك 24", "url": "https://tech24.ma/feed/"},
    {"name": "البوابة العربية للأخبار التقنية", "url": "https://aitnews.com/feed/"},
    {"name": "عالم التقنية", "url": "https://www.tech-wd.com/wd/feed"},
    {"name": "سكاي نيوز عربية - تكنولوجيا", "url": "https://www.skynewsarabia.com/technology/rss"},
    {"name": "الجزيرة نت - تكنولوجيا", "url": "https://www.aljazeera.net/aljazeerarss/ae187c16-07be-4806-9602-4836b3fdbf06/62763653-6fe3-4c20-afd9-a12880b0a76c"},
    {"name": "بي بي سي عربي - تكنولوجيا", "url": "https://www.bbc.com/arabic/technology/feed.xml"},
    {"name": "DW عربية - تكنولوجيا", "url": "https://rss.dw.com/ar/rss-tech"},
]
# =========================
# مكتبة الصور الاحتياطية (كاملة)
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
        "https://images.pexels.com/photos/577585/pexels-photo-577585.jpeg",
        "https://images.pexels.com/photos/1591061/pexels-photo-1591061.jpeg",
        "https://images.pexels.com/photos/3165336/pexels-photo-3165336.jpeg",
        "https://images.pexels.com/photos/3943747/pexels-photo-3943747.jpeg"
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
        "https://images.pexels.com/photos/3861973/pexels-photo-3861973.jpeg",
        "https://images.pexels.com/photos/256380/pexels-photo-256380.jpeg",
        "https://images.pexels.com/photos/1181243/pexels-photo-1181243.jpeg",
        "https://images.pexels.com/photos/5380798/pexels-photo-5380798.jpeg"
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
        "https://images.pexels.com/photos/1181245/pexels-photo-1181245.jpeg",
        "https://images.pexels.com/photos/3165337/pexels-photo-3165337.jpeg",
        "https://images.pexels.com/photos/459654/pexels-photo-459654.jpeg",
        "https://images.pexels.com/photos/2588754/pexels-photo-2588754.jpeg"
    ],
    "science": [
        "https://images.pexels.com/photos/247431/pexels-photo-247431.jpeg",
        "https://images.pexels.com/photos/326709/pexels-photo-326709.jpeg",
        "https://images.pexels.com/photos/1072824/pexels-photo-1072824.jpeg",
        "https://images.pexels.com/photos/236047/pexels-photo-236047.jpeg",
        "https://images.pexels.com/photos/2894944/pexels-photo-2894944.jpeg",
        "https://images.pexels.com/photos/669015/pexels-photo-669015.jpeg",
        "https://images.pexels.com/photos/1108572/pexels-photo-1108572.jpeg",
        "https://images.pexels.com/photos/247599/pexels-photo-247599.jpeg",
        "https://images.pexels.com/photos/417173/pexels-photo-417173.jpeg",
        "https://images.pexels.com/photos/572897/pexels-photo-572897.jpeg"
    ],
    "default": [
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg",
        "https://images.pexels.com/photos/574071/pexels-photo-574071.jpeg",
        "https://images.pexels.com/photos/325185/pexels-photo-325185.jpeg",
        "https://images.pexels.com/photos/270637/pexels-photo-270637.jpeg"
    ]
}
# ========================
# تحديد الموضوع
# =========================
def get_topic(title: str) -> str:
    lower = title.lower()
    if any(k in lower for k in ["game", "playstation", "nintendo", "xbox", "sony", "gaming", "esports"]):
        return "gaming"
    elif any(k in lower for k in ["ai", "artificial", "gemini", "chatgpt", "openai", "gpt", "llm", "neural"]):
        return "AI"
    elif any(k in lower for k in ["elephant", "ghost", "wildlife", "animal", "nature", "forest", "discovery", "research", "scientist", "science", "ecology", "conservation"]):
        return "science"
    elif any(k in lower for k in ["iphone", "samsung", "apple", "macbook", "android", "pixel", "tech", "smartphone"]):
        return "tech"
    return "default"

# =========================
# جلب خبر واحد من مصدر متاح
# =========================
def get_news():
    state = load_sources_state()
    available_sources = get_available_sources(NEWS_SOURCES, state)
    
    if not available_sources:
        logger.warning("⚠️ لا توجد مصادر متاحة اليوم (جميعها استخدمت). توقف.")
        return [], None
    
    random.shuffle(available_sources)
    posted_links = load_posted_news()
    
    for source in available_sources:
        logger.info(f"🔍 جاري البحث في: {source['name']}")
        try:
            resp = requests.get(source["url"], timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            if feed.bozo:
                logger.warning(f"⚠️ خطأ في تغذية RSS لـ {source['name']}: {feed.bozo_exception}")
                continue
        except Exception as e:
            logger.error(f"❌ فشل جلب RSS من {source['name']}: {e}")
            continue
        
        for entry in feed.entries:
            norm_link = normalize_link(entry.link)
            if norm_link in posted_links:
                continue
                
            content = entry.get('content', [{}])[0].get('value', '') or entry.get('summary', '')
            image_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
            image = image_match.group(1) if image_match else ""
            
            logger.info(f"✅ تم العثور على خبر جديد من {source['name']}")
            return [{
                "title": entry.title,
                "link": entry.link,
                "norm_link": norm_link,
                "image": image,
                "source": source["name"]
            }], source["name"]
    
    logger.info("❌ لم يتم العثور على أي خبر جديد في المصادر المتاحة")
    return [], None

# =========================
# تحميل الصورة والتحقق منها + تغيير الحجم إذا لزم الأمر
# =========================
def download_and_resize_image(url):
    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200 and "image" in res.headers.get("Content-Type", ""):
            # فتح الصورة باستخدام PIL
            img = Image.open(io.BytesIO(res.content))
            # تغيير الحجم إذا كان العرض أكبر من MAX_IMAGE_WIDTH
            if img.width > MAX_IMAGE_WIDTH:
                ratio = MAX_IMAGE_WIDTH / img.width
                new_height = int(img.height * ratio)
                img = img.resize((MAX_IMAGE_WIDTH, new_height), Image.LANCZOS)
                logger.info(f"🖼️ تم تغيير حجم الصورة من {img.width}x{img.height} إلى {MAX_IMAGE_WIDTH}x{new_height}")
            # حفظ الصورة بصيغة JPEG بجودة 85% لتقليل الحجم
            img.save(TEMP_IMAGE, "JPEG", quality=85, optimize=True)
            return True
    except Exception as e:
        logger.error(f"Download/resize image error: {e}")
    return False

def validate_image():
    try:
        with open(TEMP_IMAGE, "rb") as f:
            header = f.read(4)
        if header[:3] == b"\xff\xd8\xff":
            return True
        if header[:4] == b"\x89PNG":
            return True
        return False
    except:
        return False

# =========================
# بحث متطور في Google Images مع اختيار عشوائي
# =========================
def get_google_image(title: str, used_images=None) -> str:
    query = title.replace(" ", "+").replace(":", "").replace("?", "").replace("!", "")[:100]
    url = f"https://www.google.com/search?tbm=isch&q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        matches = re.findall(r'https?://[^"\']+\.(?:jpg|jpeg|png|webp|gif)', res.text, re.IGNORECASE)
        valid_images = [
            m for m in matches 
            if len(m) > 40 and "google" not in m.lower() and "logo" not in m.lower()
        ]
        if not valid_images:
            return None
        
        if used_images is not None:
            new_images = [img for img in valid_images if img not in used_images]
            if new_images:
                return random.choice(new_images)
            else:
                return random.choice(valid_images)
        else:
            return random.choice(valid_images)
    except Exception as e:
        logger.error(f"Google Images Error: {e}")
        return None

# =========================
# توليد المنشور عبر Gemini (نسخة محسّنة مع تحديد صارم للطول)
# =========================
def generate_post(title):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    
    # Prompt محسّن مع تعليمات صارمة حول الطول
    prompt = f"""
أنت كاتب محتوى تقني محترف ومؤثر على وسائل التواصل الاجتماعي، تستهدف الجمهور المغربي الشاب المهتم بالتكنولوجيا. اكتب منشوراً احترافياً وجذاباً بالدارجة المغربية حول الخبر التالي:

الخبر: "{title}"

متطلبات صارمة:
- **الطول**: يجب أن يكون المنشور بين 1500 و 2000 حرف بالضبط. لا تتجاوز 2000 حرف أبداً.
- الهيكل:
  1. مقدمة قوية: جملة أو سؤال يثير الفضول.
  2. شرح الخبر: بطريقة مبسطة.
  3. الأهمية والتأثير: لماذا هذا الخبر مهم للمغربي.
  4. لمسة شخصية: رأيك أو توقعاتك.
  5. سؤال تفاعلي: في النهاية.
  6. الإيموجي: 3-5 إيموجيات مناسبة (📱💻🚀🔥).
  7. الهاشتاجات: سطر منفصل بـ 4-5 هاشتاجات.

- اللغة: دارجة مغربية سليمة مع بعض المصطلحات التقنية بالإنجليزية.

اكتب المنشور الآن دون أي مقدمات إضافية.
"""

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, json=data, headers=headers, timeout=30)
        res.raise_for_status()
        res_json = res.json()
        post_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # إذا تجاوز الحد الأقصى، نطلب إعادة كتابة بشكل أقصر
        if len(post_text) > MAX_POST_LENGTH:
            logger.warning(f"⚠️ النص طويل جداً ({len(post_text)} حرف)، جاري طلب نسخة مختصرة...")
            
            retry_prompt = f"""
المنشور الذي أرسلته سابقاً طويل جداً (تجاوز 2000 حرف). أعد كتابة نفس المنشور ولكن بشكل مختصر جداً، مع الالتزام بالطول التالي: 1500-1800 حرف.

الموضوع: "{title}"

المطلوب:
- مقدمة سريعة.
- شرح الخبر في نقطتين.
- التأثير الرئيسي.
- سؤال تفاعلي واحد.
- 3-4 هاشتاجات.

اكتب النسخة المختصرة مباشرة:
"""
            data = {"contents": [{"parts": [{"text": retry_prompt}]}]}
            res = requests.post(url, json=data, headers=headers, timeout=30)
            res.raise_for_status()
            res_json = res.json()
            post_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # إذا لا يزال طويلاً، نقلم بذكاء (نبحث عن آخر جملة كاملة)
        if len(post_text) > MAX_POST_LENGTH:
            logger.warning(f"⚠️ لا يزال النص طويلاً ({len(post_text)} حرف)، سيتم تقليمه بذكاء")
            
            # نأخذ أول MAX_POST_LENGTH حرف
            trimmed = post_text[:MAX_POST_LENGTH]
            # نبحث عن آخر علامة نهاية جملة في النصف الثاني من النص المقتطع
            # علامات نهاية الجمل: . ! ؟ ... ). ]. " 
            last_punct = -1
            for punct in ['.', '!', '؟', '...', ').', '].', '"']:
                pos = trimmed.rfind(punct)
                if pos > MAX_POST_LENGTH * 0.7:  # ضمن آخر 30%
                    last_punct = pos
                    break
            
            if last_punct != -1:
                post_text = trimmed[:last_punct+1]
                # نحاول إضافة الهاشتاجات إذا كانت موجودة بعد القطع
                # نبحث عن # في النص المتبقي
                hashtag_line = ""
                lines = post_text.split('\n')
                for line in reversed(lines):
                    if '#' in line:
                        hashtag_line = line
                        break
                if hashtag_line:
                    # إذا وجدنا سطر هاشتاجات، نتركه، وإلا نخلي النص كما هو
                    pass
            else:
                # إذا لم نجد علامة، نأخذ النص كما هو (أفضل من لا شيء)
                post_text = trimmed
        
        return post_text
        
    except Exception as e:
        logger.error(f"❌ Gemini Error: {e}")
        return None

# =========================
# النشر على فيسبوك
# =========================
def post_to_facebook(message):
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    try:
        with open(TEMP_IMAGE, "rb") as img_file:
            files = {"source": ("post.jpg", img_file, "image/jpeg")}
            payload = {"caption": message, "access_token": FB_PAGE_ACCESS_TOKEN}
            res = requests.post(fb_url, data=payload, files=files, timeout=30)
        return res.json()
    except Exception as e:
        logger.error("Facebook API Error:", e)
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
    logger.info(f"📝 جاري معالجة الخبر: {article['title']} (من {article['source']})")

    used_images = load_used_images()

    image_ok = False

    # 1. صورة الخبر الأصلية
    if article.get("image"):
        logger.info("🖼️ جاري تجربة صورة الخبر الأصلية...")
        image_ok = download_and_resize_image(article["image"])
        if image_ok and validate_image():
            logger.info("✅ تم استخدام صورة الخبر الأصلية")
        else:
            image_ok = False

    # 2. بحث في Google Images
    if not image_ok:
        logger.info("🔍 جاري البحث التلقائي عن صورة مناسبة في Google Images...")
        google_url = get_google_image(article["title"], used_images)
        if google_url:
            image_ok = download_and_resize_image(google_url)
            if image_ok and validate_image():
                logger.info("✅ تم العثور على صورة ممتازة من Google Images")
                used_images.add(google_url)
                save_used_images(used_images)
            else:
                image_ok = False

    # 3. الصورة الاحتياطية
    if not image_ok:
        topic = get_topic(article["title"])
        backup_image = random.choice(IMAGE_LIBRARY.get(topic, IMAGE_LIBRARY["default"]))
        logger.info(f"🖼️ استخدام صورة احتياطية لموضوع '{topic}'")
        image_ok = download_and_resize_image(backup_image)
        if not image_ok or not validate_image():
            logger.error("❌ فشل تحميل الصورة، تخطي الخبر")
            return

    post_text = generate_post(article["title"])
    if not post_text:
        logger.error("❌ فشل توليد المنشور.")
        return

    logger.info("🚀 جاري النشر على فيسبوك...")
    res = post_to_facebook(post_text)
    if res and "id" in res:
        logger.info(f"✅ تم النشر بنجاح: {res['id']}")
    else:
        logger.error(f"❌ فشل النشر على فيسبوك: {res}")
        return

    posted_news[article["norm_link"]] = True
    save_posted_news(posted_news)
    
    if source_name:
        state = load_sources_state()
        mark_source_used(source_name, state)
        logger.info(f"📅 تم تحديث حالة المصدر '{source_name}' لليوم")

    try:
        os.remove(TEMP_IMAGE)
    except:
        pass

if __name__ == "__main__":
    main()
