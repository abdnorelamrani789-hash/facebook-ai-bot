import os
import requests

FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def generate_content():
    # استعملنا v1 (النسخة الأكثر استقراراً) وموديل gemini-pro العادي
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": "اكتب نصيحة تقنية قصيرة جدا بالدارجة المغربية."}]}]
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        res_json = response.json()
        
        # إيلا نجح Gemini
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # إيلا بقى 404، غانخدمو بـ "الذكاء الاصطناعي ديالنا" (جمل عشوائية واجدة)
            from datetime import datetime
            tips = [
                "تعلم الاختصارات ديال الكيبورد غايربحك بزاف ديال الوقت فخدمتك! ⌨️",
                "ديما دير Backup لبياناتك، ما كتعرفش إمتى يغدرك الهارد ديسك! 💾",
                "البرمجة هي صبر قبل ما تكون ذكاء، غير كمل غاتوصل! 🚀",
                "سد التابز (Tabs) اللي ما خدامش بيهم باش تسرع المتصفح ديالك! 🌐"
            ]
            # عزل جملة على حسب الدقيقة باش كل مرة يبان بوست مختلف
            return tips[datetime.now().minute % len(tips)]

    except Exception:
        return "تقنية بالدارجة: معلومة جديدة جاية ف الطريق! 💡"

def post_to_facebook(message):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {'message': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
    r = requests.post(url, data=payload)
    return r.json()

if __name__ == "__main__":
    content = generate_content()
    print(f"Content: {content}")
    result = post_to_facebook(content)
    print("Facebook Result:", result)
