import os
import requests
import random
import json
import feedparser

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
# Load posted news
# =========================
if os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        posted_news = json.load(f)
        # force dict if file contains a list
        if isinstance(posted_news, list):
            posted_news = {}
else:
    posted_news = {}

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
        else:
            raise Exception("Invalid image response")
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
        if header[:3] == b"\xff\xd8\xff":
            return True
        print("Invalid JPEG header")
        return False
    except:
        return False

# =========================
# Gemini Content Generation
# =========================
def generate_post(article_title, article_url, article_image):
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
أنت خبير في التقنية. عندك خبر: "{article_title}".

اكتب منشور احترافي وطويل بالدارجة المغربية لصفحة "تقنية بالدارجة"، بدون مقدمة زايدة.
اشرح الخبر بطريقة مفهومة وبسيطة، استعمل إيموجي تقنية.
في النهاية، ضيف سؤال لتحفيز التفاعل.
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
# Fetch News (RSS example)
# =========================
NEWS_RSS = "https://www.theverge.com/rss/index.xml"  # يمكن تغييره لأي مصدر مفتوح

def get_news():
    feed = feedparser.parse(NEWS_RSS)
    for entry in feed.entries:
        if entry.link not in posted_news:
            # حاول الحصول على صورة إذا كانت موجودة
            image_url = entry.get("media_content", [{}])[0].get("url", "")
            return {
                "title": entry.title,
                "link": entry.link,
                "image": image_url
            }
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

    # تنزيل صورة الخبر الأصلية أولاً
    image_downloaded = False
    if article.get("image"):
        image_downloaded = download_image(article["image"])
        if image_downloaded and not validate_image():
            image_downloaded = False

    # توليد النص
    post_text = generate_post(article["title"], article["link"], article.get("image"))
    if not post_text:
        print("Failed to generate post text")
        return

    # تنزيل صورة placeholder إذا Gemini عطاش صورة خاصة أو صورة الخبر فشلت
    if not image_downloaded:
        print("Using placeholder image...")
        download_image("https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg")

    # نشر على فيسبوك
    print("Posting to Facebook...")
    res = post_to_facebook(post_text)
    print("Facebook response:", res)

    # تسجيل الخبر كمنشور لتجنب التكرار
    posted_news[article["link"]] = True
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(posted_news, f, ensure_ascii=False, indent=2)

    # حذف الصورة المؤقتة
    try:
        os.remove(TEMP_IMAGE)
    except:
        pass

if __name__ == "__main__":
    main()
