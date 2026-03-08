import os
import json
import requests
import feedparser
from google import genai

# =========================
# إعداد مفاتيح البيئة
# =========================
FACEBOOK_PAGE_ID = os.getenv("FB_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise Exception("Missing required environment variables")

client = genai.Client(api_key=GEMINI_API_KEY)
POSTED_FILE = "posted_news.json"

# =========================
# تحميل الأخبار المنشورة
# =========================
def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r") as f:
            return json.load(f)
    return []

def save_posted(url):
    posted = load_posted()
    posted.append(url)
    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f)

# =========================
# جلب الأخبار من RSS
# =========================
def get_news():
    feeds = [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.engadget.com/rss.xml"
    ]

    posted = load_posted()

    for feed_url in feeds:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            link = entry.link
            if link not in posted:
                title = entry.title
                desc = entry.summary if "summary" in entry else ""
                image = None
                if "media_content" in entry:
                    image = entry.media_content[0]["url"]
                elif "media_thumbnail" in entry:
                    image = entry.media_thumbnail[0]["url"]
                return {
                    "title": title,
                    "desc": desc,
                    "url": link,
                    "image": image
                }
    return None

# =========================
# توليد منشور احترافي بالدارجة
# =========================
def generate_post(article):
    prompt = f"""
أنت خبير في صياغة محتوى فايسبوك تقني.  

اكتب منشور احترافي **بالدارجة المغربية** حول خبر تقني، بدون أي مقدمة خارجية، وبدون تكرار العنوان.  

القواعد:
- طول المنشور بين 4 و6 أسطر
- استخدم 3 إيموجي تقنية
- أضف سؤال في النهاية لتحفيز التفاعل
- أضف هاشتاغات تقنية مناسبة

العنوان: {article['title']}
الوصف: {article['desc']}
"""

    response = client.chat.completions.create(
        model="gemini-1.5",
        messages=[{"role": "user", "content": prompt}],
        max_output_tokens=500
    )

    return response.choices[0].message.content.strip()

# =========================
# نشر في فايسبوك
# =========================
def post_to_facebook(message, image_url):
    url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/photos"
    payload = {
        "url": image_url,
        "caption": message,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    r = requests.post(url, data=payload)
    print("Facebook response:", r.json())

# =========================
# تشغيل البوت
# =========================
def run():
    article = get_news()
    if not article:
        print("No new news found")
        return

    print("Generating post...")
    post_text = generate_post(article)

    # استخدام صورة الخبر الأصلية أو placeholder
    image_url = article["image"] or "https://via.placeholder.com/1200x630.png?text=Tech+News"

    print("Posting to Facebook...")
    post_to_facebook(post_text, image_url)

    save_posted(article["url"])
    print("Done! News posted and saved.")

if __name__ == "__main__":
    run()
