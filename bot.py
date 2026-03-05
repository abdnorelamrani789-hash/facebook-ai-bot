import os
import requests
import io
import time

# جلب المفاتيح من GitHub Secrets
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
HF_API_KEY = os.getenv('HF_API_KEY') # تأكد من هاد السمية فـ GitHub

def generate_content_and_prompt():
    # استعمال Gemini 3 Flash Preview
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = """
    أنت خبير تقني مغربي. اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة 'تقنية بالدارجة'.
    الشروط:
    1. ابدأ المنشور مباشرة بالمحتوى (ممنوع منعاً باتاً كتابة أي مقدمات).
    2. حافظ على الطول والشرح المعمق (نقاط واضحة، نصائح تقنية).
    3. في آخر سطر، اكتب عبارة IMAGE_PROMPT: متبوعة بوصف دقيق بالإنجليزية لصورة تقنية سينمائية تناسب المحتوى.
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
        return full_text, "futuristic cyber security technology"
    except:
        return None, None

def generate_image_hf(prompt):
    # غنستعملو موديل FLUX.1-schnell حيت سريع بزاف وكيولد صور واعرين
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # محاولة توليد الصورة
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    
    if response.status_code == 200:
        return response.content
    else:
        print(f"HF Error: {response.text}")
        return None

def post_to_facebook(message, image_bytes):
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    
    files = {
        'source': ('image.jpg', image_bytes, 'image/jpeg')
    }
    payload = {
        'caption': message,
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    return requests.post(fb_url, data=payload, files=files).json()

if __name__ == "__main__":
    # 1. توليد النص والوصف باستعمال Gemini 3
    content, img_prompt = generate_content_and_prompt()
    
    if content:
        print(f"Generating image for: {img_prompt}")
        # 2. توليد الصورة باستعمال Hugging Face
        image_data = generate_image_hf(img_prompt)
        
        if image_data:
            print("Image ready. Posting to Facebook...")
            # 3. النشر لفيسبوك
            result = post_to_facebook(content, image_data)
            print("Facebook Result:", result)
        else:
            print("Failed to generate image.")
    else:
        print("Failed to generate content.")
