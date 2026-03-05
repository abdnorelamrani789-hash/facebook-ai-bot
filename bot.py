import os
import requests

# جلب المفاتيح من GitHub Secrets
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content():
    # فرض استخدام موديل Gemini 3 Flash Preview
    model_name = "models/gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # برومبت مخصص لاهتماماتك في الشبكات والأمن المعلوماتي
    prompt = "اكتب منشوراً مدهشاً لفيسبوك بالدارجة المغربية عن معلومة في الأمن المعلوماتي أو الشبكات. ابدأ بـ 'واش كنتي عارف بلي...' واستخدم إيموجي."
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        res_json = response.json()
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Gemini Error: {res_json}")
            return "واش كنتي عارف بلي حماية بياناتك بتبدأ بكلمة سر قوية؟ 🔐✨"
    except Exception as e:
        print(f"Error: {e}")
        return None

def post_to_facebook_with_image(message):
    # رابط نشر الصور في فيسبوك
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    
    # رابط لتصويرة تقنية عشوائية عالية الجودة
    image_url = "https://loremflickr.com/800/600/technology,cybersecurity"
    
    payload = {
        'url': image_url,
        'caption': message, # النص غيتكتب كـ "Caption" للتصويرة
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    
    r = requests.post(url, data=payload)
    return r.json()

if __name__ == "__main__":
    # 1. توليد النص باستعمال الموديل الجديد
    content = generate_content()
    
    if content:
        print(f"Content from Gemini 3 Flash: {content}")
        # 2. النشر مع صورة
        result = post_to_facebook_with_image(content)
        print("Facebook Result:", result)
