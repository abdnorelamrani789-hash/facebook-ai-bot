import os
import requests
import json

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

TEMP_IMAGE = "news_image.jpg"
POSTED_FILE = "posted_news.json"
PLACEHOLDER_IMAGE_URL = "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg"

# =========================
# Load/Save posted news
# =========================
def load_posted_news():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r") as f:
            return json.load(f)
    return []

def save_posted_news(posted):
    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f)

# =========================
# Get trending tech news
# =========================
def get_trending_news():
    url = "https://newsapi.org/v2/top-headlines"
    params = {"category": "technology", "language": "en", "pageSize": 20, "apiKey": NEWS_API_KEY}
    r = requests.get(url, params=params, timeout=20)
    data = r.json()
    if "articles" not in data:
        return None
    posted = load_posted_news()
    for article in data["articles"]:
        if article["url"] not in posted:
            return {
                "title": article["title"],
                "description": article["description"] or "",
                "url": article["url"],
                "image": article.get("urlToImage")
            }
    return None

# =========================
# Download image
# =========================
def download_image(url):
    try:
        img = requests.get(url, timeout=30)
        with open(TEMP_IMAGE, "wb") as f:
            f.write(img.content)
        return True
    except:
        return False

# =========================
# Post to Facebook
# =========================
def post_to_facebook(text):
    try:
        fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        with open(TEMP_IMAGE, "rb") as img:
            payload = {"caption": text, "access_token": FB_PAGE_ACCESS_TOKEN}
            files = {"source": img}
            r = requests.post(fb_url, data=payload, files=files, timeout=30)
            return r.json()
    except Exception as e:
        print("Facebook post error:", e)
        return None

# =========================
# Generate post text in Darija
# =========================
def generate_post_text(article):
    # هنا نولدو النص مباشرة بالدارجة المغربية
    # Hook + شرح + إيموجيات + سؤال + hashtags
    text = f"""
💥 {article['title']}

واخا كان البعض متوقع، دابا الأمور واضحة: {article['description']}

🎮💻🤔 واش هاد الخبر غادي يعجبكم ولا غادي يخلّيكم تشوفوا بدائل؟

#TechNews #التقنية #أخبار_التكنولوجيا #MoroccoTech
"""
    return text.strip()

# =========================
# Main
# =========================
def main():
    article = get_trending_news()
    if not article:
        print("No new article found")
        return

    content = generate_post_text(article)

    # تنزيل الصورة الأصلية، fallback للـ placeholder إذا ما كانتش موجودة
    if not article.get("image") or not download_image(article["image"]):
        print("Using placeholder image...")
        download_image(PLACEHOLDER_IMAGE_URL)

    print("Posting to Facebook...")
    result = post_to_facebook(content)
    print("Facebook response:", result)

    # سجل الخبر لتجنب التكرار
    posted = load_posted_news()
    posted.append(article["url"])
    save_posted_news(posted)

if __name__ == "__main__":
    main()
