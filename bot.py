import os
import requests
import json
import time

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

TEMP_IMAGE = "ai_news.jpg"
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
        if article["url"] not in posted:
            return {
                "title": article["title"],
                "description": article["description"] or "",
                "url": article["url"],
                "image": article.get("urlToImage")
            }
    return None

# =========================
# Gemini generate content + image prompt
# =========================
def generate_content_and_image(article):
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"

    # برومت واضح، مباشر، بدون مقدمة زائدة، مع Hook + سؤال + hashtags
    prompt = f"""
أنت صانع محتوى تقني محترف. المطلوب كتابة منشور فايسبوك احترافي بالدارجة المغربية حول الخبر التالي:

القواعد:
1. ابدأ النص مباشرة بـ Hook جذاب بدون أي مقدمة خارجية.
2. اجعل المنشور طويل نسبياً، مع شرح الخبر بوضوح ومفصل.
3. أضف 3-4 إيموجي تقنية مناسبة.
4. أضف سؤال في النهاية لتحفيز التفاعل.
5. أضف Hashtags مناسبة في آخر المنشور.
6. أعطيني وصف IMAGE_PROMPT باللغة الإنجليزية لتوليد صورة AI مميزة لكل خبر.

العنوان: {article['title']}
الوصف: {article['description']}

رجاءً أعطني:
- النص النهائي للبوست مباشرة
- IMAGE_PROMPT: وصف باللغة الإنجليزية لصورة AI احترافية متعلقة بالخبر
"""

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        res = r.json()
        full_text = res["candidates"][0]["content"]["parts"][0]["text"]

        # فصل النص عن IMAGE_PROMPT
        if "IMAGE_PROMPT:" in full_text:
            text, img_prompt = full_text.split("IMAGE_PROMPT:", 1)
            return text.strip(), img_prompt.strip()
        return full_text.strip(), article['title']
    except Exception as e:
        print("Gemini API error:", e)
        return article['title'], article['title']

# =========================
# Generate AI image from Gemini prompt
# =========================
def generate_ai_image(prompt):
    try:
        image_url = "https://image.pollinations.ai/prompt/"
        final_url = image_url + prompt.replace(" ", "%20")
        img = requests.get(final_url, timeout=60)
        with open(TEMP_IMAGE, "wb") as f:
            f.write(img.content)
        return True
    except Exception as e:
        print("AI Image generation failed:", e)
        return False

# =========================
# Download image from URL
# =========================
def download_image(url):
    try:
        img = requests.get(url, timeout=30)
        with open(TEMP_IMAGE, "wb") as f:
            f.write(img.content)
        return True
    except Exception as e:
        print("Image download failed:", e)
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

    print("Generating content for:", article["title"])
    content, img_prompt = generate_content_and_image(article)

    print("Generating AI image...")
    ai_success = generate_ai_image(img_prompt)

    if not ai_success:
        print("AI image generation failed, using original article image...")
        if article.get("image") and download_image(article["image"]):
            print("Downloaded original article image.")
        else:
            print("Downloading placeholder image...")
            download_image(PLACEHOLDER_IMAGE_URL)

    print("Posting to Facebook...")
    result = post_to_facebook(content)
    print("Facebook response:", result)

    # Save posted news to avoid duplicates
    posted = load_posted_news()
    posted.append(article["url"])
    save_posted_news(posted)

if __name__ == "__main__":
    main()
