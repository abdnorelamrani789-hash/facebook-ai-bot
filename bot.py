import os
import requests
import time
import json
import random
import hashlib
from io import BytesIO
from PIL import Image

# --- GitHub Secrets ---
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')

# --- Files ---
HISTORY_FILE = "history.json"
REPLIED_COMMENTS_FILE = "replied_comments.json"
USED_IMAGES_FILE = "used_images.json"
TEMP_IMAGE = "temp.jpg"

# --- JSON helpers ---
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

def get_image_hash(img_path):
    with open(img_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# --- Get trending keyword ---
def get_trending_keyword():
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360)
        trending = pytrends.trending_searches(pn='united_states')
        return trending[0][0]
    except:
        return "technology"

# --- Generate content & image prompt ---
def generate_content_and_image_prompt(keyword):
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
أنت خبير في الأمن المعلوماتي والشبكات. اكتب منشوراً بالدارجة المغربية حول "{keyword}".
1. ابدأ المحتوى مباشرة.
2. في آخر المنشور أضف IMAGE_PROMPT بالإنجليزية لوصف صورة تقنية.
"""
    headers = {'Content-Type': 'application/json'}
    data = {"contents":[{"parts":[{"text": prompt}]}]}
    try:
        res = requests.post(url, json=data, headers=headers)
        res_json = res.json()
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        if "IMAGE_PROMPT:" in full_text:
            parts = full_text.split("IMAGE_PROMPT:")
            return parts[0].strip(), parts[1].strip()
        return full_text.strip(), keyword
    except Exception as e:
        print(f"Error generating content: {e}")
        return None, keyword

# --- Download image from Unsplash API or fallback ---
def download_image(keyword):
    used_hashes = load_json(USED_IMAGES_FILE)
    fallback_keywords = ["cybersecurity", "programming", "server room", "AI technology", "tech office"]

    # First try the Gemini IMAGE_PROMPT or keyword
    keywords_to_try = [keyword] + fallback_keywords
    for k in keywords_to_try:
        try:
            headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
            params = {"query": k, "orientation": "squarish", "per_page": 10}
            response = requests.get("https://api.unsplash.com/search/photos", headers=headers, params=params)
            data = response.json()
            if "results" not in data or not data["results"]:
                continue
            random.shuffle(data["results"])
            for item in data["results"]:
                img_url = item["urls"]["regular"]
                r = requests.get(img_url, timeout=15)
                if 'image' not in r.headers.get('Content-Type',''):
                    continue
                img = Image.open(BytesIO(r.content)).convert("RGB")
                img.save(TEMP_IMAGE, format="JPEG")
                img_hash = get_image_hash(TEMP_IMAGE)
                if img_hash in used_hashes:
                    continue
                used_hashes.append(img_hash)
                save_json(USED_IMAGES_FILE, used_hashes)
                print(f"Image downloaded successfully for '{k}'")
                return True
        except Exception as e:
            print(f"Failed for keyword '{k}': {e}")
    raise Exception("Critical: Could not download a valid image from any keyword.")

# --- Post to Facebook ---
def post_to_facebook(message):
    with open(TEMP_IMAGE, "rb") as img_file:
        files = {'source': ('post.jpg', img_file, 'image/jpeg')}
        payload = {'caption': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
        response = requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",
                                 data=payload, files=files)
        return response.json()

# --- Reply to comments ---
def reply_to_comments():
    replied = load_json(REPLIED_COMMENTS_FILE)
    print("Replying to comments (force old comments)...")
    save_json(REPLIED_COMMENTS_FILE, replied)

# --- Main ---
if __name__ == "__main__":
    print("Starting bot...")
    trending_keyword = get_trending_keyword()
    print(f"Trending keyword: {trending_keyword}")

    content, img_prompt = generate_content_and_image_prompt(trending_keyword)
    if content:
        print("Generating content...")
        try:
            download_image(img_prompt or trending_keyword)
        except Exception as e:
            print(e)
            exit(1)

        print("Posting to Facebook...")
        fb_result = post_to_facebook(content)
        print("Facebook response:", fb_result)

        reply_to_comments()
        print("Done!")
    else:
        print("Failed to generate content.")
