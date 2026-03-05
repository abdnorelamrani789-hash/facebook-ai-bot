import os
import requests

# جلب المفاتيح
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content():
    # استعمال رابط API المباشر ديال Gemini
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": "اكتب منشوراً فيسبوكياً قصيراً جداً بالدارجة المغربية عن معلومة تقنية مفيدة. استخدم إيموجي."}]
        }]
    }
    
    response = requests.post(url, json=data, headers=headers)
    res_json = response.json()
    
    if 'candidates' in res_json:
        return res_json['candidates'][0]['content']['parts'][0]['text']
    else:
        raise Exception(f"Gemini Error: {res_json}")

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
        print(f"Content: {content[:50]}...")
        result = post_to_facebook(content)
        print("Facebook Result:", result)
    except Exception as e:
        print("Detailed Error:", str(e))
