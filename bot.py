import os
import requests
import google.generativeai as genai

# هاد المعلومات غايجيبهم البوت من السيكريتس (Secrets) اللي غانصاوبو من بعد
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content():
    # إعداد Gemini باش يكتب لينا البوست
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    prompt = "اكتب منشوراً فيسبوكياً قصيراً بالدارجة المغربية عن معلومة تقنية مفيدة (مثلاً عن البرمجة أو الذكاء الاصطناعي). استخدم إيموجي."
    response = model.generate_content(prompt)
    return response.text

def post_to_facebook(message):
    # إرسال المنشور للفيسبوك
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
    payload = {
        'message': message,
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    r = requests.post(url, data=payload)
    return r.json()

if __name__ == "__main__":
    try:
        content = generate_content()
        result = post_to_facebook(content)
        print("Success:", result)
    except Exception as e:
        print("Error:", e)

