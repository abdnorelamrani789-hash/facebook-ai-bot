import os
import requests
import random
import time

# =========================
# Environment Variables
# =========================
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise Exception("Missing required environment variables")

TEMP_IMAGE = "temp_image.jpg"

# =========================
# Image Library (real images)
# =========================
# ضع هنا روابط حقيقية للصور لكل موضوع
IMAGE_LIBRARY = {
    "cybersecurity": [
        "https://images.pexels.com/photos/547429/pexels-photo-547429.jpeg",
        "https://images.pexels.com/photos/325229/pexels-photo-325229.jpeg",
        "https://images.pexels.com/photos/546819/pexels-photo-546819.jpeg"
    ],
    "programming": [
        "https://images.pexels.com/photos/574071/pexels-photo-574071.jpeg",
        "https://images.pexels.com/photos/3861972/pexels-photo-3861972.jpeg",
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg"
    ],
    "AI": [
        "https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg",
        "https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg",
        "https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg"
    ],
    "default": [
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg"
    ]
}

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

        return full_text.strip(), "cybersecurity"

    except Exception as e:
        print("Gemini Error:", e)
        return None, None

# =========================
# Download Image
# =========================
def download_image(topic):
    # اختيار الموضوع الصحيح أو default
    topic_key = topic.lower() if topic.lower() in IMAGE_LIBRARY else "default"
    image_url = random.choice(IMAGE_LIBRARY[topic_key])
    print(f"Downloading image for topic '{topic}': {image_url}")

    try:
        img_res = requests.get(image_url, timeout=30)
        if img_res.status_code == 200 and 'image' in img_res.headers.get('Content-Type', ''):
            with open(TEMP_IMAGE, "wb") as f:
                f.write(img_res.content)
            return True
        else:
            raise Exception("Invalid image response")
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
        if header[:3] == b"\xff\xd8\xff":
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
# Main
# =========================
def main():
    print("Generating content...")
    content, img_prompt = generate_content_and_image_prompt()

    if not content:
        print("Failed to generate content")
        return

    print("Content generated successfully")

    if not download_image(img_prompt):
        print("Image download failed")
        return

    if not validate_image():
        print("Image validation failed")
        return

    print("Posting to Facebook...")
    result = post_to_facebook(content)
    print("Facebook response:", result)

    try:
        os.remove(TEMP_IMAGE)
    except:
        pass

if __name__ == "__main__":
    main()
