import os
import random
import json
import requests
from io import BytesIO
from PIL import Image
import time

# إعدادات صفحة فيسبوك
PAGE_ID = os.environ.get("PAGE_ID")
PAGE_TOKEN = os.environ.get("PAGE_TOKEN")

# ملفات التاريخ
HISTORY_FILE = "history.json"

# المواضيع التقنية
TOPICS = [
    "Artificial Intelligence",
    "Cybersecurity",
    "Programming",
    "Linux",
    "Cloud Computing",
    "Data Science",
    "Ethical Hacking",
    "Web Development",
    "Automation"
]

# تحميل وحفظ التاريخ
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"topics": [], "images": []}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

# اختيار موضوع جديد
def get_topic():
    history = load_history()
    available = [t for t in TOPICS if t not in history.get("topics", [])]
    if not available:
        history["topics"] = []
        available = TOPICS
    topic = random.choice(available)
    history["topics"].append(topic)
    save_history(history)
    return topic

# توليد المنشور
def generate_post(topic):
    return f"""
📌 موضوع اليوم: {topic}

هاذ الموضوع مهم بزاف في العالم التقني. غادي نشارك معاكم أهم النقاط بطريقة مبسطة:

• شرح مفهوم {topic} بطريقة مفهومة للجميع.
• كيفاش يمكن تستعملو فحياتك اليومية أو العمل.
• نصائح مهمة واحترافية لتحسين مهاراتك في {topic}.

💬 واش عندك تجربة مع {topic}? شاركنا فالكومنت!
"""

# تحميل صورة من Unsplash Source API بطريقة مضمونة
def get_image(topic):
    history = load_history()
    # الكلمات المفتاحية القصيرة لضمان التحميل
    keywords = [topic.replace(" ", "+"), "technology", "computer", "AI"]
    random.shuffle(keywords)
    
    for kw in keywords:
        url = f"https://source.unsplash.com/1080x1080/?{kw}"
        if url in history["images"]:
            continue
        try:
            r = requests.get(url, timeout=10)
            img = Image.open(BytesIO(r.content))
            img.save("post_image.jpg")
            history["images"].append(url)
            save_history(history)
            return "post_image.jpg"
        except Exception as e:
            print(f"Attempt failed for {url}: {e}")
            continue

    # fallback مضمون
    fallback_url = "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1080"
    r = requests.get(fallback_url, timeout=10)
    img = Image.open(BytesIO(r.content))
    img.save("post_image.jpg")
    return "post_image.jpg"

# نشر على فيسبوك
def post_to_facebook(text, image_file):
    url = f"https://graph.facebook.com/{PAGE_ID}/photos"
    try:
        with open(image_file, "rb") as img:
            payload = {"caption": text, "access_token": PAGE_TOKEN}
            files = {"source": img}
            r = requests.post(url, data=payload, files=files)
            print(r.json())
    except Exception as e:
        print(f"Error posting to Facebook: {e}")

# الرد على التعليقات (يمكن تطوير لاحق)
def reply_to_comments():
    pass

# تشغيل البوت 3 مرات يومياً
def run_bot():
    for _ in range(3):
        topic = get_topic()
        print("Topic:", topic)
        text = generate_post(topic)
        image_file = get_image(topic)
        if not image_file:
            print("Critical: Could not download a valid image. Aborting post.")
            continue
        print("Image downloaded:", image_file)
        post_to_facebook(text, image_file)
        reply_to_comments()
        print("Post published and comments replied\n")
        time.sleep(2)  # تأخير صغير بين المنشورات

if __name__ == "__main__":
    print("Starting bot...")
    run_bot()
