import os
import requests
import urllib.parse

# جلب المفاتيح من GitHub Secrets
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content_and_image_prompt():
    # استعمال Gemini 3 Flash Preview
    model = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = """
    أنت خبير في الأمن المعلوماتي والشبكات. اكتب منشوراً احترافياً ومطولاً بالدارجة المغربية لصفحة 'تقنية بالدارجة'.
    الشروط:
    1. ابدأ المنشور مباشرة بالمحتوى (ممنوع تكتب أي مقدمة بحال 'هاك المنشور').
    2. المنشور يجب أن يكون تقنياً ومفيداً (شرح، خطوات، نصائح).
    3. في آخر المنشور، أضف سطراً يبدأ بكلمة IMAGE_PROMPT: متبوعة بوصف دقيق بالإنجليزية للصورة (مثال: cybersecurity hacker matrix style).
    """
    
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        res_json = response.json()
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        if "IMAGE_PROMPT:" in full_text:
            parts = full_text.split("IMAGE_PROMPT:")
            post_content = parts[0].strip()
            img_description = parts[1].strip()
        else:
            post_content = full_text
            img_description = "futuristic technology cyber security"
            
        return post_content, img_description
    except:
        return None, None

def post_to_facebook(message, img_description):
    # 1. إنشاء رابط الصورة
    encoded_prompt = urllib.parse.quote(img_description)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true"
    
    # 2. تحميل الصورة محلياً (باش فيسبوك يلقاها واجدة)
    img_data = requests.get(image_url).content
    with open('temp_image.jpg', 'wb') as handler:
        handler.write(img_data)
    
    # 3. إرسال الصورة كملف (File Upload)
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    
    with open('temp_image.jpg', 'rb') as img_file:
        files = {
            'source': img_file # هنا صيفطنا الملف حقيقي ماشي غير رابط
        }
        payload = {
            'caption': message,
            'access_token': FB_PAGE_ACCESS_TOKEN
        }
        response = requests.post(fb_url, data=payload, files=files)
        return response.json()

if __name__ == "__main__":
    content, img_prompt = generate_content_and_image_prompt()
    
    if content:
        print(f"Content ready. Sending to Facebook...")
        result = post_to_facebook(content, img_prompt)
        print("Facebook Result:", result)
    else:
        print("Failed to generate content.")
