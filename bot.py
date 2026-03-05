import os
import requests
import google.generativeai as genai

FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content():
    genai.configure(api_key=GEMINI_API_KEY)
    # استعملنا gemini-1.5-flash حيت هو اللي خدام دابا
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = "اكتب منشوراً فيسبوكياً قصيراً جداً بالدارجة المغربية عن معلومة تقنية مفيدة. استخدم إيموجي."
    response = model.generate_content(prompt)
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
        print("Generated:", content)
        result = post_to_facebook(content)
        print("Facebook Result:", result)
    except Exception as e:
        print("Error details:", e)
