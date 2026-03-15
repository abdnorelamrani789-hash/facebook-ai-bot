import os
import re
import json
import time
import base64
import random
import logging
import requests
import io
from datetime import date
from pathlib import Path
from PIL import Image

# =========================
# إعداد التسجيل
# =========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================
# Environment Variables
# =========================
FB_PAGE_ID           = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")
PEXELS_API_KEY       = os.getenv("PEXELS_API_KEY")
UNSPLASH_ACCESS_KEY  = os.getenv("UNSPLASH_ACCESS_KEY")
MODEL_NAME           = "gemini-2.5-flash"

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise EnvironmentError("❌ متغيرات البيئة المطلوبة غير موجودة")

# =========================
# الثوابت
# =========================
TEMP_IMAGE        = Path("temp_image.jpg")
POSTED_FILE       = Path("posted_content.json")
USED_IMAGES_FILE  = Path("used_images.json")
MAX_IMAGE_WIDTH   = 1200
MAX_POST_LENGTH   = 2000

# =========================
# Session
# =========================
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    )
})

# =========================
# أنواع المحتوى الفيروسي
# كل نوع عنده topics خاصة بيه
# =========================
CONTENT_TYPES = [
    {
        "type":        "حيلة تقنية",
        "emoji":       "💡",
        "topics": [
            "حيل مخفية في iPhone لا يعرفها معظم الناس",
            "اختصارات لوحة المفاتيح في Windows توفر الوقت",
            "إعدادات Android المخفية تحسن الأداء",
            "حيل في WhatsApp تجهلها الأغلبية",
            "ميزات سرية في Google Chrome",
            "حيل في YouTube لا يعرفها كثيرون",
            "إعدادات الكاميرا في الهاتف لصور احترافية",
            "حيل في Gmail توفر ساعات من العمل",
            "ميزات مخفية في MacOS تسهل الحياة",
            "حيل في Instagram لزيادة التفاعل",
            "اختصارات مفيدة في Google Maps",
            "حيل في PDF تجعل حياتك أسهل",
        ]
    },
    {
        "type":        "تطبيق مفيد",
        "emoji":       "📱",
        "topics": [
            "تطبيقات مجانية تغني عن الاشتراكات المدفوعة",
            "تطبيقات إنتاجية تضاعف إنجازك اليومي",
            "تطبيقات تحرير صور احترافية مجانية",
            "تطبيقات تعلم البرمجة من الصفر",
            "تطبيقات توفير الوقت والتنظيم الشخصي",
            "تطبيقات VPN مجانية وموثوقة",
            "تطبيقات تحويل الملفات بدون إنترنت",
            "تطبيقات تحميل الفيديو من كل المنصات",
            "تطبيقات قراءة الكتب مجاناً",
            "تطبيقات إدارة كلمات المرور بأمان",
        ]
    },
    {
        "type":        "أداة AI",
        "emoji":       "🤖",
        "topics": [
            "أدوات AI مجانية أفضل من ChatGPT لا تعرفها",
            "أدوات AI لإنشاء صور احترافية مجاناً",
            "أدوات AI لكتابة المحتوى والمقالات",
            "أدوات AI لتحرير الفيديو تلقائياً",
            "أدوات AI لترجمة المستندات بدقة عالية",
            "أدوات AI لإنشاء العروض التقديمية",
            "أدوات AI لتحليل البيانات بدون برمجة",
            "أدوات AI لتحسين جودة الصوت والفيديو",
            "أدوات AI لتلخيص المقالات والكتب",
            "أدوات AI للمساعدة في البرمجة",
            "كيف تستخدم ChatGPT لتوفير ساعات من العمل",
        ]
    },
    {
        "type":        "تحذير أمني",
        "emoji":       "🔒",
        "topics": [
            "إعدادات الخصوصية في هاتفك يجب تغييرها الآن",
            "تطبيقات خطيرة تسرب بياناتك الشخصية",
            "كيف تعرف إذا كان حسابك مخترقاً",
            "أخطاء شائعة تعرض كلمات مرورك للخطر",
            "كيف تحمي هاتفك من الاختراق",
            "إعدادات واتساب تهدد خصوصيتك",
            "كيف تتحقق من أمان شبكة WiFi",
            "احتيالات رقمية شائعة وكيف تتجنبها",
            "كيف تحذف بياناتك من الإنترنت",
            "إعدادات فيسبوك تحمي حسابك من الاختراق",
            "علامات تدل على أن هاتفك مراقب",
        ]
    },
]

