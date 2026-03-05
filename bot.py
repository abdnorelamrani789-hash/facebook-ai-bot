import os
import requests
import random
import json
import hashlib
from io import BytesIO
from PIL import Image
from pytrends.request import TrendReq

# -----------------------
# إعدادات البوت
# -----------------------
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

TEMP_IMAGE = "temp.jpg"
HISTORY_FILE = "history.json"
REPLIED_COMMENTS_FILE = "replied_comments.json"
USED_IMAGES_FILE = "used_images.json"

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
# جلب مواضيع الترند التقنية
# -----------------------
def get_trending_keyword():
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        trending = pytrends.trending_searches(pn='morocco')  # يمكن تغيير الدولة
        # اختيار مواضيع مرتبطة بالتقنية
        tech_trends = [t for t in trending[0:20] if any(k in t.lower() for k in ['tech', 'ai', 'cyber', 'linux', 'computer'])]
        keyword = random.choice(tech_trends) if tech_trends else "technology"
        return keyword
    except Exception as e:
        print(f"Error fetching trending topics: {e}")
        return "technology"

# -----------------------
# توليد محتوى المنشور
# -----------------------
def generate_content(keyword):
    used_topics = load_json(HISTORY_FILE)
    if keyword in used_topics:
        print(f"Keyword {keyword} already used, picking random fallback")
        keyword = random.choice(["cybersecurity", "linux tips", "data protection", "ethical hacking"])
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
أنت خبير في التكنولوجيا والأمن المعلوماتي.

اكتب منشوراً **بالدارجة المغربية** حول {keyword}.

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
            parts = text.split("IMAGE_KEYWORD:")
            content = "".join(parts[:-1]).strip()
            img_keyword = parts[-1].strip()
        else:
            content, img_keyword = text, keyword
    except Exception as e:
        print(f"Error generating content: {e}")
        content, img_keyword = f"منشور عن {keyword} بالدارجة المغربية", keyword

    used_topics.append(keyword)
    save_json(HISTORY_FILE, used_topics)
    return content, img_keyword

# -----------------------
# حساب hash الصورة
# -----------------------
def get_image_hash(img_path):
    with open(img_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# -----------------------
# تحميل الصورة مع fallback + منع التكرار
# -----------------------
def download_image(keyword):
    used_hashes = load_json(USED_IMAGES_FILE)
    urls = [
        f"https://source.unsplash.com/1080x1080/?{keyword},technology",
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1080"  # fallback
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=15)
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img.save(TEMP_IMAGE, format="JPEG")
            img_hash = get_image_hash(TEMP_IMAGE)
            if img_hash in used_hashes:
                print("Image already used! Trying next option...")
                continue
            used_hashes.append(img_hash)
            save_json(USED_IMAGES_FILE, used_hashes)
            print(f"Image downloaded successfully from {url}")
            return
        except Exception as e:
            print(f"Failed to download image from {url}: {e}")
    print("No new image could be downloaded. The post will be text only.")

# -----------------------
# نشر المنشور على فيسبوك
# -----------------------
def post_to_facebook(message):
    if not os.path.exists(TEMP_IMAGE):
        print("No image file found, posting text only.")
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
        data = {"message": message, "access_token": FB_PAGE_ACCESS_TOKEN}
        r = requests.post(url, data=data)
        print("Facebook response:", r.json())
        return
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
def reply_to_comments(force=False):
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
                if not force and comment_id in replied:
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
    print("Fetching trending keyword...")
    keyword = get_trending_keyword()
    print("Trending keyword:", keyword)

    print("Generating content...")
    content, img_keyword = generate_content(keyword)
    print("Image keyword:", img_keyword)

    print("Downloading image...")
    download_image(img_keyword)

    print("Posting to Facebook...")
    post_to_facebook(content)

    print("Replying to comments (force old comments)...")
    reply_to_comments(force=True)

    if os.path.exists(TEMP_IMAGE):
        os.remove(TEMP_IMAGE)

    print("Done!")

if __name__ == "__main__":
    main()
