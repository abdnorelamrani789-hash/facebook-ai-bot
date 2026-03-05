import os
import requests
import json
import urllib.parse

# جلب المفاتيح من GitHub Secrets
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content_and_image_prompt():
    # استعمال موديل Gemini 3 Flash Preview
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    
    # برومبت دقيق باش يحيد المقدمة ويقاد التصويرة
    prompt = """
    أنت خبير في الأمن المعلوماتي والشبكات. اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة 'تقنية بالدارجة'.
    الشروط:
    1. ابدأ المنشور مباشرة بالمحتوى (ممنوع تكتب أي مقدمة بحال 'هاك المنشور' أو 'إليك هاد المعلومة').
    2. حافظ على نفس طول المنشور السابق (شرح معمق، خطوات واضحة، ونصائح).
    3. في آخر المنشور، أضف سطراً يبدأ بكلمة IMAGE_PROMPT: متبوعة بوصف دقيق بالإنجليزية للصورة التي تناسب المحتوى (مثال: A high-tech digital security shield with neon lights).
    """
    
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        res_json = response.json()
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        # تقسيم النص لاستخراج المنشور ووصف الصورة
        if "IMAGE_PROMPT:" in full_text:
            parts = full_text.split("IMAGE_PROMPT:")
            post_content = parts[0].strip()
            img_description = parts[1].strip()
        else:
            post_content = full_text
            img_description = "cybersecurity technology concept"
            
        return post_content, img_description
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def post_to_facebook(message, img_description):
    # توليد صورة ذكاء اصطناعي بناءً على وصف Gemini
    encoded_prompt = urllib.parse.quote(img_description)
    # استعملنا محرك توليد الصور Pollinations اللي كيعطي نتائج فنية ومرتبطة بالوصف
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true"
    
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    payload = {
        'url': image_url,
        'caption': message,
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    return requests.post(fb_url, data=payload).json()

if __name__ == "__main__":
    content, img_prompt = generate_content_and_image_prompt()
    
    if content:
        print(f"Content ready (No intro). Image prompt: {img_prompt}")
        result = post_to_facebook(content, img_prompt)
        print("Facebook Result:", result)
    else:
        print("Failed to generate content.")
