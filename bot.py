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
        img = add_watermark(img)
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
# إضافة Watermark للصورة
# =========================
def add_watermark(img: Image.Image, text: str = "تقنية بالدارجة") -> Image.Image:
    """
    يضيف Watermark احترافي للصورة:
    - نص الصفحة في الركن السفلي الأيسر
    - خلفية شبه شفافة خلف النص
    - يتكيف مع حجم الصورة تلقائياً
    """
    try:
        img      = img.convert("RGBA")
        W, H     = img.size
        overlay  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw     = ImageDraw.Draw(overlay)

        # حجم الخط بناءً على عرض الصورة
        font_size = max(22, W // 45)

        # البحث عن أفضل font متاح
        font_paths = [
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        font = ImageFont.load_default()
        for fp in font_paths:
            if Path(fp).exists():
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except Exception:
                    continue

        # حساب حجم النص
        bbox    = draw.textbbox((0, 0), text, font=font)
        txt_w   = bbox[2] - bbox[0]
        txt_h   = bbox[3] - bbox[1]
        padding = 12

        # موقع Watermark: ركن أسفل يسار
        margin = 20
        x      = margin
        y      = H - txt_h - padding * 2 - margin

        # خلفية داكنة شفافة خلف النص
        draw.rounded_rectangle(
            [x - padding, y - padding,
             x + txt_w + padding, y + txt_h + padding],
            radius = 8,
            fill   = (0, 0, 0, 160),
        )
        # 🤖 إيموجي الصفحة قبل النص
        full_text  = "🤖 " + text
        # حساب الحجم الكامل للنص مع الإيموجي
        full_bbox  = draw.textbbox((0, 0), full_text, font=font)
        full_w     = full_bbox[2] - full_bbox[0]
        # تحديث عرض الخلفية ليناسب النص الكامل
        draw.rounded_rectangle(
            [x - padding, y - padding,
             x + full_w + padding, y + txt_h + padding],
            radius = 8,
            fill   = (0, 0, 0, 160),
        )
        # رسم النص مع الإيموجي
        draw.text(
            (x, y),
            full_text,
            font = font,
            fill = (255, 255, 255, 230),
        )

        # دمج الـ overlay مع الصورة الأصلية
        result = Image.alpha_composite(img, overlay).convert("RGB")
        logger.info(f"✅ تم إضافة Watermark")
        return result

    except Exception as e:
        logger.warning(f"⚠️ فشل إضافة Watermark: {e}")
        return img.convert("RGB")



# =========================
# قاموس كلمات البحث الذكية لـ Pexels
# كل نوع محتوى عنده 5 كلمات بحث مختلفة
# يتم اختيار واحدة عشوائياً كل مرة
# =========================
# =========================
# توليد صورة بـ Gemini Image (الصحيح)
# =========================
def generate_image_with_gemini(content_type: str, topic: str) -> bool:
    IMAGE_STYLE = {
        "حيلة تقنية":      "modern tech smartphone with glowing blue interface, dark background, professional social media",
        "تطبيق مفيد":      "colorful mobile app on smartphone screen, material design, vibrant clean background",
        "أداة AI":          "futuristic AI neural network visualization, purple blue gradient, glowing particles",
        "تحذير أمني":      "cybersecurity red warning, dark background, digital lock shield glowing",
        "مقارنة تقنية":    "two modern smartphones side by side, clean white studio background, professional",
        "خطوات عملية":     "person learning on laptop, clean desk, warm lighting, productive workspace",
        "إحصائيات صادمة":  "colorful data charts on screen, analytics dashboard, blue orange colors",
        "سؤال تفاعلي":     "diverse group using smartphones, social interaction, warm modern atmosphere",
        "نصيحة احترافية":  "professional clean desk setup, laptop notebook coffee, warm productive lighting",
        "ترند تقني":        "futuristic city with holographic technology, neon blue glow, innovation",
    }
    style = IMAGE_STYLE.get(content_type, "modern technology concept, professional, clean, social media")
    prompt = (
        f"Professional social media image for tech post about: {topic}. "
        f"Style: {style}. No text in image. Wide landscape 16:9. Ultra high quality."
    )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-image-preview:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}
    }

    try:
        logger.info("🎨 توليد صورة بـ Gemini Image...")
        res = SESSION.post(url, json=payload,
                          headers={"Content-Type": "application/json"},
                          timeout=60)

        if res.status_code == 429:
            logger.warning("⚠️ Gemini Image: تجاوز الحد")
            return False
        if res.status_code in (400, 404):
            logger.warning(f"⚠️ Gemini Image غير متاح: {res.status_code}")
            return False

        res.raise_for_status()
        parts = res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])

        for part in parts:
            inline = part.get("inlineData", {})
            if inline.get("data"):
                img_bytes = base64.b64decode(inline["data"])
                img = Image.open(io.BytesIO(img_bytes))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                if img.width > MAX_IMAGE_WIDTH:
                    ratio = MAX_IMAGE_WIDTH / img.width
                    img = img.resize((MAX_IMAGE_WIDTH, int(img.height * ratio)), Image.LANCZOS)
                img = add_watermark(img)
                img.save(TEMP_IMAGE, "JPEG", quality=90, optimize=True)
                logger.info(f"✅ Gemini Image: {img.width}x{img.height}")
                return True

        logger.warning("⚠️ Gemini Image: لا توجد صورة في الرد")
        return False

    except Exception as e:
        logger.error(f"❌ Gemini Image Error: {e}")
        return False


