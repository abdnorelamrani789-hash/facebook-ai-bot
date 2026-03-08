import os
import requests
import random
import json
import feedparser
import re
from urllib.parse import urlparse, urlunparse

# =========================
# Environment Variables
# =========================
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")      # ← جديد: لازم تضيفه
MODEL_NAME = "gemini-2.5-flash"

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY or not PEXELS_API_KEY:
    raise Exception("Missing required environment variables (أضف PEXELS_API_KEY)")

TEMP_IMAGE = "temp_image.jpg"
POSTED_FILE = "posted_news.json"

# =========================
# تطبيع الروابط + تحميل posted_news
# =========================
def normalize_link(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', '')).rstrip('/')
    return clean

if os.path.exists(POSTED_FILE):
    try:
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            posted_news = {normalize_link(link): True for link in data if isinstance(link, str)}
        else:
            posted_news = {normalize_link(k): v for k, v in data.items()}
    except:
        posted_news = {}
else:
    posted_news = {}

# =========================
# مصادر الأخبار
# =========================
NEWS_SOURCES = [
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica", "url": "https://arstechnica.com/feed/"},
    {"name": "Engadget", "url": "https://www.engadget.com/rss.xml"},
    {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/"},
    {"name": "CNET", "url": "https://www.cnet.com/rss/"},
    {"name": "عرب هاردوير", "url": "https://www.arabhardware.net/feed"},
    {"name": "البوابة التقنية AIT", "url": "https://aitnews.com/feed/"},
    {"name": "تيك 24", "url": "https://tech24.ma/feed/"},
    {"name": "ياسين تك", "url": "https://www.yasintech.com/feed/"},
]

# =========================
# مكتبة الصور الاحتياطية (48 صورة + science)
# =========================
IMAGE_LIBRARY = {
    "gaming": [ ... ],   # نفس القائمة السابقة كاملة (انسخها من الكود القديم)
    "AI": [ ... ],
    "tech": [ ... ],
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
    "default": [ ... ]
}  # (انسخ القوائم كاملة من الكود السابق)

# =========================
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
# جلب خبر واحد من مصدر عشوائي
# =========================
def get_news():
    sources = NEWS_SOURCES.copy()
    random.shuffle(sources)
    
    for source in sources:
        print(f"🔍 جاري البحث في: {source['name']}")
        feed = feedparser.parse(source["url"])
        
        for entry in feed.entries:
            norm_link = normalize_link(entry.link)
            if norm_link in posted_news:
                continue
                
            content = entry.get('content', [{}])[0].get('value', '') or entry.get('summary', '')
            image_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
            image = image_match.group(1) if image_match else ""
            
            print(f"✅ تم العثور على خبر جديد من {source['name']}")
            return [{
                "title": entry.title,
                "link": entry.link,
                "norm_link": norm_link,
                "image": image,
                "source": source["name"]
            }]
    
    print("❌ لم يتم العثور على أي خبر جديد")
    return []

# =========================
# Download + Validate Image
# =========================
def download_image(url):
    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200 and "image" in res.headers.get("Content-Type", ""):
            with open(TEMP_IMAGE, "wb") as f:
                f.write(res.content)
            return True
    except:
        pass
    return False

def validate_image():
    try:
        with open(TEMP_IMAGE, "rb") as f:
            header = f.read(4)
        return header[:3] == b"\xff\xd8\xff"
    except:
        return False

# =========================
# 🔍 بحث تلقائي عن صورة مناسبة في Pexels (بدل Google Images)
# =========================
def get_pexels_image(title: str) -> str:
    query = title.replace(" ", "+").replace(":", "").replace("?", "").replace("!", "")[:80]
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=3&orientation=landscape"
    headers = {"Authorization": PEXELS_API_KEY}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            photos = data.get("photos", [])
            if photos:
                return photos[0]["src"]["large2x"]   # أعلى جودة
    except Exception as e:
        print("Pexels API Error:", e)
    return None

# =========================
# Generate Post (مع هاشتاجات)
# =========================
def generate_post(title):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
أنت خبير تقني مغربي محترف ومؤثر.
اكتب منشور احترافي، جذاب وطويل بالدارجة المغربية الأصيلة لصفحة "تقنية بالدارجة".

الخبر: "{title}"

التعليمات الدقيقة:
- ابدأ مباشرة بجملة قوية تجذب الانتباه.
- شرح الخبر بطريقة مبسطة ومفصلة.
- أبرز أهميته وتأثيره على حياتنا.
- استعمل إيموجي تقنية بذكاء.
- في النهاية أضف سطر منفصل يحتوي على بالضبط 4-5 هاشتاجات مناسبة.

الهدف: منشور يولّد تفاعل عالي!
"""

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, json=data, headers=headers, timeout=30)
        res.raise_for_status()
        res_json = res.json()
        return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return None

# =========================
# Post to Facebook
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
        print("Facebook API Error:", e)
        return None

# =========================
# Main - الآن يبحث في Pexels أولاً
# =========================
def main():
    articles = get_news()
    if not articles:
        print("No new articles to post.")
        return

    article = articles[0]
    print(f"📝 جاري معالجة الخبر: {article['title']} (من {article['source']})")

    # === اختيار الصورة الجديد (ترتيب الأولوية) ===
    image_ok = False

    # 1. صورة الخبر الأصلية
    if article.get("image"):
        print("🖼️ جاري تجربة صورة الخبر الأصلية...")
        image_ok = download_image(article["image"])
        if image_ok and validate_image():
            print("✅ تم استخدام صورة الخبر الأصلية")
        else:
            image_ok = False

    # 2. بحث في Pexels (الجديد)
    if not image_ok:
        print("🔍 جاري البحث التلقائي عن صورة مناسبة في Pexels...")
        pexels_url = get_pexels_image(article["title"])
        if pexels_url:
            image_ok = download_image(pexels_url)
            if image_ok and validate_image():
                print("✅ تم العثور على صورة ممتازة من Pexels")
            else:
                image_ok = False

    # 3. الصورة الاحتياطية من المكتبة (آخر حل)
    if not image_ok:
        topic = get_topic(article["title"])
        backup_image = random.choice(IMAGE_LIBRARY.get(topic, IMAGE_LIBRARY["default"]))
        print(f"🖼️ Using backup image for '{topic}'")
        image_ok = download_image(backup_image)
        if not image_ok:
            print("❌ فشل تحميل الصورة، تخطي الخبر")
            return

    post_text = generate_post(article["title"])
    if not post_text:
        print("❌ فشل توليد المنشور.")
        return

    print("🚀 Posting to Facebook...")
    res = post_to_facebook(post_text)
    print("Facebook response:", res)

    posted_news[article["norm_link"]] = True
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(posted_news, f, ensure_ascii=False, indent=2)
    print(f"✅ تم النشر والحفظ بنجاح من {article['source']}")

    try:
        os.remove(TEMP_IMAGE)
    except:
        pass

if __name__ == "__main__":
    main()
