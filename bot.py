import os
import requests
import random
import json
import feedparser
import re  # لاستخراج الصورة من الـ RSS

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
# Load posted news (محصن ضد أي نوع بيانات قديم)
# =========================
if os.path.exists(POSTED_FILE):
    try:
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if isinstance(data, list):
            posted_news = {link: True for link in data if isinstance(link, str)}
            print("✅ تم تحويل الملف القديم من list إلى dict")
        else:
            posted_news = data
    except (json.JSONDecodeError, TypeError):
        print("⚠️ ملف posted_news.json تالف، نبدأ من الصفر")
        posted_news = {}
else:
    posted_news = {}

# =========================
# Backup Images Library
# =========================
IMAGE_LIBRARY = {
    "gaming": [
        "https://images.pexels.com/photos/442580/pexels-photo-442580.jpeg",
        "https://images.pexels.com/photos/163064/play-station-ps4-controller-game-163064.jpeg",
        "https://images.pexels.com/photos/1591060/pexels-photo-1591060.jpeg"
    ],
    "AI": [
        "https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg",
        "https://images.pexels.com/photos/256381/pexels-photo-256381.jpeg",
        "https://images.pexels.com/photos/3861972/pexels-photo-3861972.jpeg"
    ],
    "tech": [
        "https://images.pexels.com/photos/574071/pexels-photo-574071.jpeg",
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg",
        "https://images.pexels.com/photos/270637/pexels-photo-270637.jpeg"
    ],
    "default": [
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg"
    ]
}

# =========================
# Fetch news from RSS + استخراج الصورة الصحيح
# =========================
NEWS_RSS = "https://www.theverge.com/rss/index.xml"

def get_topic(title: str) -> str:
    lower = title.lower()
    if any(k in lower for k in ["game", "playstation", "nintendo", "xbox", "gaming", "sony"]):
        return "gaming"
    elif any(k in lower for k in ["ai", "artificial", "gemini", "chatgpt", "openai", "llm"]):
        return "AI"
    elif any(k in lower for k in ["iphone", "samsung", "apple", "macbook", "phone", "android", "tech"]):
        return "tech"
    return "default"

def get_news():
    feed = feedparser.parse(NEWS_RSS)
    for entry in feed.entries:
        link = entry.link
        if link in posted_news:
            continue
            
        # استخراج الصورة من الـ content أو summary (طريقة The Verge الصحيحة)
        content = entry.get('content', [{}])[0].get('value', '') or entry.get('summary', '')
        image_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
        image = image_match.group(1) if image_match else ""
        
        return {"title": entry.title, "link": link, "image": image}
    return None

# =========================
# Download & Validate Image
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

def validate_image():
    try:
        with open(TEMP_IMAGE, "rb") as f:
            header = f.read(4)
        return header[:3] == b"\xff\xd8\xff"  # JPEG check
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
        text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text
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
# Main
# =========================
def main():
    article = get_news()
    if not article:
        print("No new articles to post.")
        return

    print(f"Generating post for: {article['title']}")

    # تنزيل الصورة الأصلية إذا موجودة وصالحة
    image_ok = False
    if article.get("image"):
        image_ok = download_image(article["image"])
        if image_ok and not validate_image():
            image_ok = False

    # إذا ما نجحتش → صورة احتياطية حسب الموضوع
    if not image_ok:
        topic = get_topic(article["title"])
        backup_image = random.choice(IMAGE_LIBRARY.get(topic, IMAGE_LIBRARY["default"]))
        print(f"Using backup image for topic '{topic}': {backup_image}")
        image_ok = download_image(backup_image)
        if not image_ok:
            print("No image to post, aborting...")
            return

    # توليد المنشور بالدارجة
    post_text = generate_post(article["title"])
    if not post_text:
        print("Failed to generate post text")
        return

    # نشر على فيسبوك
    print("Posting to Facebook...")
    res = post_to_facebook(post_text)
    print("Facebook response:", res)

    # حفظ الخبر
    posted_news[article["link"]] = True
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(posted_news, f, ensure_ascii=False, indent=2)
    print(f"✅ تم حفظ الخبر بنجاح")

    # تنظيف الصورة المؤقتة
    try:
        os.remove(TEMP_IMAGE)
    except:
        pass

if __name__ == "__main__":
    main()