PEXELS_QUERIES = {
    "حيلة تقنية": [
        "smartphone hidden features",
        "phone tips tricks technology",
        "mobile technology lifestyle",
        "tech gadgets close up",
        "person using smartphone",
    ],
    "تطبيق مفيد": [
        "mobile app interface",
        "productivity smartphone app",
        "phone screen colorful apps",
        "person using phone apps",
        "technology mobile productivity",
    ],
    "أداة AI": [
        "artificial intelligence technology",
        "machine learning digital",
        "futuristic AI robot technology",
        "data science computer",
        "neural network technology glow",
    ],
    "تحذير أمني": [
        "cybersecurity digital protection",
        "data privacy internet security",
        "hacker cyber attack dark",
        "password security lock",
        "digital security shield",
    ],
    "مقارنة تقنية": [
        "smartphone comparison technology",
        "two phones side by side",
        "tech gadgets review",
        "apple vs android phone",
        "technology devices comparison",
    ],
    "خطوات عملية": [
        "step by step learning technology",
        "person learning coding laptop",
        "online course digital skills",
        "tutorial technology screen",
        "professional learning computer",
    ],
    "إحصائيات صادمة": [
        "data analytics dashboard",
        "business charts statistics",
        "digital infographic screen",
        "data visualization technology",
        "statistics graphs technology",
    ],
    "سؤال تفاعلي": [
        "people using smartphones together",
        "social media community interaction",
        "group people technology",
        "friends phones social",
        "community digital interaction",
    ],
    "نصيحة احترافية": [
        "professional workspace desk setup",
        "productivity laptop notebook",
        "business professional technology",
        "clean modern desk computer",
        "expert working technology",
    ],
    "ترند تقني": [
        "future technology innovation",
        "emerging technology digital",
        "tech trend modern city",
        "innovation startup technology",
        "technology future concept",
    ],
}

def get_image(content_type: str, topic: str, used_images: set) -> bool:
    """
    ✅ نظام صور ذكي بـ Pexels فقط:
    1. يبحث بكلمات إنجليزية مخصصة لكل نوع محتوى
    2. يجرب 3 كلمات بحث مختلفة إذا فشلت الأولى
    3. يتجنب الصور المستخدمة مسبقاً
    4. يفضل الصور الأفقية عالية الجودة
    5. مكتبة محلية كآخر خيار
    """
    queries = PEXELS_QUERIES.get(content_type, ["technology innovation", "digital tech"])
    random.shuffle(queries)  # خلط الترتيب كل مرة

    # 1️⃣ Gemini Image (إذا كان Pro متاحاً)
    if GEMINI_API_KEY:
        if generate_image_with_gemini(content_type, topic) and validate_image():
            return True
        logger.info("⚠️ Gemini Image فشل — جاري الانتقال لـ Pexels")

    # 2️⃣ Pexels — يجرب 3 كلمات بحث مختلفة
    if PEXELS_API_KEY:
        for i, search_query in enumerate(queries[:3]):
            try:
                logger.info(f"🔍 Pexels [{i+1}/3]: '{search_query}'")
                res = SESSION.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": PEXELS_API_KEY},
                    params={
                        "query":       search_query,
                        "per_page":    20,          # أكثر خيارات
                        "orientation": "landscape",
                        "size":        "large",
                    },
                    timeout=15,
                )
                res.raise_for_status()
                photos    = res.json().get("photos", [])
                new_photos = [p for p in photos if p["src"]["large2x"] not in used_images]
                pool       = new_photos if new_photos else photos

                if pool:
                    # اختيار من أفضل 5 صور (الأولى في النتائج = الأكثر صلة)
                    chosen = random.choice(pool[:5])
                    url    = chosen["src"]["large2x"]
                    if download_and_resize_image(url) and validate_image():
                        logger.info(f"✅ صورة من Pexels (ID: {chosen['id']})")
                        used_images.add(url)
                        save_used_images(used_images)
                        return True

            except Exception as e:
                logger.error(f"❌ Pexels Error [{i+1}]: {e}")

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

