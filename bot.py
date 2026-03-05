import os
import requests
import urllib.parse
import time
import random
from datetime import datetime

# ========================
# ENV VARIABLES
# ========================

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

TEMP_IMAGE = "temp_image.jpg"

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise Exception("Missing environment variables")


# ========================
# DAILY TOPICS
# ========================

TOPICS = [
    "cybersecurity",
    "computer networks",
    "linux",
    "ethical hacking",
    "internet safety",
    "wifi security",
    "data protection"
]


# ========================
# GENERATE CONTENT
# ========================

def generate_content():

    topic = random.choice(TOPICS)

    model = "models/gemini-3-flash-preview"

    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
أنت خبير في الأمن المعلوماتي.

اكتب منشوراً احترافياً بالدارجة المغربية حول: {topic}

القواعد:

- ابدأ مباشرة في الشرح
- استعمل أسلوب مبسط
- أضف ايموجي تقنية
- قدم مثال واقعي
- اختم بسؤال لتحفيز التفاعل

في آخر سطر اكتب:

IMAGE_PROMPT: وصف احترافي لصورة تقنية بالإنجليزية
"""

    data = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    try:

        r = requests.post(url, json=data, timeout=30)

        res = r.json()

        text = res["candidates"][0]["content"]["parts"][0]["text"]

        if "IMAGE_PROMPT:" in text:

            content, img_prompt = text.split("IMAGE_PROMPT:", 1)

            return content.strip(), img_prompt.strip()

        return text, "cyber security network technology"

    except Exception as e:

        print("Gemini error:", e)

        return None, None


# ========================
# IMAGE GENERATION
# ========================

def generate_image(prompt):

    encoded = urllib.parse.quote(prompt)

    seed = random.randint(1, 999999)

    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&seed={seed}&nologo=true"

    print("Generating image...")

    for attempt in range(3):

        try:

            print("Attempt:", attempt + 1)

            time.sleep(15)

            r = requests.get(url, timeout=60)

            if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):

                with open(TEMP_IMAGE, "wb") as f:
                    f.write(r.content)

                if validate_image():
                    return True

        except Exception as e:

            print("Image error:", e)

    print("Using fallback image")

    return download_fallback()


# ========================
# FALLBACK IMAGE
# ========================

def download_fallback():

    fallback_images = [
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1080",
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1080",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1080"
    ]

    url = random.choice(fallback_images)

    try:

        r = requests.get(url)

        with open(TEMP_IMAGE, "wb") as f:
            f.write(r.content)

        return True

    except:

        return False


# ========================
# VALIDATE IMAGE
# ========================

def validate_image():

    try:

        with open(TEMP_IMAGE, "rb") as f:
            header = f.read(3)

        return header == b"\xff\xd8\xff"

    except:

        return False


# ========================
# POST TO FACEBOOK
# ========================

def post_to_facebook(message):

    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"

    with open(TEMP_IMAGE, "rb") as img:

        files = {"source": img}

        data = {
            "caption": message,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }

        r = requests.post(url, data=data, files=files)

        return r.json()


# ========================
# MAIN
# ========================

def main():

    print("Starting bot...")

    content, img_prompt = generate_content()

    if not content:

        print("Content generation failed")

        return

    print("Content generated")

    if not generate_image(img_prompt):

        print("Image generation failed")

        return

    print("Posting to Facebook...")

    res = post_to_facebook(content)

    print("Facebook response:")

    print(res)

    try:
        os.remove(TEMP_IMAGE)
    except:
        pass


if __name__ == "__main__":
    main()
