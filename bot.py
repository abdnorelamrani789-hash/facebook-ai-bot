import os
import requests
import urllib.parse
import time

# جلب المفاتيح من GitHub Secrets
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content_and_image_prompt():
    # استخدام Gemini 3 Flash Preview
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = """
    أنت خبير في الأمن المعلوماتي والشبكات. اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة 'تقنية بالدارجة'.
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
        return full_text.strip(), "cybersecurity infrastructure network"
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None, None

def post_to_facebook(message, img_description):
    # 1. محاولة توليد الصورة برابط بديل وأكثر استقراراً
    encoded_prompt = urllib.parse.quote(img_description)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true"
    
    print(f"Attempting to download image: {image_url}")
    time.sleep(12) # وقت أطول لضمان توليد الصورة
    
    try:
        img_res = requests.get(image_url, timeout=30)
        # التأكد من أن الرد هو فعلاً صورة وليس نص خطأ
        if img_res.status_code == 200 and 'image' in img_res.headers.get('Content-Type', ''):
            with open('temp_image.jpg', 'wb') as f:
                f.write(img_res.content)
            print("Image downloaded successfully.")
        else:
            raise Exception("Invalid image response")
            
    except Exception as e:
        print(f"Primary image failed ({e}). Using reliable Unsplash fallback.")
        # رابط احتياطي مباشر لمواضيع الأمن المعلوماتي
        fallback_url = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1080&q=80"
        img_res = requests.get(fallback_url)
        with open('temp_image.jpg', 'wb') as f:
            f.write(img_res.content)

    # 2. التحقق من صحة الملف (Magic Numbers لـ JPEG)
    with open('temp_image.jpg', 'rb') as f:
        header = f.read(4)
        if header != b'\xff\xd8\xff\xe0' and header[:3] != b'\xff\xd8\xff':
            print("Warning: File header is not a valid JPEG. Retrying fallback...")
            # محاولة أخيرة برابط مضمون جداً
            img_res = requests.get("https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1080")
            with open('temp_image.jpg', 'wb') as f_retry:
                f_retry.write(img_res.content)

    # 3. إرسال الصورة لفيسبوك
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    with open('temp_image.jpg', 'rb') as img_file:
        files = {'source': ('post.jpg', img_file, 'image/jpeg')}
        payload = {'caption': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
        response = requests.post(fb_url, data=payload, files=files)
        return response.json()

if __name__ == "__main__":
    content, img_prompt = generate_content_and_image_prompt()
    if content:
        print("Processing post for 'Taqnia Bel Darija'...")
        result = post_to_facebook(content, img_prompt)
        print("Facebook Result:", result)

