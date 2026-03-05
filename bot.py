import os
import random
import json
import requests
from io import BytesIO
from PIL import Image
from urllib.parse import quote

# معلومات صفحة الفيسبوك
PAGE_ID = os.environ.get("PAGE_ID")
PAGE_TOKEN = os.environ.get("PAGE_TOKEN")

# قائمة المواضيع التقنية
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

# اختيار موضوع جديد
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

# توليد منشور طويل واحترافي بالدارجة المغربية
def generate_post(topic):
    posts_templates = {
        "Artificial Intelligence": f"""
🤖 الذكاء الاصطناعي ({topic}) كيغير العالم بسرعة!

اليوم AI مستعمل ف:
• الطب: تحليل الصور الطبية وتشخيص الأمراض.
• السيارات: القيادة الذاتية وتقنيات السلامة.
• التطبيقات الذكية: مساعد شخصي، توصيات، وتحسين تجربة المستخدم.

💡 نصيحة: تعلم الأساسيات بحال Python وMachine Learning غادي يعطيك فرص كبيرة فالمستقبل.

💬 واش كتظن الذكاء الاصطناعي غادي يساعد البشر أو يحل محل بعض الوظائف؟
""",
        "Cybersecurity": f"""
🔐 الأمن السيبراني ({topic}) مهم بزاف فهاذ الوقت.

مع تزايد الهجمات الإلكترونية، الشركات كتحتاج خبراء يحميوا:
• الحسابات والمعلومات الشخصية.
• المواقع الإلكترونية.
• بيانات الشركات الحساسة.

💡 نصيحة: استعمال كلمات سر قوية وتفعيل المصادقة الثنائية (2FA) كيحميك من كثير من المشاكل.

💬 واش كتظن الأمن السيبراني غادي يزيد الطلب عليه؟
""",
        "Programming": f"""
💻 البرمجة ({topic}) من أهم المهارات فالعصر الرقمي!

أي تطبيق كتستعملو فالهاتف ولا موقع فالإنترنت مبني على البرمجة.

🚀 تعلم البرمجة كيعطي فرص كثيرة:
• تطوير التطبيقات.
• الذكاء الاصطناعي.
• تحليل البيانات.

💡 نصيحة: Python وJavaScript هما البداية الممتازة لأي مبتدئ.

💬 واش فكرتي تبدا تتعلم البرمجة؟
"""
    }
    return posts_templates.get(topic, f"موضوع تقني حول {topic} بطريقة مفهومة للجميع.")

# البحث عن صورة حقيقية مناسبة من Pixabay/Unsplash
def get_image(topic):
    search_keywords = [
        topic,
        topic + " technology",
        topic + " computer",
        topic + " AI" if topic=="Artificial Intelligence" else topic
    ]
    history = load_history()
    for keyword in search_keywords:
        query = quote(keyword)
        url = f"https://source.unsplash.com/1080x1080/?{query}"
        try:
            r = requests.get(url, timeout=15)
            img = Image.open(BytesIO(r.content))
            if img.format in ["JPEG", "PNG", "JPG"]:
                # تحقق من عدم تكرار الصورة
                if url not in history["images"]:
                    history["images"].append(url)
                    save_history(history)
                    img.save("post_image.jpg")
                    return "post_image.jpg"
        except:
            continue
    return None

def post_to_facebook(text, image_file):
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
    # يمكن إضافة الرد التلقائي على التعليقات لاحقاً
    pass

def run_bot():
    print("Starting bot...")
    topic = get_topic()
    print("Topic:", topic)
    text = generate_post(topic)
    image_file = get_image(topic)
    if not image_file:
        print("Critical: Could not download a valid image. Aborting post.")
        return
    print("Image downloaded:", image_file)
    post_to_facebook(text, image_file)
    reply_to_comments()
    print("Post published and comments replied")

if __name__ == "__main__":
    run_bot()
