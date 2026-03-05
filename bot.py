import os
import requests
import random
import json
import hashlib
from io import BytesIO
from PIL import Image

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

HISTORY_FILE = "history.json"
REPLIED_FILE = "replied_comments.json"


# مواضيع تقنية ترند
TRENDING_TOPICS = [
    "Cybersecurity",
    "Artificial Intelligence",
    "Linux",
    "Programming",
    "Cloud Computing",
    "Ethical Hacking",
    "Network Security",
    "Data Science",
    "DevOps",
    "Machine Learning",
]


# تحميل التاريخ
def load_history():

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)

    return {"topics": [], "images": []}


def save_history(data):

    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)


# اختيار موضوع بدون تكرار
def get_trending_topic():

    history = load_history()

    available = [t for t in TRENDING_TOPICS if t not in history["topics"]]

    if not available:
        history["topics"] = []
        available = TRENDING_TOPICS

    topic = random.choice(available)

    history["topics"].append(topic)

    save_history(history)

    print("Trending keyword:", topic)

    return topic


# كتابة المنشور
def generate_post(keyword):

    templates = [

f"""🚀 جديد في عالم التقنية!

اليوم غنهضرو على: {keyword}

هاد المجال ولى مهم بزاف فالعالم الرقمي، وكيستعملوه الشركات الكبرى باش يطورو الأنظمة ديالهم ويحسنو الأمان والأداء.

📚 التعلم ديالو ممكن يفتح فرص عمل كثيرة خصوصاً فمجال التكنولوجيا.

💬 السؤال ليك:
شنو رأيك فهاد المجال؟ واش كتشوفو مهم فالمستقبل؟

#Technology
#Tech
#Programming
#Innovation
""",

f"""💡 واش سمعت قبل على {keyword} ؟

هاد المجال ولى واحد من أكثر المجالات لي كيتطورو بسرعة فالعالم.

الشركات التقنية العالمية كتستثمر فيه بزاف حيث كيعاون فبناء حلول ذكية ومتطورة.

👨‍💻 بزاف ديال المطورين والمهندسين بداو كيتعلموه باش يطورو المسار المهني ديالهم.

💬 واش ممكن تفكر تتعلم هاد المجال؟

#AI
#Technology
#Digital
#Future
""",

f"""🌍 عالم التكنولوجيا كيتبدل بسرعة!

واحد من المجالات لي ولى عندو اهتمام كبير هو: {keyword}

هاد التقنية كتدخل فبزاف ديال المجالات بحال الأمن المعلوماتي، البرمجة، وتحليل البيانات.

📈 المستقبل ديال التكنولوجيا غادي يكون مرتبط بزاف بهاد التقنيات.

💬 شنو رأيك فهاد التطور؟

#TechNews
#Technology
#Innovation
#Programming
"""
]

    return random.choice(templates)


# تحميل صورة من Picsum
def download_image(keyword):

    history = load_history()

    for i in range(10):

        url = f"https://picsum.photos/seed/{keyword}{random.randint(1,10000)}/1080"

        try:

            r = requests.get(url, timeout=15)

            img = Image.open(BytesIO(r.content))

            hash_img = hashlib.md5(r.content).hexdigest()

            if hash_img in history["images"]:
                continue

            img.save("temp.jpg")

            history["images"].append(hash_img)

            save_history(history)

            print("Image downloaded")

            return True

        except:
            pass

    return False


# نشر في فيسبوك
def post_to_facebook(message):

    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"

    files = {
        "source": open("temp.jpg", "rb")
    }

    data = {
        "caption": message,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }

    r = requests.post(url, files=files, data=data)

    print("Facebook response:", r.json())


# الرد على التعليقات
def reply_to_comments():

    if os.path.exists(REPLIED_FILE):

        with open(REPLIED_FILE) as f:
            replied = json.load(f)

    else:
        replied = []

    posts_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/posts?access_token={FB_PAGE_ACCESS_TOKEN}"

    posts = requests.get(posts_url).json()

    for post in posts.get("data", []):

        comments_url = f"https://graph.facebook.com/v19.0/{post['id']}/comments?access_token={FB_PAGE_ACCESS_TOKEN}"

        comments = requests.get(comments_url).json()

        for comment in comments.get("data", []):

            if comment["id"] in replied:
                continue

            reply = random.choice([
                "شكراً على التعليق ديالك 🙏",
                "ملاحظة جميلة 👍",
                "شكراً على التفاعل ❤️",
                "رأي محترم 👌"
            ])

            reply_url = f"https://graph.facebook.com/v19.0/{comment['id']}/comments"

            requests.post(reply_url, data={
                "message": reply,
                "access_token": FB_PAGE_ACCESS_TOKEN
            })

            replied.append(comment["id"])

    with open(REPLIED_FILE, "w") as f:
        json.dump(replied, f)


# تشغيل البوت
def run_bot():

    print("Starting bot...")

    keyword = get_trending_topic()

    message = generate_post(keyword)

    print("Generating image...")

    if not download_image(keyword):

        print("Failed to download image")

        return

    print("Posting to Facebook...")

    post_to_facebook(message)

    print("Replying to comments...")

    reply_to_comments()

    print("Done!")


if __name__ == "__main__":
    run_bot()
