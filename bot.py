import os
import requests

FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content():
    # استهداف الموديل Flash 1.5 مباشرة عبر نسخة v1beta
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # البرومبت اللي غيخلي الموديل يبدع
    data = {
        "contents": [{
            "parts": [{"text": "اكتب معلومة تقنية مدهشة وقصيرة جدا بالدارجة المغربية لفيسبوك. ابدأ المنشور بعبارة 'واش كنتي عارف بلي...' واستخدم إيموجي."}]
        }]
    }
    
    response = requests.post(url, json=data, headers=headers)
    res_json = response.json()
    
    if 'candidates' in res_json:
        # هاد السطر كيجيب النص اللي كتبو الموديل
        return res_json['candidates'][0]['content']['parts'][0]['text']
    else:
        # إيلا باقي الـ 404، غانطبعو الخطأ باش نعرفو علاش حسابك مابغاش يخدم هاد الموديل
        print(f"Error from Gemini: {res_json}")
        return None

def post_to_facebook(message):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {'message': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
    r = requests.post(url, data=payload)
    return r.json()

if __name__ == "__main__":
    content = generate_content()
    
    if content:
        print(f"Success! Gemini Flash says: {content}")
        result = post_to_facebook(content)
        print("Facebook Result:", result)
    else:
        print("Still getting 404. Switching to local backup to keep the page alive...")
        backup_text = "واش كنتي عارف بلي البرمجة بـ Python هي الأسهل للمبتدئين؟ 🐍✨"
        post_to_facebook(backup_text)
