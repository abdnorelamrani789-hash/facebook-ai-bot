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

# --- تحميل الصورة ---
def download_image(keyword):
    used_hashes = load_json(USED_IMAGES_FILE)

    urls = [
        f"https://source.unsplash.com/1080x1080/?{keyword},technology",
        f"https://source.unsplash.com/1080x1080/?{keyword},computer",
        f"https://source.unsplash.com/1080x1080/?{keyword},cybersecurity",
        f"https://source.unsplash.com/1080x1080/?{keyword},ai",
        f"https://source.unsplash.com/1080x1080/?{keyword},network"
    ]
    random.shuffle(urls)
    urls.append("https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1080")  # fallback

    for url in urls:
        try:
            r = requests.get(url, timeout=15)
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img.save(TEMP_IMAGE, format="JPEG")
            img_hash = get_image_hash(TEMP_IMAGE)

            if img_hash in used_hashes:
                print("Image already used! Trying next option...")
                continue

            used_hashes.append(img_hash)
            save_json(USED_IMAGES_FILE, used_hashes)
            print(f"Image downloaded successfully from {url}")
            return True
        except Exception as e:
            print(f"Failed to download image from {url}: {e}")

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
    # مثال بسيط: سيقرأ التعليقات من سجل قديم ويرد إذا لم يتم الرد
    replied = load_json(REPLIED_COMMENTS_FILE)
    # هنا يمكن إضافة منطق API للحصول على التعليقات الجديدة والرد عليها
    # سنبقيه placeholder حاليا
    print("Replying to comments (force old comments)...")
    # بعد الرد على تعليق معين:
    # replied.append(comment_id)
    save_json(REPLIED_COMMENTS_FILE, replied)

# --- Main ---
if __name__ == "__main__":
    print("Starting bot...")

    keyword = get_trending_keyword()
    print(f"Trending keyword: {keyword}")

    content, image_keyword = generate_content_and_image_prompt(keyword)
    if content:
        print("Generating content...")

        download_image(image_keyword)

        print("Posting to Facebook...")
        fb_result = post_to_facebook(content)
        print("Facebook response:", fb_result)

        reply_to_comments()
        print("Done!")
    else:
        print("Failed to generate content.")
