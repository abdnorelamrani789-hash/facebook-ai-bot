import os
import re
import json
import time
import base64
import random
import logging
import requests
import io
import math
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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
MAX_POST_LENGTH   = 3000

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
    # ══════════════════════════════════════════
    # 6 أنواع جديدة ✅
    # ══════════════════════════════════════════
    {
        "type":  "مقارنة تقنية",
        "emoji": "⚔️",
        "topics": [
            "iPhone ولا Android — الجواب الحقيقي اللي ما كيقولوهش",
            "ChatGPT ولا Gemini — أيهما أفضل في 2025؟",
            "Windows ولا MacOS — شنو تختار وعلاش؟",
            "Samsung ولا Apple — مقارنة شاملة وصريحة",
            "WiFi ولا بيانات الجوال — أيهما أسرع وأأمن؟",
            "تطبيقات مدفوعة ولا مجانية — الفرق الحقيقي",
            "Chrome ولا Firefox ولا Edge — المتصفح الأفضل",
            "WhatsApp ولا Telegram — أيهما أفضل وأأمن؟",
            "SSD ولا HDD — لماذا SSD يغير كل شيء؟",
            "5G ولا 4G — هل يستحق الترقية الآن؟",
        ]
    },
    {
        "type":  "خطوات عملية",
        "emoji": "📋",
        "topics": [
            "كيف تبدأ تتعلم البرمجة من الصفر في 2025",
            "كيف تحمي خصوصيتك على الإنترنت خطوة بخطوة",
            "كيف تنظم وقتك باستخدام التكنولوجيا",
            "كيف تبني حضوراً رقمياً احترافياً",
            "كيف تختار هاتفاً جديداً بذكاء",
            "كيف تسرع هاتفك القديم بدون شراء جديد",
            "كيف تحقق دخلاً من الإنترنت خطوة بخطوة",
            "كيف تتعلم لغة إنجليزية بالتكنولوجيا مجاناً",
            "كيف تنشئ CV احترافياً باستخدام AI",
            "كيف تحمي أطفالك على الإنترنت",
        ]
    },
    {
        "type":  "إحصائيات صادمة",
        "emoji": "📊",
        "topics": [
            "أرقام صادمة عن استخدام الهاتف لن تصدقها",
            "إحصائيات مرعبة عن الاختراق الإلكتروني في 2025",
            "أرقام عن وقتك على السوشل ميديا ستصدمك",
            "إحصائيات عن AI وكيف غيّر سوق العمل",
            "أرقام عن الجرائم الإلكترونية في العالم العربي",
            "إحصائيات عن التسوق الإلكتروني في المغرب",
            "أرقام عن مستخدمي الإنترنت في إفريقيا",
            "إحصائيات صادمة عن بيانات المستخدمين المسربة",
            "أرقام عن الوقت الضائع في السوشل ميديا يومياً",
            "إحصائيات عن نمو AI في السنوات القادمة",
        ]
    },
    {
        "type":  "سؤال تفاعلي",
        "emoji": "🗳️",
        "topics": [
            "أنتم فريق iPhone ولا Android؟ ولماذا؟",
            "كم ساعة تقضي على هاتفك يومياً؟",
            "ما هو التطبيق الذي لا تستطيع العيش بدونه؟",
            "هل تثق في تخزين بياناتك على السحابة؟",
            "ما هو أكثر شيء يزعجك في هاتفك؟",
            "هل جربت أدوات AI في عملك؟ ما رأيك؟",
            "ما هي أول حيلة تقنية تعلمتها غيرت حياتك؟",
            "هل تفضل العمل من المنزل أم المكتب؟ دور التقنية؟",
            "ما هو الجهاز التقني الذي لا تستطيع العيش بدونه؟",
            "هل تعتقد أن AI سيأخذ وظيفتك في المستقبل؟",
        ]
    },
    {
        "type":  "نصيحة احترافية",
        "emoji": "🎯",
        "topics": [
            "نصائح تقنية يستخدمها المحترفون ولا يشاركونها",
            "كيف يستخدم المبرمجون الكمبيوتر بطريقة مختلفة",
            "أسرار المصورين المحترفين في تصوير الهاتف",
            "كيف يدير المديرالناجح وقته باستخدام التقنية",
            "نصائح خبراء الأمن الإلكتروني لحماية نفسك",
            "كيف يبحث المحترفون على Google بطريقة مختلفة",
            "أسرار يوتيوبرز الناجحين في إنشاء المحتوى",
            "كيف يتعلم المبرمجون الناجحون مهارات جديدة",
            "نصائح خبراء SEO لظهورك على الإنترنت",
            "كيف يستخدم رجال الأعمال AI لزيادة الإنتاجية",
        ]
    },
    {
        "type":  "ترند تقني",
        "emoji": "🔥",
        "topics": [
            "أبرز التقنيات التي ستغير حياتك في 2025",
            "تقنيات اختفت وأخرى ستختفي قريباً",
            "مستقبل الهواتف الذكية بعد 5 سنوات",
            "كيف ستغير AI طريقة عملنا بحلول 2030",
            "أحدث ترندات التقنية التي يتحدث عنها الجميع",
            "تقنيات الواقع الافتراضي وأين وصلنا",
            "مستقبل العمل عن بُعد والتقنيات الداعمة له",
            "تقنيات قادمة ستجعل حياتك أسهل بكثير",
            "كيف ستبدو السيارات الذكية في المستقبل القريب",
            "مستقبل الذكاء الاصطناعي في التعليم",
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
    "مقارنة تقنية": [
        "https://images.pexels.com/photos/1779487/pexels-photo-1779487.jpeg",
        "https://images.pexels.com/photos/2582937/pexels-photo-2582937.jpeg",
        "https://images.pexels.com/photos/1714208/pexels-photo-1714208.jpeg",
        "https://images.pexels.com/photos/3861958/pexels-photo-3861958.jpeg",
    ],
    "خطوات عملية": [
        "https://images.pexels.com/photos/3184291/pexels-photo-3184291.jpeg",
        "https://images.pexels.com/photos/1181298/pexels-photo-1181298.jpeg",
        "https://images.pexels.com/photos/3184360/pexels-photo-3184360.jpeg",
        "https://images.pexels.com/photos/6804073/pexels-photo-6804073.jpeg",
    ],
    "إحصائيات صادمة": [
        "https://images.pexels.com/photos/590022/pexels-photo-590022.jpeg",
        "https://images.pexels.com/photos/669615/pexels-photo-669615.jpeg",
        "https://images.pexels.com/photos/265087/pexels-photo-265087.jpeg",
        "https://images.pexels.com/photos/1181671/pexels-photo-1181671.jpeg",
    ],
    "سؤال تفاعلي": [
        "https://images.pexels.com/photos/3184465/pexels-photo-3184465.jpeg",
        "https://images.pexels.com/photos/1181533/pexels-photo-1181533.jpeg",
        "https://images.pexels.com/photos/7688336/pexels-photo-7688336.jpeg",
        "https://images.pexels.com/photos/3184339/pexels-photo-3184339.jpeg",
    ],
    "نصيحة احترافية": [
        "https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg",
        "https://images.pexels.com/photos/1181244/pexels-photo-1181244.jpeg",
        "https://images.pexels.com/photos/3182812/pexels-photo-3182812.jpeg",
        "https://images.pexels.com/photos/3184287/pexels-photo-3184287.jpeg",
    ],
    "ترند تقني": [
        "https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg",
        "https://images.pexels.com/photos/2599244/pexels-photo-2599244.jpeg",
        "https://images.pexels.com/photos/3861972/pexels-photo-3861972.jpeg",
        "https://images.pexels.com/photos/1714208/pexels-photo-1714208.jpeg",
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
    "morning": ["حيلة تقنية", "أداة AI", "خطوات عملية", "نصيحة احترافية", "ترند تقني"],
    # المساء: محتوى تفاعلي بعد يوم عمل
    "evening": ["تحذير أمني", "مقارنة تقنية", "سؤال تفاعلي", "إحصائيات صادمة", "تطبيق مفيد"],
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
   - ⚠️ كل هاشتاج لازم يبدأ بعلامة # بدون استثناء
   - مثال: #تقنية_بالدارجة #المغرب_التقني #نصائح_تقنية #TechTips #Technology
   - ❌ ممنوع: تقنية_بالدارجة بدون # في البداية

**قواعد إضافية:**
- الطول: بين 1800 و 2500 حرف
- من 6 إلى 8 إيموجيات موزعة بذكاء
- لا تكرار ولا حشو
- معلومات دقيقة وقابلة للتحقق
- بدون markdown أو نجوم في النص النهائي
- ⚠️ مهم جداً: المنشور لازم يكون مكتمل 100% — لا تقطعه في المنتصف
- ⚠️ لازم ينتهي بـ: سؤال تفاعلي + الهاشتاجات — هادين العنصرين إلزاميين

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


            # ✅ إصلاح الهاشتاجات تلقائياً — نبحث عن سطر الهاشتاجات ونضيف #
            def fix_hashtag_line(line: str) -> str:
                # نتعرف على سطر الهاشتاجات: كلمات مفصولة بمسافات بدون نقطة أو فاصلة
                stripped = line.strip()
                if not stripped:
                    return line
                words = stripped.split()
                # شروط سطر الهاشتاجات:
                # 1. من 3 لـ 6 كلمات
                # 2. كل كلمة تحتوي حروف أو أرقام أو _ فقط
                # 3. على الأقل كلمة واحدة تحتوي _
                if not (3 <= len(words) <= 6):
                    return line
                for w in words:
                    if not re.match(r'^#?[\u0600-\u06FFa-zA-Z0-9_]+$', w):
                        return line
                if not any('_' in w for w in words):
                    return line
                if any(c in stripped for c in ['.', '!', '?', '؟', '،', ':']):
                    return line
                return ' '.join(w if w.startswith('#') else f'#{w}' for w in words)

            post_text = '\n'.join(fix_hashtag_line(l) for l in post_text.split('\n'))


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
# تصاميم الصور v2 — أيقونات هندسية احترافية
# =========================
DESIGNS = {
    "حيلة تقنية":     {"bg1": (8,12,35),  "bg2": (15,60,130), "accent": (0,180,255),  "icon": "lightbulb"},
    "تطبيق مفيد":     {"bg1": (18,8,45),  "bg2": (80,25,140), "accent": (180,80,255), "icon": "phone"},
    "أداة AI":         {"bg1": (4,18,30),  "bg2": (8,85,105),  "accent": (0,220,200),  "icon": "robot"},
    "تحذير أمني":     {"bg1": (30,4,4),   "bg2": (110,15,15), "accent": (255,55,55),  "icon": "shield"},
    "مقارنة تقنية":   {"bg1": (8,22,8),   "bg2": (15,90,50),  "accent": (0,210,90),   "icon": "compare"},
    "خطوات عملية":    {"bg1": (22,18,4),  "bg2": (110,80,8),  "accent": (255,195,0),  "icon": "steps"},
    "إحصائيات صادمة": {"bg1": (4,4,30),   "bg2": (35,18,110), "accent": (90,140,255), "icon": "chart"},
    "سؤال تفاعلي":    {"bg1": (28,8,28),  "bg2": (110,35,110),"accent": (255,95,195), "icon": "question"},
    "نصيحة احترافية": {"bg1": (18,13,4),  "bg2": (85,60,12),  "accent": (215,165,45), "icon": "target"},
    "ترند تقني":       {"bg1": (4,4,4),    "bg2": (38,4,75),   "accent": (145,45,255), "icon": "fire"},
}

def _get_font(size: int):
    for fp in [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if Path(fp).exists():
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def _draw_gradient(img, c1, c2):
    W, H = img.size
    draw = ImageDraw.Draw(img)
    for x in range(W):
        r = int(c1[0] + (c2[0]-c1[0]) * x/W)
        g = int(c1[1] + (c2[1]-c1[1]) * x/W)
        b = int(c1[2] + (c2[2]-c1[2]) * x/W)
        draw.line([(x,0),(x,H)], fill=(r,g,b))
    return img

def _draw_icon(draw, cx, cy, size, icon_type, accent):
    """أيقونات هندسية مرسومة بالكود — لا تعتمد على fonts"""
    s  = size
    lw = max(4, s // 20)

    if icon_type == "lightbulb":
        draw.ellipse([cx-s//2, cy-s//2, cx+s//2, cy+s//4], outline=accent, width=lw)
        draw.rectangle([cx-s//5, cy+s//4, cx+s//5, cy+s//2], outline=accent, width=lw)
        draw.line([(cx-s//4, cy+s//2),(cx+s//4, cy+s//2)], fill=accent, width=lw)
        for angle in [0,45,90,135,180,225,270,315]:
            rad = math.radians(angle)
            x1 = cx+int((s//2+15)*math.cos(rad)); y1 = cy+int((s//2+15)*math.sin(rad))
            x2 = cx+int((s//2+30)*math.cos(rad)); y2 = cy+int((s//2+30)*math.sin(rad))
            draw.line([(x1,y1),(x2,y2)], fill=(*accent,150), width=max(2,lw//2))

    elif icon_type == "phone":
        pw,ph = s//3, s*2//3
        draw.rounded_rectangle([cx-pw,cy-ph//2,cx+pw,cy+ph//2], radius=pw//3, outline=accent, width=lw)
        draw.ellipse([cx-4,cy+ph//2-20,cx+4,cy+ph//2-12], fill=accent)
        draw.line([(cx-s//5,cy-ph//2+12),(cx+s//5,cy-ph//2+12)], fill=accent, width=lw)

    elif icon_type == "robot":
        hw = s//2
        draw.rounded_rectangle([cx-hw,cy-hw//2,cx+hw,cy+hw//2], radius=hw//6, outline=accent, width=lw)
        ew = s//8
        draw.ellipse([cx-s//4-ew,cy-ew,cx-s//4+ew,cy+ew], fill=accent)
        draw.ellipse([cx+s//4-ew,cy-ew,cx+s//4+ew,cy+ew], fill=accent)
        draw.arc([cx-s//4,cy+s//12,cx+s//4,cy+s//4], start=0, end=180, fill=accent, width=lw)
        draw.line([(cx,cy-hw//2),(cx,cy-hw//2-s//4)], fill=accent, width=lw)
        draw.ellipse([cx-6,cy-hw//2-s//4-6,cx+6,cy-hw//2-s//4+6], fill=accent)

    elif icon_type == "shield":
        pts = [(cx,cy-s//2),(cx+s//2,cy-s//4),(cx+s//2,cy+s//8),
               (cx,cy+s//2),(cx-s//2,cy+s//8),(cx-s//2,cy-s//4)]
        draw.polygon(pts, outline=accent, width=lw)
        draw.line([(cx-s//5,cy),(cx,cy+s//5),(cx+s//4,cy-s//6)], fill=accent, width=lw*2)

    elif icon_type == "compare":
        draw.line([(cx-s//3,cy-s//4),(cx+s//3,cy-s//4)], fill=accent, width=lw)
        draw.polygon([(cx+s//3,cy-s//4),(cx+s//3-s//8,cy-s//4-s//10),(cx+s//3-s//8,cy-s//4+s//10)], fill=accent)
        draw.line([(cx+s//3,cy+s//4),(cx-s//3,cy+s//4)], fill=accent, width=lw)
        draw.polygon([(cx-s//3,cy+s//4),(cx-s//3+s//8,cy+s//4-s//10),(cx-s//3+s//8,cy+s//4+s//10)], fill=accent)
        draw.line([(cx,cy-s//2),(cx,cy+s//2)], fill=(*accent,80), width=2)

    elif icon_type == "steps":
        step = s//4
        for i in range(4):
            x1 = cx-s//2+i*step; y1 = cy+s//4-i*step//2
            draw.rectangle([x1,y1,x1+step,y1+(4-i)*step//2], outline=accent, width=lw)

    elif icon_type == "chart":
        bars = [0.4,0.7,0.5,0.9,0.6]
        bw   = s//7
        for i,h in enumerate(bars):
            bh=int(s*h*0.7); bx=cx-s//2+i*(bw+4); by=cy+s//3
            draw.rectangle([bx,by-bh,bx+bw,by], fill=(*accent,180), outline=accent, width=1)
        draw.line([(cx-s//2,cy+s//3),(cx+s//2,cy+s//3)], fill=accent, width=lw)

    elif icon_type == "question":
        draw.arc([cx-s//3,cy-s//2,cx+s//3,cy], start=240, end=60, fill=accent, width=lw*2)
        draw.line([(cx,cy),(cx,cy+s//5)], fill=accent, width=lw*2)
        draw.ellipse([cx-5,cy+s//4,cx+5,cy+s//4+10], fill=accent)

    elif icon_type == "target":
        for r in [s//2,s//3,s//6]:
            draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline=accent, width=lw)
        draw.ellipse([cx-8,cy-8,cx+8,cy+8], fill=accent)
        draw.line([(cx,cy-s//2-15),(cx,cy+s//2+15)], fill=(*accent,100), width=1)
        draw.line([(cx-s//2-15,cy),(cx+s//2+15,cy)], fill=(*accent,100), width=1)

    elif icon_type == "fire":
        pts = [(cx,cy-s//2),(cx+s//4,cy-s//4),(cx+s//3,cy+s//6),
               (cx+s//6,cy+s//3),(cx,cy+s//2),(cx-s//6,cy+s//3),
               (cx-s//3,cy+s//6),(cx-s//4,cy-s//4)]
        draw.polygon(pts, outline=accent, width=lw)
        inner = [(cx,cy-s//5),(cx+s//8,cy+s//8),(cx,cy+s//3),(cx-s//8,cy+s//8)]
        draw.polygon(inner, fill=(*accent,120))

# =========================
# ✅ توليد الصورة v2
# =========================
def create_post_image(content_type: str, topic: str,
                      page_name: str = "تقنية بالدارجة") -> bool:
    try:
        W, H   = 1200, 630
        design = DESIGNS.get(content_type, DESIGNS["حيلة تقنية"])
        accent = design["accent"]

        # خلفية متدرجة
        img  = Image.new("RGB", (W, H))
        img  = _draw_gradient(img, design["bg1"], design["bg2"])
        draw = ImageDraw.Draw(img, "RGBA")

        # شبكة خفيفة
        for x in range(0, W, 70):
            draw.line([(x,0),(x,H)], fill=(*accent,10), width=1)
        for y in range(0, H, 70):
            draw.line([(0,y),(W,y)], fill=(*accent,10), width=1)

        # دوائر زخرفية
        for r, a in [(350,8),(250,12),(150,18)]:
            draw.ellipse([W*3//4-r, H//2-r, W*3//4+r, H//2+r],
                         outline=(*accent,a), width=2)

        # شريط يسار
        for i in range(12):
            draw.rectangle([i,0,i+1,H], fill=(*accent,int(255*(1-i/12))))

        # شريط علوي
        draw.rectangle([0,0,W,3], fill=(*accent,180))

        # توهج خلف الأيقونة
        icon_cx, icon_cy, icon_size = W//2, H//2-40, 120
        for r in range(icon_size, icon_size-40, -8):
            draw.ellipse([icon_cx-r,icon_cy-r,icon_cx+r,icon_cy+r],
                         fill=(*accent,int(30*(icon_size-r)/40)))

        # الأيقونة الهندسية
        _draw_icon(draw, icon_cx, icon_cy, icon_size, design["icon"], accent)

        # نوع المحتوى
        type_font = _get_font(30)
        type_text = f"— {content_type} —"
        tb = draw.textbbox((0,0), type_text, font=type_font)
        tx = (W-(tb[2]-tb[0]))//2 - tb[0]
        draw.text((tx, icon_cy-icon_size-45), type_text,
                  font=type_font, fill=(*accent,200))

        # خط فاصل
        line_y = icon_cy+icon_size+30
        draw.rectangle([(W-400)//2, line_y, (W+400)//2, line_y+2],
                       fill=(*accent,150))

        # الموضوع
        topic_font = _get_font(42)
        t = topic
        while True:
            tb = draw.textbbox((0,0), t, font=topic_font)
            if tb[2]-tb[0] <= W-140 or len(t)<10: break
            t = t[:-4]+"..."
        tb  = draw.textbbox((0,0), t, font=topic_font)
        t_x = (W-(tb[2]-tb[0]))//2 - tb[0]
        t_y = line_y+18
        draw.rectangle([t_x-20,t_y-8,t_x+(tb[2]-tb[0])+20,t_y+(tb[3]-tb[1])+8],
                       fill=(0,0,0,60))
        draw.text((t_x+2,t_y+2), t, font=topic_font, fill=(0,0,0,90))
        draw.text((t_x,t_y),     t, font=topic_font, fill="white")

        # Watermark
        wm_font = _get_font(26)
        wm_text = f"| {page_name}"
        wm_bbox = draw.textbbox((0,0), wm_text, font=wm_font)
        wm_w    = wm_bbox[2]-wm_bbox[0]
        wm_h    = wm_bbox[3]-wm_bbox[1]
        pad,mx  = 10, 20
        wx      = mx
        wy      = H-wm_h-pad*2-mx
        draw.rounded_rectangle([wx-pad,wy-pad,wx+wm_w+pad*3,wy+wm_h+pad],
                                radius=6, fill=(0,0,0,170))
        draw.ellipse([wx,wy+wm_h//2-5,wx+10,wy+wm_h//2+5], fill=accent)
        draw.text((wx+14,wy), wm_text, font=wm_font, fill=(255,255,255,230))

        img.convert("RGB").save(TEMP_IMAGE, "JPEG", quality=92, optimize=True)
        logger.info(f"✅ صورة Pillow v2: {content_type}")
        return True

    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء الصورة: {e}")
        return False

def validate_image() -> bool:
    try:
        with TEMP_IMAGE.open("rb") as f:
            header = f.read(4)
        return header[:3] == b"\xff\xd8\xff" or header[:4] == b"\x89PNG"
    except Exception:
        return False

# =========================
# الدالة الرئيسية لجلب الصورة
# =========================
def get_image(content_type: str, topic: str, used_images: set) -> bool:
    # 1️⃣ Pillow v2 (مجاني + سريع + مخصص)
    if create_post_image(content_type, topic) and validate_image():
        return True

    # 2️⃣ مكتبة محلية احتياطية
    logger.warning("⚠️ فشل Pillow — استخدام صورة احتياطية")
    backup_list = IMAGE_LIBRARY.get(content_type, list(IMAGE_LIBRARY.values())[0])
    backup_url  = random.choice(backup_list)
    try:
        res = SESSION.get(backup_url, timeout=20)
        if res.status_code == 200:
            img = Image.open(io.BytesIO(res.content)).convert("RGB")
            if img.width > MAX_IMAGE_WIDTH:
                ratio = MAX_IMAGE_WIDTH / img.width
                img   = img.resize((MAX_IMAGE_WIDTH, int(img.height*ratio)), Image.LANCZOS)
            img.save(TEMP_IMAGE, "JPEG", quality=85, optimize=True)
            if validate_image():
                logger.info(f"✅ صورة احتياطية ({content_type})")
                return True
    except Exception as e:
        logger.error(f"❌ فشل الصورة الاحتياطية: {e}")

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

