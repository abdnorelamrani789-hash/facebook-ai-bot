import requests
import json
import os
import google.generativeai as genai

NEWS_API_KEY = "NEWS_API_KEY"
FACEBOOK_PAGE_ID = "PAGE_ID"
FACEBOOK_ACCESS_TOKEN = "PAGE_ACCESS_TOKEN"
GEMINI_API_KEY = "GEMINI_API_KEY"

genai.configure(api_key=GEMINI_API_KEY)

POSTED_FILE = "posted_news.json"


# تحميل الأخبار المنشورة
def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r") as f:
            return json.load(f)
    return []


# حفظ خبر منشور
def save_posted(url):
    posted = load_posted()
    posted.append(url)

    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f)


# جلب الأخبار
def get_news():

    url = "https://newsapi.org/v2/everything"

    params = {
        "q": "AI OR Apple OR Google OR Microsoft OR Nvidia OR OpenAI OR Gaming OR Smartphone",
        "language": "en",
        "sortBy": "popularity",
        "pageSize": 20,
        "domains": "techcrunch.com,theverge.com,wired.com",
        "apiKey": NEWS_API_KEY
    }

    r = requests.get(url, params=params)
    data = r.json()

    posted = load_posted()

    for article in data["articles"]:

        if article["url"] not in posted:

            return {
                "title": article["title"],
                "desc": article["description"],
                "url": article["url"],
                "image": article["urlToImage"]
            }

    return None


# توليد منشور
def generate_post(article):

    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
اكتب منشور فايسبوك تقني احترافي بالدارجة المغربية.

القواعد:
- بدون أي مقدمة
- لا تكرر العنوان
- شرح الخبر بطريقة بسيطة
- استعمل 3 ايموجي
- اجعل المنشور بين 4 و 6 أسطر
- أضف سؤال في النهاية لزيادة التفاعل
- أضف هاشتاغات تقنية

العنوان:
{article['title']}

الوصف:
{article['desc']}

اكتب نص المنشور فقط.
"""

    response = model.generate_content(prompt)

    return response.text.strip()


# توليد صورة
def generate_image(title):

    try:

        model = genai.GenerativeModel("gemini-pro-vision")

        prompt = f"create a modern tech news illustration about: {title}"

        result = model.generate_content(prompt)

        if hasattr(result, "image"):
            return result.image

    except:
        pass

    return None


# النشر في فايسبوك
def post_to_facebook(message, image_url):

    url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/photos"

    payload = {
        "url": image_url,
        "caption": message,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }

    r = requests.post(url, data=payload)

    print("Facebook response:", r.json())


# تشغيل البوت
def run():

    article = get_news()

    if not article:
        print("No new news found")
        return

    print("Generating post...")

    post_text = generate_post(article)

    image = generate_image(article["title"])

    if image:
        image_url = image
    else:
        image_url = article["image"]

    print("Posting to Facebook...")

    post_to_facebook(post_text, image_url)

    save_posted(article["url"])


run()