# =========================
# مكتبة الصور الاحتياطية حسب النوع
# =========================
IMAGE_LIBRARY = {
    "حيلة تقنية": [
        "https://images.pexels.com/photos/574071/pexels-photo-574071.jpeg",
        "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg",
        "https://images.pexels.com/photos/270637/pexels-photo-270637.jpeg",
        "https://images.pexels.com/photos/325185/pexels-photo-325185.jpeg",
    ],
    "تطبيق مفيد": [
        "https://images.pexels.com/photos/887751/pexels-photo-887751.jpeg",
        "https://images.pexels.com/photos/1092644/pexels-photo-1092644.jpeg",
        "https://images.pexels.com/photos/699122/pexels-photo-699122.jpeg",
        "https://images.pexels.com/photos/3585088/pexels-photo-3585088.jpeg",
    ],
    "أداة AI": [
        "https://images.pexels.com/photos/8386440/pexels-photo-8386440.jpeg",
        "https://images.pexels.com/photos/3861972/pexels-photo-3861972.jpeg",
        "https://images.pexels.com/photos/5380797/pexels-photo-5380797.jpeg",
        "https://images.pexels.com/photos/8386438/pexels-photo-8386438.jpeg",
    ],
    "تحذير أمني": [
        "https://images.pexels.com/photos/60504/security-protection-anti-virus-software-60504.jpeg",
        "https://images.pexels.com/photos/5380664/pexels-photo-5380664.jpeg",
        "https://images.pexels.com/photos/4974914/pexels-photo-4974914.jpeg",
        "https://images.pexels.com/photos/1181671/pexels-photo-1181671.jpeg",
    ],
}

# =========================
# أدوات JSON
# =========================
def _load_json(path: Path, default):
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"خطأ في تحميل {path.name}: {e}")
    return default

def _save_json(path: Path, data):
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ {path.name}: {e}")

# =========================
# إدارة المحتوى المنشور
# =========================
def load_posted() -> list:
    return _load_json(POSTED_FILE, [])

def save_posted(posted: list):
    # نحتفظ بآخر 200 منشور فقط
    _save_json(POSTED_FILE, posted[-200:])

def load_used_images() -> set:
    return set(_load_json(USED_IMAGES_FILE, []))

def save_used_images(used: set):
    _save_json(USED_IMAGES_FILE, list(used))

# =========================
# اختيار موضوع المنشور
# ✅ نظام ذكي يضمن التنويع اليومي
# ✅ محتوى مختلف صباحاً ومساءً
# =========================

# أنواع المحتوى المفضلة لكل وقت
SESSION_PREFERENCE = {
    # الصباح: محتوى تحفيزي وعملي يبدأ به اليوم
    "morning": ["حيلة تقنية", "أداة AI", "تطبيق مفيد"],
    # المساء: محتوى تفاعلي وتحذيري بعد يوم عمل
    "evening": ["تحذير أمني", "حيلة تقنية", "أداة AI"],
}

def pick_content_topic() -> dict:
    """
    يختار نوع المحتوى والموضوع بذكاء:
    - يراعي وقت النشر (صباح / مساء)
    - يتجنب تكرار نفس النوع يومين متتاليين
    - يتجنب تكرار نفس الموضوع في آخر 30 منشور
    """
    posted        = load_posted()
    recent_topics = {p.get("topic", "") for p in posted[-30:]}
    recent_types  = [p.get("type", "")  for p in posted[-4:]]
    session       = os.getenv("POST_SESSION", "morning")
    preferred     = SESSION_PREFERENCE.get(session, [])

    logger.info(f"🕐 وقت النشر: {session}")

    # ترتيب الأنواع: المفضلة أولاً ثم الباقي
    preferred_types = [c for c in CONTENT_TYPES if c["type"] in preferred]
    other_types     = [c for c in CONTENT_TYPES if c["type"] not in preferred]
    ordered_types   = preferred_types + other_types
    random.shuffle(preferred_types)
    ordered_types   = preferred_types + other_types

    for content in ordered_types:
        # تجنب نفس النوع مرتين متتاليتين
        if recent_types and recent_types[-1] == content["type"]:
            continue

        # فلتر المواضيع غير المستخدمة مؤخراً
        available_topics = [
            t for t in content["topics"]
            if t not in recent_topics
        ]

        if not available_topics:
            available_topics = content["topics"]  # إعادة الكل إذا نفدت

        topic = random.choice(available_topics)
        logger.info(f"📌 النوع: {content['type']} | الموضوع: {topic}")
        return {
            "type":  content["type"],
            "emoji": content["emoji"],
            "topic": topic,
        }

    # fallback
    content = random.choice(CONTENT_TYPES)
    return {
        "type":  content["type"],
        "emoji": content["emoji"],
        "topic": random.choice(content["topics"]),
    }

