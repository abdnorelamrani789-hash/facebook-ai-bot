import os
import requests
import time

# جلب المفاتيح من GitHub Secrets
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
HF_API_KEY = os.getenv('HF_API_KEY')

def generate_content_and_prompt():
    # فرض استخدام Gemini 3 Flash Preview لإنتاج محتوى احترافي
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = """
    أنت خبير في الأمن المعلوماتي. اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة 'تقنية بالدارجة'.
    الشروط:
    1. ابدأ المنشور مباشرة بالمحتوى (ممنوع أي مقدمات).
    2. حافظ على الشرح المعمق والتنسيق الجيد.
    3. في آخر سطر تماماً، اكتب IMAGE_PROMPT: متبوعة بوصف إنجليزي لصورة سينمائية تجمع بين التكنولوجيا واللمسة المغربية.
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
        return full_text.strip(), "modern cybersecurity workspace with moroccan touch"
    except:
        return None, None

def generate_image_hf(image_prompt):
    # الرابط المباشر لموديل FLUX الأسرع
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_API_KEY.strip()}"} # استعملنا strip() لضمان عدم وجود فراغات
    
    response = requests.post(API_URL, headers=headers, json={"inputs": image_prompt})
    
    if response.status_code == 200:
        return response.content
    else:
        # إذا كان الموديل في طور التحميل (503)
        if response.status_code == 503:
            print("Model is warming up... waiting 15s")
            time.sleep(15)
            return generate_image_hf(image_prompt)
        print(f"HF Error Detail: {response.text}")
        return None

def post_to_facebook(message, image_bytes):
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    files = {'source': ('image.jpg', image_bytes, 'image/jpeg')}
    payload = {'caption': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
    return requests.post(fb_url, data=payload, files=files).json()

if __name__ == "__main__":
    content, img_prompt = generate_content_and_prompt()
    if content:
        print(f"Image Prompt: {img_prompt}")
        image_data = generate_image_hf(img_prompt)
        if image_data:
            result = post_to_facebook(content, image_data)
            print("Facebook Result:", result)
        else:
            print("Failed to generate image. Check your HF Token permissions.")
