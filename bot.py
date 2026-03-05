import os
import requests

FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content():
    # جربنا gemini-1.0-pro حيت هو الأكثر توافقاً عالمياً
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.0-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": "اكتب معلومة تقنية مفيدة بالدارجة المغربية في سطر واحد."}]}]
    }
    
    response = requests.post(url, json=data, headers=headers)
    res_json = response.json()
    
    if 'candidates' in res_json:
        return res_json['candidates'][0]['content']['parts'][0]['text']
    else:
        # إيلا فشل، غنعطيوه نص احتياطي باش ما يوقفش البوت ونشوفو واش فيسبوك خدام
        print("Gemini failed, using backup text.")
        return "واش كتعرف بلي البرمجة هي لغة المستقبل؟ تعلم كودينغ دابا! 💻"

def post_to_facebook(message):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {
        'message': message,
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    r = requests.post(url, data=payload)
    return r.json()

if __name__ == "__main__":
    content = generate_content()
    print(f"Content to post: {content}")
    result = post_to_facebook(content)
    print("Facebook Result:", result)
