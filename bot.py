import os
import requests
import random
import json

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

TEMP_IMAGE = "ai_news.jpg"
POSTED_FILE = "posted_news.json"

# =========================
# Load previously posted news
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
    params = {
        "category": "technology",
        "language": "en",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY
    }
    r = requests.get(url, params=params, timeout=20)
    data = r.json()
    if "articles" not in data:
        print("No articles:", data)
        return None

    posted = load_posted_news()
    for article in data["articles"]:
        if article["url"] not in posted and article.get("urlToImage"):
            return {
                "title": article["title"],
                "description": article["description"] or "",
                "url": article["url"],
                "image": article["urlToImage"]
            }
    return None

# =========================
# Download image
# =========================
def download_image(url):
    try:
        img = requests.get(url, timeout=20)
        with open(TEMP_IMAGE, "wb") as f:
            f.write(img.content)
        return True
    except Exception as e:
        print("Image download failed:", e)
        return False

# =========================
# Gemini summarize & translate
# =========================
def summarize_news(article):
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
أنت صانع محتوى تقني.

المطلوب:
1. اكتب Hook قوي يجذب الانتباه
2. لخص الخبر بالدارجة المغربية
3. اجعل النص مناسب لفايسبوك
4. أضف 2-3 ايموجي تقنية
5. في النهاية ضع سؤال للتفاعل
6. أضف Hashtags مقترحة

العنوان:
{article['title']}

الوصف:
{article['description']}
"""

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        r = requests.post(url, headers=headers, json=data, timeout=30)
        res = r.json()
        text = res["candidates"][0]["content"]["parts"][0]["text"]
        return text
    except Exception as e:
        print("Gemini summarize error:", e)
        return article['title']

# =========================
# Generate AI image
# =========================
def generate_ai_image(prompt):
    try:
        image_url = "https://image.pollinations.ai/prompt/"
        final_url = image_url + prompt.replace(" ", "%20")
        img = requests.get(final_url, timeout=20)
        with open(TEMP_IMAGE, "wb") as f:
            f.write(img.content)
        return True
    except Exception as e:
        print("AI Image generation failed:", e)
        return False

# =========================
# Post to Facebook
# =========================
def post_to_facebook(text):
    try:
        fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        with open(TEMP_IMAGE, "rb") as img:
            payload = {
                "caption": text,
                "access_token": FB_PAGE_ACCESS_TOKEN
            }
            files = {"source": img}
            r = requests.post(fb_url, data=payload, files=files, timeout=30)
            return r.json()
    except Exception as e:
        print("Facebook post error:", e)
        return None

# =========================
# Main
# =========================
def main():
    article = get_trending_news()
    if not article:
        print("No new article found")
        return

    print("Posting news:", article["title"])

    if not download_image(article["image"]):
        print("Downloading original image failed, generating AI image...")
        generate_ai_image(article["title"])

    summary = summarize_news(article)
    result = post_to_facebook(summary)
    print("Facebook response:", result)

    # Save posted news
    posted = load_posted_news()
    posted.append(article["url"])
    save_posted_news(posted)

if __name__ == "__main__":
    main()
