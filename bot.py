import os
import random
import json
import requests
from io import BytesIO
from PIL import Image

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

# روابط الصور الحقيقية لكل موضوع (زيادة عدد الروابط لتقليل التكرار)
IMAGES = {
    "Artificial Intelligence": [
        "https://cdn.pixabay.com/photo/2017/07/10/15/04/artificial-intelligence-2495506_1280.jpg",
        "https://cdn.pixabay.com/photo/2020/04/28/21/11/artificial-intelligence-5103689_1280.jpg",
        "https://cdn.pixabay.com/photo/2019/09/25/10/05/ai-4503604_1280.jpg",
        "https://cdn.pixabay.com/photo/2018/01/18/07/09/artificial-3089735_1280.jpg"
    ],
    "Cybersecurity": [
        "https://cdn.pixabay.com/photo/2019/07/29/10/47/cyber-4368792_1280.jpg",
        "https://cdn.pixabay.com/photo/2018/08/07/18/14/hacker-3584824_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/06/20/18/27/cyber-security-2421284_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/01/10/19/05/hacker-1968687_1280.jpg"
    ],
    "Programming": [
        "https://cdn.pixabay.com/photo/2015/05/31/12/14/programming-791298_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/08/10/03/49/computer-2617543_1280.jpg",
        "https://cdn.pixabay.com/photo/2014/05/02/21/50/code-336583_1280.jpg"
    ],
    "Linux": [
        "https://cdn.pixabay.com/photo/2017/05/10/19/19/ubuntu-2306804_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/08/10/03/48/linux-2617542_1280.jpg"
    ],
    "Cloud Computing": [
        "https://cdn.pixabay.com/photo/2018/03/01/12/32/data-3190378_1280.jpg",
        "https://cdn.pixabay.com/photo/2019/07/08/10/57/server-4320051_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/08/07/10/52/cloud-2602832_1280.jpg"
    ],
    "Data Science": [
        "https://cdn.pixabay.com/photo/2018/03/06/22/16/data-3205577_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/10/11/17/24/data-2838920_1280.jpg",
        "https://cdn.pixabay.com/photo/2016/11/29/09/32/data-1869306_1280.jpg"
    ],
    "Ethical Hacking": [
        "https://cdn.pixabay.com/photo/2017/01/10/19/05/hacker-1968687_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/03/21/19/03/hacker-2168230_1280.jpg",
        "https://cdn.pixabay.com/photo/2016/11/29/03/48/robot-1869237_1280.jpg"
    ],
    "Web Development": [
        "https://cdn.pixabay.com/photo/2015/01/08/18/30/web-593359_1280.jpg",
        "https://cdn.pixabay.com/photo/2016/10/28/22/20/web-1779994_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/08/10/03/48/programming-2617541_1280.jpg"
    ],
    "Automation": [
        "https://cdn.pixabay.com/photo/2016/11/29/03/48/robot-1869237_1280.jpg",
        "https://cdn.pixabay.com/photo/2016/10/31/22/53/robotic-1782352_1280.jpg",
        "https://cdn.pixabay.com/photo/2017/01/12/21/20/factory-1971917_1280.jpg"
    ]
}

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
    available = [t for t in TOPICS if t not in history["topics"]]
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

💬 واش عندك تجربة مع {topic}؟ شاركنا فالكومنت!
"""

# تحميل صورة صالحة
def get_image(topic):
    history = load_history()
    possible_images = IMAGES.get(topic, [])
    random.shuffle(possible_images)
    
    for img_url in possible_images:
        if img_url in history["images"]:
            continue
        try:
            r = requests.get(img_url, timeout=10)
            img = Image.open(BytesIO(r.content))
            img.verify()
            img = Image.open(BytesIO(r.content))
            img.save("post_image.jpg")
            history["images"].append(img_url)
            save_history(history)
            return "post_image.jpg"
        except:
            continue
    
    # صورة احتياطية عامة
    fallback_url = "https://cdn.pixabay.com/photo/2015/01/08/18/30/technology-593358_1280.jpg"
    try:
        r = requests.get(fallback_url, timeout=10)
        img = Image.open(BytesIO(r.content))
        img.save("post_image.jpg")
        return "post_image.jpg"
    except:
        return None

# نشر على فيسبوك
def post_to_facebook(text, image_file):
    url = f"https://graph.facebook.com/{PAGE_ID}/photos"
    with open(image_file, "rb") as img:
        payload = {"caption": text, "access_token": PAGE_TOKEN}
        files = {"source": img}
        r = requests.post(url, data=payload, files=files)
        print(r.json())

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

if __name__ == "__main__":
    run_bot()
