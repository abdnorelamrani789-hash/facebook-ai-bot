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
MODEL_NAME = "gemini-2.5-flash"

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise Exception("Missing required environment variables")

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
# 🔍 بحث بسيط في Google Images (بدون أي API Key)
# =========================
def get_google_image(title: str) -> str:
    query = title.replace(" ", "+").replace(":", "").replace("?", "").replace("!", "")[:100]
    url = f"https://www.google.com/search?tbm=isch&q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        # استخراج أول صورة مباشرة من نتائج Google
        matches = re.findall(r'https?://[^"\']+\.(?:jpg|jpeg|png|webp|gif)', res.text, re.IGNORECASE)
        for m in matches:
            if len(m) > 40 and "google" not in m.lower() and "logo" not in m.lower():
                return m
    except Exception as e:
        print("Google Images Error:", e)
    return None

# =========================
# Generate Post
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
# Main
# =========================
def main():
    articles = get_news()
    if not articles:
        print("No new articles to post.")
        return

    article = articles[0]
    print(f"📝 جاري معالجة الخبر: {article['title']} (من {article['source']})")

    # === اختيار الصورة (ترتيب الأولوية) ===
    image_ok = False

    # 1. صورة الخبر الأصلية
    if article.get("image"):
        print("🖼️ جاري تجربة صورة الخبر الأصلية...")
        image_ok = download_image(article["image"])
        if image_ok and validate_image():
            print("✅ تم استخدام صورة الخبر الأصلية")
        else:
            image_ok = False

    # 2. بحث في Google Images (الجديد)
    if not image_ok:
        print("🔍 جاري البحث التلقائي عن صورة مناسبة في Google Images...")
        google_url = get_google_image(article["title"])
        if google_url:
            image_ok = download_image(google_url)
            if image_ok and validate_image():
                print("✅ تم العثور على صورة ممتازة من Google Images")
            else:
                image_ok = False

    # 3. الصورة الاحتياطية من المكتبة
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