# =========================
# توليد المنشور عبر Gemini
# ✅ Prompt محسّن للانتشار الفيروسي
# =========================
def generate_post(content: dict) -> str | None:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    )

    prompt = f"""
أنت خبير سوشل ميديا متخصص في المحتوى التقني للجمهور العربي والمغربي.
مهمتك كتابة منشور فيسبوك يحقق انتشاراً فيروسياً حول:

النوع: {content['type']} {content['emoji']}
الموضوع: {content['topic']}

━━━━━━━━━━━━━━━━━━━━━━
🎯 قواعد الانتشار الفيروسي:
━━━━━━━━━━━━━━━━━━━━━━

**اللغة:**
- امزج الدارجة المغربية مع العربية الفصحى بشكل طبيعي
- الدارجة في المقدمة والتعليقات العاطفية
- الفصحى في شرح المعلومات التقنية
- المصطلحات التقنية تبقى بالإنجليزية (AI، App، Update...)

**هيكل المنشور الفيروسي (إلزامي):**

1. **HOOK قوي (سطر واحد فقط):**
   - إما رقم مثير: "7 أشياء في هاتفك ما كتعرفهمش..."
   - إما تحدي: "جرب هاد الشي دابا وشوف شنو غيوقع..."
   - إما سر: "ما كيقولوش هاد الشي بصراحة..."
   - إما تحذير: "احذر! هاد الإعداد كيسرب بياناتك..."

2. **المحتوى (القلب):**
   - قائمة من 5 إلى 7 نقاط عملية وقابلة للتطبيق فوراً
   - كل نقطة: عنوان قصير + شرح 1-2 جملة
   - استخدم إيموجي مختلف لكل نقطة
   - المعلومات حقيقية ومفيدة وقابلة للتطبيق

3. **لحظة WOW:**
   - جملة أو جملتين فيها معلومة مفاجئة أو إحصائية صادمة

4. **CTA فيروسي (مهم جداً):**
   - سؤال يجبر على التعليق: "أنتم واش كتستخدمو هاد الشي؟"
   - أو طلب مشاركة: "شارك مع شخص يحتاج هاد المعلومة"
   - أو تحدي: "جرب الخطوة الأولى دابا وقول لنا النتيجة"

5. **الهاشتاجات (سطر منفصل):**
   - 5 هاشتاجات: 3 عربية + 2 إنجليزية
   - مثال: #تقنية_بالدارجة #المغرب_التقني #نصائح_تقنية #TechTips #Technology

**قواعد إضافية:**
- الطول: بين 1500 و 2000 حرف
- من 6 إلى 8 إيموجيات موزعة بذكاء
- لا تكرار ولا حشو
- معلومات دقيقة وقابلة للتحقق
- بدون markdown أو نجوم في النص النهائي

اكتب المنشور مباشرة ابتداءً من الـ HOOK:
"""

    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    delay   = 30

    for attempt in range(1, 4):
        try:
            logger.info(f"📡 توليد المنشور {attempt}/3...")
            res = SESSION.post(url, json=payload, headers=headers, timeout=60)

            if res.status_code == 429:
                logger.warning(f"⚠️ Gemini 429 — انتظار {delay}ث...")
                time.sleep(delay); delay *= 2; continue

            res.raise_for_status()
            post_text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # تنظيف Markdown
            post_text = re.sub(r'^\s*\*\s+',     '• ', post_text, flags=re.MULTILINE)
            post_text = re.sub(r'\*\*(.*?)\*\*',  r'\1', post_text)
            post_text = re.sub(r'\*(.*?)\*',       r'\1', post_text)
            post_text = re.sub(r'#+\s*',           '',    post_text)

            # قطع ذكي إذا تجاوز الحد
            if len(post_text) > MAX_POST_LENGTH:
                post_text = post_text[:MAX_POST_LENGTH].rsplit(' ', 1)[0] + "..."

            logger.info(f"✅ تم توليد المنشور ({len(post_text)} حرف)")
            return post_text

        except requests.exceptions.Timeout:
            logger.error(f"❌ Gemini Timeout (محاولة {attempt})")
        except Exception as e:
            logger.error(f"❌ Gemini Error (محاولة {attempt}): {e}")

        if attempt < 3:
            time.sleep(delay); delay *= 2

    logger.error("❌ فشلت جميع المحاولات مع Gemini")
    return None

