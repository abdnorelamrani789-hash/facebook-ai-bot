import os
import requests
from google import genai

# جلب المعلومات من Secrets
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content():
    # إعداد العميل الجديد لـ Gemini
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = "اكتب منشوراً فيسبوكياً قصيراً جداً بالدارجة المغربية عن معلومة تقنية مفيدة. استخدم إيموجي."
    
    # طلب توليد النص باستعمال موديل gemini-1.5-flash
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )
    return response.text

def post_to_facebook(message):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {
        'message': message,
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    r = requests.post(url, data=payload)
    return r.json()

if __name__ == "__main__":
    try:
        content = generate_content()
        print(f"Content Generated: {content[:50]}...") # طباعة أول 50 حرف للتأكد
        result = post_to_facebook(content)
        print("Facebook Result:", result)
    except Exception as e:
        print("Detailed Error:", str(e))
