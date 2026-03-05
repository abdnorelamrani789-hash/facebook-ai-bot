import os
import requests

FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def get_working_model():
    # هاد الدالة غتقلب لينا شنو هوما الموديلات اللي عندك فيهم الحق
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        res = requests.get(list_url).json()
        if 'models' in res:
            # كنقلبو على أي موديل فيه كلمة flash
            flash_models = [m['name'] for m in res['models'] if 'flash' in m['name']]
            if flash_models:
                print(f"Found Flash models: {flash_models}")
                return flash_models[0] # غناخدو أول واحد (غالباً gemini-1.5-flash أو gemini-2.0-flash)
        print(f"Full API Response: {res}")
    except Exception as e:
        print(f"Error checking models: {e}")
    return "models/gemini-1.5-flash" # احتياط إيلا فشل البحث

def generate_content(model_name):
    # دابا غنخدمو بـ الموديل اللي لقيناه
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": "اكتب معلومة تقنية مدهشة بالدارجة المغربية لصفحة 'تقنية بالدارجة'. استخدم إيموجي."}]}]
    }
    
    response = requests.post(url, json=data, headers=headers)
    res_json = response.json()
    
    if 'candidates' in res_json:
        return res_json['candidates'][0]['content']['parts'][0]['text']
    else:
        print(f"Failed to generate with {model_name}. Error: {res_json}")
        return None

def post_to_facebook(message):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {'message': message, 'access_token': FB_PAGE_ACCESS_TOKEN}
    r = requests.post(url, data=payload)
    return r.json()

if __name__ == "__main__":
    # 1. قلب على الموديل اللي خدام
    active_model = get_working_model()
    print(f"Using model: {active_model}")
    
    # 2. ولد النص
    content = generate_content(active_model)
    
    if content:
        print(f"Content: {content}")
        result = post_to_facebook(content)
        print("Facebook Result:", result)
    else:
        print("Could not generate content. Check the logs above.")
