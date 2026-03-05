import os
import requests
import urllib.parse
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

        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=30
        )

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

    encoded_prompt = urllib.parse.quote(prompt)

    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true"

    print("Generating image...")
    print(image_url)

    time.sleep(15)

    try:

        img_res = requests.get(image_url, timeout=40)

        if img_res.status_code == 200 and "image" in img_res.headers.get("Content-Type", ""):

            with open(TEMP_IMAGE, "wb") as f:
                f.write(img_res.content)

            return True

        else:
            raise Exception("Invalid image response")

    except Exception as e:

        print("Primary image failed:", e)

        fallback = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1080&q=80"

        try:

            img_res = requests.get(fallback, timeout=30)

            with open(TEMP_IMAGE, "wb") as f:
                f.write(img_res.content)

            return True

        except Exception as e:

            print("Fallback failed:", e)
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

            files = {
                "source": ("post.jpg", img_file, "image/jpeg")
            }

            payload = {
                "caption": message,
                "access_token": FB_PAGE_ACCESS_TOKEN
            }

            response = requests.post(
                fb_url,
                data=payload,
                files=files,
                timeout=30
            )

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
        print("Image generation failed")
        return

    if not validate_image():
        print("Image validation failed")
        return

    print("Posting to Facebook...")

    result = post_to_facebook(content)

    print("Facebook response:")
    print(result)

    # Remove temp image
    try:
        os.remove(TEMP_IMAGE)
    except:
        pass


if __name__ == "__main__":
    main()
