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

# =========================
# تصاميم الصور لكل نوع محتوى
# =========================
DESIGNS = {
    "حيلة تقنية": {
        "bg": [(10, 15, 40), (20, 80, 160)],
        "accent": (0, 180, 255),
        "emoji": "💡",
        "pattern": "circuit",
    },
    "تطبيق مفيد": {
        "bg": [(20, 10, 50), (100, 30, 150)],
        "accent": (180, 80, 255),
        "emoji": "📱",
        "pattern": "dots",
    },
    "أداة AI": {
        "bg": [(5, 20, 35), (10, 100, 120)],
        "accent": (0, 220, 200),
        "emoji": "🤖",
        "pattern": "grid",
    },
    "تحذير أمني": {
        "bg": [(35, 5, 5), (120, 20, 20)],
        "accent": (255, 60, 60),
        "emoji": "🔒",
        "pattern": "lines",
    },
    "مقارنة تقنية": {
        "bg": [(10, 25, 10), (20, 100, 60)],
        "accent": (0, 220, 100),
        "emoji": "⚔️",
        "pattern": "split",
    },
    "خطوات عملية": {
        "bg": [(25, 20, 5), (120, 90, 10)],
        "accent": (255, 200, 0),
        "emoji": "📋",
        "pattern": "dots",
    },
    "إحصائيات صادمة": {
        "bg": [(5, 5, 35), (40, 20, 120)],
        "accent": (100, 150, 255),
        "emoji": "📊",
        "pattern": "grid",
    },
    "سؤال تفاعلي": {
        "bg": [(30, 10, 30), (120, 40, 120)],
        "accent": (255, 100, 200),
        "emoji": "🗳️",
        "pattern": "circles",
    },
    "نصيحة احترافية": {
        "bg": [(20, 15, 5), (90, 65, 15)],
        "accent": (220, 170, 50),
        "emoji": "🎯",
        "pattern": "lines",
    },
    "ترند تقني": {
        "bg": [(5, 5, 5), (40, 5, 80)],
        "accent": (150, 50, 255),
        "emoji": "🔥",
        "pattern": "circuit",
    },
}

