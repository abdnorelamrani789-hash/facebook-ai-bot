import os
import requests
import urllib.parse
import time

# جلب المفاتيح من GitHub Secrets
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content_and_image_prompt():
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = """
    أنت خبير في الأمن المعلوماتي والشبكات. اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة 'تقنية بالدارجة'.
    الشروط:
    1. ابدأ المنشور مباشرة بالمحتوى (بدون أي مقدمات).
    2. حافظ على الشرح المعمق والتنسيق الجيد.
    3. في آخر المنشور، أضف سطراً يبدأ بكلمة IMAGE_PROMPT: متبوعة بوصف دقيق بالإنجليزية لصورة تقنية.
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
        return full_text.strip(), "cybersecurity digital network concept"
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None, None

def post_to_facebook(message, img_description):
    # 1. إنشاء رابط الصورة (استعمال رابط مباشر ومستقر)
    encoded_prompt = urllib.parse.quote(img_description)
    image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1080&height=1080&seed=42&model=flux"
    
    print(f"Downloading image from: {image_url}")
    
    # محاولة التحميل مع وقت انتظار كافي
    time.sleep(10) # ننتظر 10 ثواني لضمان توليد الصورة
    img_res = requests.get(image_url, stream=True)
    
    if img_res.status_code == 200:
        with open('temp_image.jpg', 'wb') as f:
            for chunk in img_res.iter_content(1024):
                f.write(chunk)
    else:
        print("Image download failed. Using a fallback tech image.")
        img_res = requests.get("https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1080&q=80")
        with open('temp_image.jpg', 'wb') as f:
            f.write(img_res.content)

    # 2. إرسال الصورة لفيسبوك مع التحقق من الحجم
    if os.path.getsize('temp_image.jpg') < 1000: # إذا كان الملف أصغر من 1KB فهو ليس صورة
        print("Error: The file is too small to be an image.")
        return {"error": "Invalid file content"}

    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    
    with open('temp_image.jpg', 'rb') as img_file:
        files = {'source': ('image.jpg', img_file, 'image/jpeg')}
        payload = {
            'caption': message,
            'access_token': FB_PAGE_ACCESS_TOKEN
        }
        response = requests.post(fb_url, data=payload, files=files)
        return response.json()

if __name__ == "__main__":
    content, img_prompt = generate_content_and_image_prompt()
    
    if content:
        print("Content ready. Sending to Facebook...")
        result = post_to_facebook(content, img_prompt)
        print("Facebook Result:", result)
