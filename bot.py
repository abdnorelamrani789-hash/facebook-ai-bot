import os
import requests
import time

# جلب المفاتيح مع التأكد من وجودها
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
HF_API_KEY = os.getenv('HF_API_KEY')

def check_secrets():
    """التأكد من أن جميع المفاتيح الضرورية موجودة"""
    missing = []
    if not FB_PAGE_ID: missing.append("FB_PAGE_ID")
    if not FB_PAGE_ACCESS_TOKEN: missing.append("FB_PAGE_ACCESS_TOKEN")
    if not GEMINI_API_KEY: missing.append("GEMINI_API_KEY")
    if not HF_API_KEY: missing.append("HF_API_KEY")
    
    if missing:
        raise ValueError(f"المفاتيح التالية ناقصة في GitHub Secrets: {', '.join(missing)}")

def generate_content_and_prompt():
    # استخدام Gemini 3 Flash Preview لإنتاج محتوى احترافي
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = """
    أنت خبير في الأمن المعلوماتي والشبكات. اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة 'تقنية بالدارجة'.
    1. ابدأ المنشور مباشرة بالمحتوى (بدون مقدمات).
    2. حافظ على الشرح المعمق والتنسيق الجيد.
    3. في آخر سطر، اكتب IMAGE_PROMPT: متبوعة بوصف إنجليزي لصورة سينمائية تقنية.
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
        return full_text.strip(), "modern cybersecurity technology concept"
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None, None

def generate_image_hf(image_prompt):
    # استخدام رابط الاستدلال لـ Hugging Face
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    # إضافة التحقق لتجنب خطأ NoneType
    api_key = HF_API_KEY.strip() if HF_API_KEY else ""
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.post(API_URL, headers=headers, json={"inputs": image_prompt})
    
    if response.status_code == 200:
        return response.content
    else:
        print(f"HF Error: {response.status_code} - {response.text}")
        return None

def post_to_facebook(message, image_bytes):
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    files = {'source': ('image.jpg', image_bytes, 'image/jpeg')}
    payload = {'caption': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
    return requests.post(fb_url, data=payload, files=files).json()

if __name__ == "__main__":
    try:
        check_secrets()
        content, img_prompt = generate_content_and_prompt()
        if content:
            print(f"Generating image for: {img_prompt}")
            image_data = generate_image_hf(img_prompt)
            if image_data:
                result = post_to_facebook(content, image_data)
                print("Facebook Result:", result)
            else:
                print("Failed to generate image. Check HF Token.")
    except Exception as e:
        print(f"خطأ في التشغيل: {e}")
