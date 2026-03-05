import os
import requests
import random
import json
import time

# -----------------------
# إعدادات البوت
# -----------------------
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

TEMP_IMAGE = "temp.jpg"
HISTORY_FILE = "history.json"
REPLIED_COMMENTS_FILE = "replied_comments.json"

# -----------------------
# التعامل مع ملفات JSON
# -----------------------
def load_json(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

# -----------------------
# توليد محتوى المنشور
# -----------------------
def generate_content():
    used_topics = load_json(HISTORY_FILE)
    topics = [
        "cybersecurity",
        "wifi security",
        "computer networks",
        "linux tips",
        "ethical hacking",
        "data protection",
        "phishing attacks",
        "dark web",
        "password security"
    ]
    available = [t for t in topics if t not in used_topics]
    if not available:
        available = topics
    topic = random.choice(available)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
أنت خبير في التكنولوجيا والأمن المعلوماتي.

اكتب منشوراً تقنياً **بالدارجة المغربية** حول {topic}.

القواعد:
- ابدأ مباشرة في الشرح
- استعمل أسلوب مبسط مع بعض الإيموجيات 💻🔐
- قدم مثال عملي أو نصيحة
- اختم بسؤال تحفيزي 🤔

في آخر سطر اكتب:
IMAGE_KEYWORD: كلمة انجليزية تمثل موضوع الصورة
"""

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        r = requests.post(url, json=data)
        res = r.json()
        text = res["candidates"][0]["content"]["parts"][0]["text"]
        if "IMAGE_KEYWORD:" in text:
            content, keyword = text.split("IMAGE_KEYWORD:")
        else:
            content, keyword = text, topic
    except Exception as e:
        print(f"Error generating content: {e}")
        content, keyword = "منشور تجريبي بالدارجة المغربية", topic

    used_topics.append(topic)
    save_json(HISTORY_FILE, used_topics)

    return content.strip(), keyword.strip()

# -----------------------
# تحميل الصورة
# -----------------------
def download_image(keyword):
    url = f"https://source.unsplash.com/1080x1080/?{keyword},technology"
    try:
        r = requests.get(url)
        with open(TEMP_IMAGE, "wb") as f:
            f.write(r.content)
    except Exception as e:
        print(f"Error downloading image: {e}")

# -----------------------
# نشر المنشور على فيسبوك
# -----------------------
def post_to_facebook(message):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    try:
        with open(TEMP_IMAGE, "rb") as img:
            files = {"source": img}
            data = {"caption": message, "access_token": FB_PAGE_ACCESS_TOKEN}
            r = requests.post(url, data=data, files=files)
            print("Facebook response:", r.json())
    except Exception as e:
        print(f"Error posting to Facebook: {e}")

# -----------------------
# الرد التلقائي على التعليقات
# -----------------------
def reply_to_comments():
    replied = load_json(REPLIED_COMMENTS_FILE)
    try:
        feed_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed?access_token={FB_PAGE_ACCESS_TOKEN}"
        posts = requests.get(feed_url).json().get("data", [])
        for post in posts:
            post_id = post["id"]
            comments_url = f"https://graph.facebook.com/v19.0/{post_id}/comments?access_token={FB_PAGE_ACCESS_TOKEN}"
            comments = requests.get(comments_url).json().get("data", [])
            for c in comments:
                comment_id = c["id"]
                if comment_id in replied:
                    continue
                message = random.choice([
                    "شكراً على تعليقك 🙏",
                    "مرحبا بك في الصفحة 💻",
                    "تابعنا للمزيد من المعلومات التقنية 🔐"
                ])
                reply_url = f"https://graph.facebook.com/v19.0/{comment_id}/comments"
                data = {"message": message, "access_token": FB_PAGE_ACCESS_TOKEN}
                requests.post(reply_url, data=data)
                replied.append(comment_id)
        save_json(REPLIED_COMMENTS_FILE, replied)
    except Exception as e:
        print(f"Error replying to comments: {e}")

# -----------------------
# تشغيل البوت
# -----------------------
def main():
    print("Generating content...")
    content, keyword = generate_content()
    print("Keyword:", keyword)
    print("Downloading image...")
    download_image(keyword)
    print("Posting to Facebook...")
    post_to_facebook(content)
    print("Replying to comments...")
    reply_to_comments()
    if os.path.exists(TEMP_IMAGE):
        os.remove(TEMP_IMAGE)
    print("Done!")

if __name__ == "__main__":
    main()