# =========================
# أدوات مساعدة للصورة
# =========================
def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for fp in [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

def _draw_gradient(img: Image.Image, c1: tuple, c2: tuple) -> Image.Image:
    W, H = img.size
    draw = ImageDraw.Draw(img)
    for x in range(W):
        r = int(c1[0] + (c2[0] - c1[0]) * x / W)
        g = int(c1[1] + (c2[1] - c1[1]) * x / W)
        b = int(c1[2] + (c2[2] - c1[2]) * x / W)
        draw.line([(x, 0), (x, H)], fill=(r, g, b))
    return img

def _draw_pattern(draw, W: int, H: int, pattern: str, accent: tuple):
    a15, a20, a30, a40 = (*accent, 15), (*accent, 20), (*accent, 30), (*accent, 40)
    if pattern == "circuit":
        for x in range(0, W, 80):
            draw.line([(x, 0), (x, H)], fill=(*accent, 12), width=1)
        for y in range(0, H, 80):
            draw.line([(0, y), (W, y)], fill=(*accent, 12), width=1)
        for x in range(0, W, 80):
            for y in range(0, H, 80):
                draw.ellipse([x-3, y-3, x+3, y+3], fill=(*accent, 35))
    elif pattern == "dots":
        for x in range(0, W, 50):
            for y in range(0, H, 50):
                r = 3 if (x + y) % 100 == 0 else 2
                draw.ellipse([x-r, y-r, x+r, y+r], fill=a30)
    elif pattern == "grid":
        for x in range(0, W, 60):
            draw.line([(x, 0), (x, H)], fill=(*accent, 10), width=1)
        for y in range(0, H, 60):
            draw.line([(0, y), (W, y)], fill=(*accent, 10), width=1)
    elif pattern == "lines":
        for i in range(0, W + H, 60):
            draw.line([(i, 0), (0, i)], fill=(*accent, 12), width=1)
    elif pattern == "circles":
        cx, cy = W // 2, H // 2
        for r in range(50, max(W, H), 80):
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=a20, width=1)
    elif pattern == "split":
        draw.line([(W//2, 0), (W//2, H)], fill=(*accent, 25), width=2)
        for x in range(0, W, 100):
            draw.line([(x, 0), (x, H)], fill=(*accent, 8), width=1)

# =========================
# ✅ توليد الصورة بـ Pillow
# =========================
def create_post_image(content_type: str, topic: str,
                      page_name: str = "تقنية بالدارجة") -> bool:
    """
    ينشئ صورة احترافية مخصصة لكل نوع محتوى بـ Pillow.
    لا يعتمد على أي API خارجي — مجاني 100% وسريع.
    """
    try:
        W, H   = 1200, 630
        design = DESIGNS.get(content_type, DESIGNS["حيلة تقنية"])
        accent = design["accent"]

        # 1. خلفية متدرجة
        img  = Image.new("RGB", (W, H))
        img  = _draw_gradient(img, design["bg"][0], design["bg"][1])
        draw = ImageDraw.Draw(img, "RGBA")

        # 2. زخارف الخلفية
        _draw_pattern(draw, W, H, design["pattern"], accent)

        # 3. شريط لون على اليسار
        draw.rectangle([0, 0, 8, H], fill=(*accent, 255))

        # 4. دائرة كبيرة شفافة (يمين)
        draw.ellipse([W//2, -H//3, W+H//2, H+H//3], fill=(*accent, 8))

        # 5. إيموجي كبير في المنتصف
        emoji_font = _get_font(160)
        emoji      = design["emoji"]
        e_bbox     = draw.textbbox((0, 0), emoji, font=emoji_font)
        e_w  = e_bbox[2] - e_bbox[0]
        e_h  = e_bbox[3] - e_bbox[1]
        e_x  = (W - e_w) // 2 - e_bbox[0]
        e_y  = H // 2 - e_h // 2 - e_bbox[1] - 40
        draw.text((e_x+4, e_y+4), emoji, font=emoji_font, fill=(0, 0, 0, 60))
        draw.text((e_x, e_y), emoji, font=emoji_font, fill=(255, 255, 255, 200))

        # 6. نوع المحتوى فوق الإيموجي
        type_font = _get_font(32)
        type_text = f"[ {content_type} ]"
        t_bbox    = draw.textbbox((0, 0), type_text, font=type_font)
        t_w       = t_bbox[2] - t_bbox[0]
        t_x       = (W - t_w) // 2 - t_bbox[0]
        draw.text((t_x, e_y - 55), type_text,
                  font=type_font, fill=(*accent, 220))

        # 7. خط فاصل
        line_y = e_y + e_h + 25
        line_w = 300
        draw.rectangle(
            [(W-line_w)//2, line_y, (W+line_w)//2, line_y+3],
            fill=(*accent, 180)
        )

        # 8. الموضوع أسفل الإيموجي
        topic_font = _get_font(38)
        topic_text = topic
        max_w      = W - 120
        while True:
            tb = draw.textbbox((0, 0), topic_text, font=topic_font)
            if tb[2] - tb[0] <= max_w or len(topic_text) < 10:
                break
            topic_text = topic_text[:-4] + "..."
        tb  = draw.textbbox((0, 0), topic_text, font=topic_font)
        t_w = tb[2] - tb[0]
        t_x = (W - t_w) // 2 - tb[0]
        t_y = line_y + 20
        draw.text((t_x+2, t_y+2), topic_text, font=topic_font, fill=(0, 0, 0, 100))
        draw.text((t_x, t_y),     topic_text, font=topic_font, fill="white")

        # 9. Watermark أسفل يسار
        wm_font = _get_font(28)
        wm_text = f"🤖 {page_name}"
        wm_bbox = draw.textbbox((0, 0), wm_text, font=wm_font)
        wm_w    = wm_bbox[2] - wm_bbox[0]
        wm_h    = wm_bbox[3] - wm_bbox[1]
        padding = 12
        margin  = 20
        wm_x    = margin
        wm_y    = H - wm_h - padding * 2 - margin
        draw.rounded_rectangle(
            [wm_x-padding, wm_y-padding,
             wm_x+wm_w+padding, wm_y+wm_h+padding],
            radius=8, fill=(0, 0, 0, 160)
        )
        draw.text((wm_x, wm_y), wm_text, font=wm_font,
                  fill=(255, 255, 255, 230))

        # حفظ الصورة
        img = img.convert("RGB")
        img.save(TEMP_IMAGE, "JPEG", quality=90, optimize=True)
        logger.info(f"✅ تم إنشاء صورة Pillow: {content_type}")
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
    """
    ✅ نظام الصور الجديد:
    1. Pillow: صورة مخصصة لكل نوع (مجاني + سريع + لا API)
    2. مكتبة محلية: آخر خيار
    """
    # 1️⃣ Pillow (الأفضل — مخصصة ومجانية)
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
                img   = img.resize((MAX_IMAGE_WIDTH, int(img.height * ratio)), Image.LANCZOS)
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

