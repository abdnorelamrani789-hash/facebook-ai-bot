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
            print("✅ تم تحويل الملف القديم من list إلى dict")
        else:
            posted_news = {normalize_link(k): v for k, v in data.items()}
    except:
        posted_news = {}
else:
    posted_news = {}

# =========================
# مصادر الأخبار (7 مصادر)
# =========================
NEWS_SOURCES = [
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica", "url": "https://arstechnica.com/feed/"},
    {"name": "Engadget", "url": "https://www.engadget.com/rss.xml"},
    {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/"},
    {"name": "CNET", "url": "https://www.cnet.com/rss/"},
]

# =========================
# مكتبة الصور الاحتياطية (48 صورة عالية الجودة)
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
    elif any(k in lower for k in ["ai", "artificial", "gemini", "chatgpt", "openai", "llm", "neural"]):
        return "AI"
    elif any(k in lower for k in ["iphone", "samsung", "apple", "macbook", "android", "pixel", "tech"]):
        return "tech"
    return "default"

# =========================
# جلب حتى 3 أخبار جديدة
# =========================
def get_news():
    new_articles = []
    for source in NEWS_SOURCES:
        print(f"🔍 جاري البحث في: {source['name']}")
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            raw_link = entry.link
            norm_link = normalize_link(raw_link)
            if norm_link in posted_news:
                continue
                
            content = entry.get('content', [{}])[0].get('value', '') or entry.get('summary', '')
            image_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
            image = image_match.group(1) if image_match else ""
            
            new_articles.append({
                "title": entry.title,
                "link": raw_link,
                "norm_link": norm_link,
                "image": image,
                "source": source["name"]
            })
            print(f"✅ تم العثور على خبر جديد من {source['name']}")
            
            if len(new_articles) >= 3:
                break
        if len(new_articles) >= 3:
            break
    return new_articles

# =========================
# Download Image
# =========================
def download_image(url):
    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200 and "image" in res.headers.get("Content-Type", ""):
            with open(TEMP_IMAGE, "wb") as f:
                f.write(res.content)
            return True
    except Exception as e:
        print("Image download failed:", e)
    return False

# =========================
# Validate Image
# =========================
def validate_image():
    try:
        with open(TEMP_IMAGE, "rb") as f:
            header = f.read(4)
        return header[:3] == b"\xff\xd8\xff"
    except:
        return False

# =========================
# Generate Post using Gemini
# =========================
def generate_post(title):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
أنت خبير في التقنية. عندك خبر: "{title}".
اكتب منشور احترافي وطويل بالدارجة المغربية لصفحة "تقنية بالدارجة"، بدون مقدمة زايدة.
اشرح الخبر بطريقة مبسطة وفهمها للناس، استعمل إيموجي تقنية.
في النهاية ضيف سؤال لتحفيز التفاعل.
"""
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, json=data, headers=headers, timeout=30)
        res_json = res.json()
        if "candidates" not in res_json:
            print("Gemini API error:", res_json)
            return None
        return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print("Gemini Error:", e)
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
# Main - نشر متعدد (حتى 3 أخبار)
# =========================
def main():
    articles = get_news()
    if not articles:
        print("No new articles to post from any source.")
        return

    for idx, article in enumerate(articles, 1):
        print(f"📝 [{idx}/{len(articles)}] Generating post for: {article['title']} (من {article['source']})")

        # تنزيل الصورة
        image_ok = False
        if article.get("image"):
            image_ok = download_image(article["image"])
            if image_ok and not validate_image():
                image_ok = False

        if not image_ok:
            topic = get_topic(article["title"])
            backup_image = random.choice(IMAGE_LIBRARY.get(topic, IMAGE_LIBRARY["default"]))
            print(f"🖼️ Using backup image for '{topic}': {backup_image[:80]}...")
            image_ok = download_image(backup_image)
            if not image_ok:
                print("No image, skipping...")
                continue

        post_text = generate_post(article["title"])
        if not post_text:
            continue

        print("🚀 Posting to Facebook...")
        res = post_to_facebook(post_text)
        print("Facebook response:", res)

        # حفظ الخبر
        posted_news[article["norm_link"]] = True
        with open(POSTED_FILE, "w", encoding="utf-8") as f:
            json.dump(posted_news, f, ensure_ascii=False, indent=2)
        print(f"✅ تم حفظ الخبر بنجاح من {article['source']}")

        # تنظيف
        try:
            os.remove(TEMP_IMAGE)
        except:
            pass

if __name__ == "__main__":
    main()
