import os
import requests
import urllib.parse
import time
import json
from datetime import datetime, timedelta
import random

# =========================
# Environment Variables
# =========================
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise Exception("Missing required environment variables")

TEMP_IMAGE = "temp_image.jpg"
HISTORY_FILE = "posted_history.json"
REPLIED_FILE = "replied_comments.json"

# =========================
# Load/Save history
# =========================
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# =========================
# Generate Content
# =========================
def generate_content_and_image_prompt():
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"

    prompt = """
أنت خبير في الأمن المعلوماتي والشبكات.

اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة "تقنية بالدارجة".

القواعد:
- ابدأ المنشور مباشرة بدون مقدمة.
- اشرح الفكرة بوضوح وبطريقة مبسطة.
- استعمل تنسيق جيد وفواصل.
- أضف بعض الإيموجي التقنية.
- في النهاية أضف سؤالاً لتحفيز التفاعل.

في آخر سطر أكتب:

IMAGE_PROMPT: وصف إنجليزي لصورة تقنية احترافية متعلقة بالموضوع.
"""

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        res_json = response.json()

        if "candidates" not in res_json:
            print("Gemini API error:", res_json)
            return None, None

        full_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        if "IMAGE_PROMPT:" in full_text:
            text, img_prompt = full_text.split("IMAGE_PROMPT:", 1)
            return text.strip(), img_prompt.strip()

        return full_text.strip(), "cybersecurity network infrastructure digital security"

    except Exception as e:
        print("Gemini Error:", e)
        return None, None

# =========================
# Download Image
# =========================
def download_image(prompt):
    # هنا نستعمل Pexels مباشرة برابط ثابت كبديل مضمون
    # مثال:
    IMAGE_LINKS = [
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg",
        "https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg",
        "https://images.pexels.com/photos/574071/pexels-photo-574071.jpeg"
    ]
    selected = random.choice(IMAGE_LINKS)
    print(f"Downloading image for topic '{prompt}': {selected}")

    try:
        img_res = requests.get(selected, timeout=30)
        with open(TEMP_IMAGE, "wb") as f:
            f.write(img_res.content)
        return True
    except Exception as e:
        print("Image download failed:", e)
        return False

# =========================
# Validate Image
# =========================
def validate_image():
    try:
        with open(TEMP_IMAGE, "rb") as f:
            header = f.read(4)
        if header[:3] == b"\xff\xd8\xff":  # JPEG check
            return True
        print("Invalid JPEG header")
        return False
    except:
        return False

# =========================
# Post to Facebook
# =========================
def post_to_facebook(message):
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    try:
        with open(TEMP_IMAGE, "rb") as img_file:
            files = {"source": ("post.jpg", img_file, "image/jpeg")}
            payload = {"caption": message, "access_token": FB_PAGE_ACCESS_TOKEN}
            response = requests.post(fb_url, data=payload, files=files, timeout=30)
        return response.json()
    except Exception as e:
        print("Facebook API Error:", e)
        return None

# =========================
# Reply to comments
# =========================
def reply_to_comments(post_id):
    replied = load_json(REPLIED_FILE)
    comments_url = f"https://graph.facebook.com/v19.0/{post_id}/comments?access_token={FB_PAGE_ACCESS_TOKEN}"

    try:
        res = requests.get(comments_url, timeout=30).json()
        for comment in res.get("data", []):
            c_id = comment["id"]
            if c_id in replied:
                continue
            reply_msg = "شكراً على تعليقك! 🌟"
            reply_url = f"https://graph.facebook.com/v19.0/{c_id}/comments"
            requests.post(reply_url, data={"message": reply_msg, "access_token": FB_PAGE_ACCESS_TOKEN})
            replied[c_id] = datetime.now().isoformat()
        save_json(REPLIED_FILE, replied)
    except Exception as e:
        print("Error replying to comments:", e)

# =========================
# Main Bot Loop
# =========================
def run_bot():
    history = load_json(HISTORY_FILE)
    posted_today = history.get(str(datetime.today().date()), [])

    while len(posted_today) < 3:  # 3 منشورات يومياً
        print(f"\nGenerating post {len(posted_today)+1} for today...")
        content, img_prompt = generate_content_and_image_prompt()
        if not content:
            print("Failed to generate content")
            break

        if not download_image(img_prompt) or not validate_image():
            print("Image download/validation failed, skipping post")
            continue

        fb_result = post_to_facebook(content)
        print("Facebook response:", fb_result)

        if fb_result and "id" in fb_result:
            post_id = fb_result["id"]
            reply_to_comments(post_id)
            posted_today.append(post_id)

        # انتظر 4 ساعات تقريباً بين كل منشور
        time.sleep(4 * 60 * 60)

    # حفظ التاريخ
    history[str(datetime.today().date())] = posted_today
    save_json(HISTORY_FILE, history)
    print("All posts done for today!")

# =========================
# Run
# =========================
if __name__ == "__main__":
    print("Starting bot...")
    run_bot()
