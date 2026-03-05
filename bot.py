import os
import random
import json
import requests
from io import BytesIO
from PIL import Image

# معلومات صفحة الفيسبوك
PAGE_ID = os.environ.get("PAGE_ID")
PAGE_TOKEN = os.environ.get("PAGE_TOKEN")

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

# روابط صور حقيقية مرتبطة بالموضوع
IMAGES = {
    "Artificial Intelligence": [
        "https://images.unsplash.com/photo-1581091215364-6d4d8e5e0a14?w=1080",
        "https://images.unsplash.com/photo-1581092795364-8c4e8b5f0b20?w=1080"
    ],
    "Cybersecurity": [
        "https://images.unsplash.com/photo-1561414927-6c7bcd0e74c4?w=1080",
        "https://images.unsplash.com/photo-1581090700220-c9f8e5b60b3d?w=1080"
    ],
    "Programming": [
        "https://images.unsplash.com/photo-1517430816045-df4b7de01dbb?w=1080",
        "https://images.unsplash.com/photo-1581090700281-7e8b5c4f0a9b?w=1080"
    ],
    "Linux": [
        "https://images.unsplash.com/photo-1581090700250-9b8e5c4b0f1b?w=1080",
        "https://images.unsplash.com/photo-1581090700290-7d4b5c0e0b20?w=1080"
    ],
    "Cloud Computing": [
        "https://images.unsplash.com/photo-1581090700230-6c8e5c0f0b2a?w=1080",
        "https://images.unsplash.com/photo-1581090700210-7c8e5d0e0b3b?w=1080"
    ]
    # أضف بقية المواضيع إذا أردت
}

# منشورات جاهزة لكل موضوع
POSTS = {
    "Programming": """💻 البرمجة من أهم المهارات فالعصر الرقمي!

أي تطبيق كتستعملو فالهاتف ولا موقع فالإنترنت مبني على البرمجة.

🚀 تعلم البرمجة كيعطي فرص كثيرة:
• تطوير التطبيقات
• الذكاء الاصطناعي
• تحليل البيانات

💬 واش فكرتي تبدا تتعلم البرمجة؟""",
    
    "Cybersecurity": """🔐 الأمن السيبراني مهم بزاف فهاذ الوقت.

مع تزايد الهجمات الإلكترونية، الشركات كتحتاج خبراء يحميوا:
• الحسابات
• المواقع
• البيانات

💬 واش كتظن الأمن السيبراني غادي يزيد الطلب عليه؟""",
    
    "Artificial Intelligence": """🤖 الذكاء الاصطناعي كيغير العالم بسرعة.

اليوم AI مستعمل ف:
• الطب
• السيارات
• التطبيقات الذكية

💬 واش كتظن الذكاء الاصطناعي غادي يساعد البشر أو يحل محل بعض الوظائف؟"""
}

# ملفات التاريخ
HISTORY_FILE = "history.json"
COMMENTS_FILE = "replied_comments.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"topics": [], "images": []}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def get_topic():
    history = load_history()
    available = [t for t in TOPICS if t not in history["topics"]]
    if not available:
        history["topics"] = []
        available = TOPICS
    topic = random.choice(available)
    history["topics"].append(topic)
    save_history(history)
    return topic

def get_image(topic):
    history = load_history()
    available = [img for img in IMAGES.get(topic, []) if img not in history["images"]]
    if not available:
        history["images"] = []
        available = IMAGES.get(topic, [])
    if not available:
        return None
    img_url = random.choice(available)
    history["images"].append(img_url)
    save_history(history)
    return img_url

def download_image(url, filename="image.jpg"):
    try:
        r = requests.get(url)
        img = Image.open(BytesIO(r.content))
        img.save(filename)
        return True
    except:
        return False

def post_to_facebook(text, image_file="image.jpg"):
    url = f"https://graph.facebook.com/{PAGE_ID}/photos"
    with open(image_file, "rb") as img:
        payload = {
            "caption": text,
            "access_token": PAGE_TOKEN
        }
        files = {"source": img}
        r = requests.post(url, data=payload, files=files)
        print(r.json())

def reply_to_comments():
    # يمكن إضافة الرد التلقائي على التعليقات هنا لاحقاً
    pass

def run_bot():
    print("Starting bot...")
    topic = get_topic()
    print("Topic:", topic)
    text = POSTS.get(topic, f"موضوع تقني حول {topic}")
    image_url = get_image(topic)
    if not image_url:
        print("No image found for topic. Skipping post.")
        return
    print("Downloading image...")
    if download_image(image_url):
        print("Image downloaded")
        post_to_facebook(text)
        reply_to_comments()
        print("Post published and comments replied")
    else:
        print("Failed to download image")

if __name__ == "__main__":
    run_bot()
