import os
import requests
import urllib.parse
import time
import json
import random
import hashlib
from io import BytesIO
from PIL import Image

# --- إعدادات GitHub Secrets ---
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- ملفات تخزين البيانات ---
HISTORY_FILE = "history.json"
REPLIED_COMMENTS_FILE = "reply_comments.json"
USED_IMAGES_FILE = "used_images.json"
TEMP_IMAGE = "temp.jpg"

# --- مساعدات JSON ---
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

# --- hash للصورة ---
def get_image_hash(img_path):
    with open(img_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# --- جلب keyword الترند ---
def get_trending_keyword():
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360)
        trending = pytrends.trending_searches(pn='united_states')
        keyword = trending[0][0]
        return keyword
    except Exception as e:
        print(f"Error fetching trending topics: {e}")
        return "technology"  # fallback

# --- توليد المحتوى باستخدام Gemini ---
def generate_content_and_image_prompt(keyword):
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
أنت خبير في الأمن المعلوماتي والشبكات. اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة 'تقنية بالدارجة' حول "{keyword}".
1. ابدأ المنشور مباشرة بالمحتوى (ممنوع أي مقدمة).
2. حافظ على الشرح المعمق والتنسيق الجيد.
3. في آخر المنشور، أضف سطراً يبدأ بكلمة IMAGE_PROMPT: متبوعة بوصف إنجليزي لصورة تقنية.
"""
    
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        res_json = response.json()
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        if "IMAGE_PROMPT:" in full_text:
            parts = full_text.split("IMAGE_PROMPT:")
            return parts[0].strip(), parts[1].strip()
        return full_text.strip(), keyword
    except Exception as e:
        print(f"Error generating content: {e}")
        return None, keyword

# --- تحميل الصورة (Unsplash + Pollinations fallback) ---
def download_image(keyword, content_prompt=None):
    used_hashes = load_json(USED_IMAGES_FILE)

    # --- قائمة keywords قصيرة للصور الحقيقية ---
    keywords_for_unsplash = [
        "cybersecurity",
        "network",
        "AI technology",
        "programming",
        "tech office",
        "server room"
    ]
    keywords_for_unsplash.append(keyword)  # إضافة keyword الرئيسي
    random.shuffle(keywords_for_unsplash)

    # --- محاولة Unsplash أولاً ---
    for k in keywords_for_unsplash:
        try:
            url = f"https://source.unsplash.com/1080x1080/?{k}"
            r = requests.get(url, timeout=15)
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img.save(TEMP_IMAGE, format="JPEG")
            img_hash = get_image_hash(TEMP_IMAGE)
            if img_hash in used_hashes:
                print(f"Image from Unsplash ({k}) already used! Trying next...")
                continue
            used_hashes.append(img_hash)
            save_json(USED_IMAGES_FILE, used_hashes)
            print(f"Image downloaded successfully from Unsplash ({k})")
            return True
        except Exception as e:
            print(f"Failed to download image from Unsplash ({k}): {e}")

    # --- fallback: توليد صورة AI عبر Pollinations ---
    if content_prompt:
        try:
            encoded_prompt = urllib.parse.quote(content_prompt)
            ai_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true"
            r = requests.get(ai_url, timeout=30)
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img.save(TEMP_IMAGE, format="JPEG")
            img_hash = get_image_hash(TEMP_IMAGE)
            if img_hash not in used_hashes:
                used_hashes.append(img_hash)
                save_json(USED_IMAGES_FILE, used_hashes)
            print("Image generated successfully from AI (Pollinations)")
            return True
        except Exception as e:
            print(f"Failed to generate AI image: {e}")

    print("No new image could be downloaded. The post will be text only.")
    return False

# --- نشر على فيسبوك ---
def post_to_facebook(message):
    if os.path.exists(TEMP_IMAGE):
        with open(TEMP_IMAGE, "rb") as img_file:
            files = {'source': ('post.jpg', img_file, 'image/jpeg')}
            payload = {'caption': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
            response = requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",
                                     data=payload, files=files)
            return response.json()
    else:
        # نشر نص فقط
        payload = {'message': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
        response = requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed",
                                 data=payload)
        return response.json()

# --- الرد على التعليقات ---
def reply_to_comments():
    replied = load_json(REPLIED_COMMENTS_FILE)
    # placeholder للردود
    print("Replying to comments (force old comments)...")
    save_json(REPLIED_COMMENTS_FILE, replied)

# --- Main ---
if __name__ == "__main__":
    print("Starting bot...")

    keyword = get_trending_keyword()
    print(f"Trending keyword: {keyword}")

    content, image_prompt = generate_content_and_image_prompt(keyword)
    if content:
        print("Generating content...")

        download_image(keyword, content_prompt=image_prompt)

        print("Posting to Facebook...")
        fb_result = post_to_facebook(content)
        print("Facebook response:", fb_result)

        reply_to_comments()
        print("Done!")
    else:
        print("Failed to generate content.")