# =========================
# جلب الصورة
# =========================
def download_and_resize_image(url: str) -> bool:
    try:
        res = SESSION.get(url, timeout=30)
        if res.status_code != 200 or "image" not in res.headers.get("Content-Type", ""):
            return False
        img = Image.open(io.BytesIO(res.content))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if img.width > MAX_IMAGE_WIDTH:
            ratio = MAX_IMAGE_WIDTH / img.width
            img   = img.resize((MAX_IMAGE_WIDTH, int(img.height * ratio)), Image.LANCZOS)
        img.save(TEMP_IMAGE, "JPEG", quality=85, optimize=True)
        return True
    except Exception as e:
        logger.error(f"خطأ في تحميل الصورة: {e}")
        return False

def validate_image() -> bool:
    try:
        with TEMP_IMAGE.open("rb") as f:
            header = f.read(4)
        return header[:3] == b"\xff\xd8\xff" or header[:4] == b"\x89PNG"
    except Exception:
        return False

# =========================
# ✅ توليد صورة مخصصة بـ Gemini Image
# نفس GEMINI_API_KEY — 500 صورة/يوم مجاناً
# =========================
def generate_image_with_gemini(content_type: str, topic: str) -> bool:
    """
    يولد صورة مخصصة للمنشور باستخدام Gemini 2.5 Flash Image.
    الصورة تعكس موضوع المنشور بالضبط — أفضل من Pexels.
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-preview-05-20:generateContent?key={GEMINI_API_KEY}"
    )

    # Prompt مصمم لصور السوشل ميديا
    IMAGE_STYLE = {
        "حيلة تقنية":  "modern tech flat design, blue and cyan colors, clean minimal style, smartphone or laptop, professional social media post",
        "تطبيق مفيد":  "colorful app interface mockup, material design, smartphone screen, vibrant colors, clean background",
        "أداة AI":      "futuristic AI concept, purple and blue gradient, neural network visualization, glowing elements, digital art",
        "تحذير أمني":  "cybersecurity concept, red and dark colors, shield or lock icon, warning atmosphere, professional design",
    }
    style = IMAGE_STYLE.get(content_type, "modern technology concept, professional, clean design, social media post")

    image_prompt = (
        f"Create a professional social media image for a tech post about: {topic}. "
        f"Style: {style}. "
        f"No text in the image. Wide format 16:9. High quality."
    )

    try:
        logger.info(f"🎨 توليد صورة بـ Gemini Image...")
        res = SESSION.post(
            url,
            json={
                "contents": [{
                    "parts": [{"text": image_prompt}]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"]
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        if res.status_code == 429:
            logger.warning("⚠️ Gemini Image: تجاوز الحد — جاري الانتظار...")
            time.sleep(30)
            return False

        if res.status_code in (404, 400):
            logger.warning(f"⚠️ Gemini Image غير متاح: {res.status_code}")
            return False

        res.raise_for_status()
        parts = res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])

        for part in parts:
            if "inlineData" in part:
                img_data  = part["inlineData"]["data"]
                img_bytes = base64.b64decode(img_data)
                img       = Image.open(io.BytesIO(img_bytes))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                if img.width > MAX_IMAGE_WIDTH:
                    ratio = MAX_IMAGE_WIDTH / img.width
                    img   = img.resize((MAX_IMAGE_WIDTH, int(img.height * ratio)), Image.LANCZOS)
                img.save(TEMP_IMAGE, "JPEG", quality=90, optimize=True)
                logger.info(f"✅ تم توليد صورة بـ Gemini Image ({img.width}x{img.height})")
                return True

        logger.warning("⚠️ Gemini Image: لا توجد صورة في الرد")
        return False

    except Exception as e:
        logger.error(f"❌ Gemini Image Error: {e}")
        return False


def get_image(content_type: str, topic: str, used_images: set) -> bool:
    """
    يجلب صورة مناسبة للمحتوى:
    1. ✅ Gemini Image (مخصصة ومولدة بـ AI)
    2. Pexels API (احتياطي)
    3. Unsplash API (احتياطي)
    4. مكتبة محلية (آخر خيار)
    """
    # كلمات بحث من الموضوع
    search_query = " ".join(topic.split()[:4])

    # 1️⃣ Gemini Image (الأفضل — مخصصة)
    if GEMINI_API_KEY:
        if generate_image_with_gemini(content_type, topic) and validate_image():
            return True
        logger.info("⚠️ Gemini Image فشل — جاري الانتقال لـ Pexels")

    # 2️⃣ Pexels
    if PEXELS_API_KEY:
        try:
            logger.info(f"🔍 [1/3] Pexels: '{search_query}'")
            res = SESSION.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={
                    "query":       search_query,
                    "per_page":    15,
                    "orientation": "landscape",
                    "size":        "large",
                },
                timeout=15,
            )
            photos    = res.json().get("photos", [])
            new_photos = [p for p in photos if p["src"]["large2x"] not in used_images]
            if new_photos or photos:
                chosen = random.choice(new_photos if new_photos else photos)
                if download_and_resize_image(chosen["src"]["large2x"]) and validate_image():
                    logger.info("✅ صورة من Pexels")
                    used_images.add(chosen["src"]["large2x"])
                    save_used_images(used_images)
                    return True
        except Exception as e:
            logger.error(f"❌ Pexels Error: {e}")

    # 2️⃣ Unsplash
    if UNSPLASH_ACCESS_KEY:
        try:
            logger.info(f"🔍 [2/3] Unsplash: '{search_query}'")
            res = SESSION.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                params={
                    "query":          search_query,
                    "per_page":       15,
                    "orientation":    "landscape",
                    "content_filter": "high",
                },
                timeout=15,
            )
            results   = res.json().get("results", [])
            new_photos = [p for p in results if p["urls"]["regular"] not in used_images]
            if new_photos or results:
                chosen = random.choice(new_photos if new_photos else results)
                url    = chosen["urls"]["regular"]
                if download_and_resize_image(url) and validate_image():
                    logger.info("✅ صورة من Unsplash")
                    used_images.add(url)
                    save_used_images(used_images)
                    return True
        except Exception as e:
            logger.error(f"❌ Unsplash Error: {e}")

    # 3️⃣ مكتبة محلية احتياطية
    logger.info("🖼️  [3/3] صورة احتياطية محلية")
    backup_list = IMAGE_LIBRARY.get(content_type, list(IMAGE_LIBRARY.values())[0])
    backup      = random.choice(backup_list)
    if download_and_resize_image(backup) and validate_image():
        logger.info(f"✅ صورة احتياطية ({content_type})")
        return True

    logger.error("❌ فشل تحميل أي صورة")
    return False

# =========================
# النشر على فيسبوك
# =========================
def post_to_facebook(message: str) -> dict | None:
    fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    try:
        with TEMP_IMAGE.open("rb") as img_file:
            res = SESSION.post(
                fb_url,
                data  = {"caption": message, "access_token": FB_PAGE_ACCESS_TOKEN},
                files = {"source": ("post.jpg", img_file, "image/jpeg")},
                timeout=30,
            )
        return res.json()
    except Exception as e:
        logger.error(f"❌ Facebook API Error: {e}")
        return None

# =========================
# الدالة الرئيسية
# =========================
def main():
    session = os.getenv("POST_SESSION", "morning")
    session_label = "🌅 الصباح" if session == "morning" else "🌙 المساء"

    logger.info("=" * 50)
    logger.info(f"🚀 بدء دورة النشر — {session_label}")
    logger.info("=" * 50)

    # 1️⃣ اختيار الموضوع
    content = pick_content_topic()
    logger.info(f"📌 {content['emoji']} {content['type']}: {content['topic']}")

    # 2️⃣ توليد المنشور
    post_text = generate_post(content)
    if not post_text:
        logger.error("❌ فشل توليد المنشور"); return

    # 3️⃣ جلب الصورة
    used_images = load_used_images()
    if not get_image(content["type"], content["topic"], used_images):
        logger.error("❌ فشل تحميل الصورة"); return

    # 4️⃣ النشر على فيسبوك
    logger.info("🚀 جاري النشر على فيسبوك...")
    result = post_to_facebook(post_text)

    if result and "id" in result:
        logger.info(f"✅ تم النشر بنجاح! ID: {result['id']}")

        # حفظ المحتوى المنشور
        posted = load_posted()
        posted.append({
            "id":      result["id"],
            "type":    content["type"],
            "topic":   content["topic"],
            "date":    date.today().isoformat(),
            "session": os.getenv("POST_SESSION", "morning"),
        })
        save_posted(posted)
        logger.info(f"💾 تم حفظ: {content['type']} — {content['topic']}")
    else:
        logger.error(f"❌ فشل النشر: {result}")

    # تنظيف
    try:
        TEMP_IMAGE.unlink(missing_ok=True)
        logger.info("🧹 تم تنظيف الملفات المؤقتة")
    except Exception:
        pass

    logger.info("=" * 50)
    logger.info("🏁 انتهت دورة النشر")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()

