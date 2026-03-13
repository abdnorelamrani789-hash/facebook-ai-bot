import os
import re
import json
import time
import random
import logging
import requests
import textwrap
import feedparser
import io
import base64
from pathlib import Path
from datetime import date
from urllib.parse import urlparse, urlunparse
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
NEWS_API_KEY         = os.getenv("NEWS_API_KEY")
PEXELS_API_KEY       = os.getenv("PEXELS_API_KEY")
UNSPLASH_ACCESS_KEY  = os.getenv("UNSPLASH_ACCESS_KEY")
MODEL_NAME           = "gemini-2.5-flash"

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise EnvironmentError("❌ متغيرات البيئة المطلوبة غير موجودة")

# =========================
# الثوابت
# =========================
VIDEO_POSTED_FILE = Path("video_posted_news.json")   # ملف منفصل عن bot.py
TEMP_AUDIO        = Path("temp_audio.mp3")
TEMP_FRAME        = Path("temp_frame.jpg")
TEMP_VIDEO        = Path("temp_video.mp4")

# أبعاد الفيديو Reels (9:16)
VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
FPS          = 24
DURATION     = 40  # ثانية

# =========================
# Session
# =========================
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/133.0.0.0"
})

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

def normalize_link(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', '')).rstrip('/')

# =========================
# تتبع الأخبار المنشورة (للفيديو فقط)
# =========================
def load_video_posted() -> set:
    data = _load_json(VIDEO_POSTED_FILE, [])
    return set(data) if isinstance(data, list) else set()

def save_video_posted(posted: set):
    _save_json(VIDEO_POSTED_FILE, list(posted))

# =========================
# جلب خبر جديد (منفصل عن bot.py)
# =========================
def get_news_for_video() -> dict | None:
    """
    يجلب خبراً جديداً مختلفاً عن خبر المنشور.
    يستخدم video_posted_news.json منفصل.
    """
    posted = load_video_posted()

    # ── NewsAPI أولاً ──────────────────────────────
    if NEWS_API_KEY:
        logger.info("📡 جلب خبر الفيديو من NewsAPI...")
        try:
            res = SESSION.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        "technology OR AI OR smartphone OR innovation",
                    "language": "en",
                    "pageSize": 20,
                    "sortBy":   "publishedAt",
                    "apiKey":   NEWS_API_KEY,
                },
                timeout=15,
            )
            res.raise_for_status()
            articles = res.json().get("articles", [])

            new_articles = [
                a for a in articles
                if a.get("url")
                and a.get("title")
                and a["title"] != "[Removed]"
                and normalize_link(a["url"]) not in posted
            ]

            if new_articles:
                chosen = random.choice(new_articles[:5])
                logger.info(f"✅ خبر الفيديو: {chosen['title'][:60]}...")
                return {
                    "title":     chosen["title"],
                    "link":      chosen["url"],
                    "norm_link": normalize_link(chosen["url"]),
                    "image":     chosen.get("urlToImage", ""),
                }
        except Exception as e:
            logger.error(f"❌ NewsAPI Error: {e}")

    # ── RSS احتياطي ────────────────────────────────
    rss_sources = [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        "https://arstechnica.com/feed/",
    ]
    random.shuffle(rss_sources)

    for url in rss_sources:
        try:
            resp = SESSION.get(url, timeout=15)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:10]:
                if not getattr(entry, 'link', None):
                    continue
                norm = normalize_link(entry.link)
                if norm not in posted:
                    logger.info(f"✅ خبر الفيديو من RSS: {entry.title[:60]}...")
                    return {
                        "title":     entry.title,
                        "link":      entry.link,
                        "norm_link": norm,
                        "image":     "",
                    }
        except Exception as e:
            logger.error(f"❌ RSS Error {url}: {e}")

    logger.error("❌ لم يُعثر على خبر جديد للفيديو")
    return None

# =========================
# توليد نص الفيديو عبر Gemini
# =========================
def generate_video_script(title: str) -> str | None:
    """
    يولد نصاً قصيراً للفيديو مناسب للقراءة في 35-40 ثانية.
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    )

    prompt = f"""
أنت "سمير" — مقدم أخبار تقنية مغربي شاب، تقدم فيديو Reels قصير على فيسبوك.

الخبر: "{title}"

اكتب نص فيديو قصير بالدارجة المغربية يُقرأ في 35-40 ثانية (80-100 كلمة فقط).

### الهيكل الإلزامي:

**[INTRO - جملة واحدة]**
جملة تشويقية تخلي الواحد يوقف التمرير.
مثال: "خبر كبير فعالم التقنية — سمعتي بـ [الموضوع]؟"

**[BODY - 3 جمل قصيرة]**
شرح مبسط للخبر بدون تعقيد.

**[OUTRO - جملة واحدة]**
دعوة للتفاعل.
مثال: "اتابعونا باش توصلكم آخر أخبار التقنية كل يوم! 🔔"

### قواعد صارمة:
- دارجة مغربية طبيعية 100%
- 80 إلى 100 كلمة فقط — لا أكثر
- بدون markdown أو نجوم
- بدون أرقام أو نقط في البداية
- النص يُقرأ بصوت عالٍ بشكل طبيعي

اكتب النص مباشرة:
"""

    delay = 30
    for attempt in range(1, 4):
        try:
            logger.info(f"📡 توليد نص الفيديو {attempt}/3...")
            res = SESSION.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            if res.status_code == 429:
                logger.warning(f"⚠️ Gemini 429 - انتظار {delay}ث...")
                time.sleep(delay)
                delay *= 2
                continue

            res.raise_for_status()
            script = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # تنظيف Markdown
            script = re.sub(r'\*\*(.*?)\*\*', r'\1', script)
            script = re.sub(r'\*(.*?)\*',     r'\1', script)
            script = re.sub(r'#+\s*',          '',    script)

            logger.info(f"✅ تم توليد نص الفيديو ({len(script.split())} كلمة)")
            return script

        except Exception as e:
            logger.error(f"❌ Gemini Error (محاولة {attempt}): {e}")
            if attempt < 3:
                time.sleep(delay)
                delay *= 2

    return None

# =========================
# توليد الصوت عبر Gemini TTS
# =========================
def generate_audio(script: str) -> bool:
    """
    يحول النص لصوت باستخدام Gemini TTS API.
    يحفظ الصوت في temp_audio.mp3
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-preview-tts:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [{
            "parts": [{"text": script}]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        # Kore: صوت عربي طبيعي ومناسب
                        "voiceName": "Kore"
                    }
                }
            }
        }
    }

    delay = 30
    for attempt in range(1, 4):
        try:
            logger.info(f"🎙️ توليد الصوت {attempt}/3...")
            res = SESSION.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )

            if res.status_code == 429:
                logger.warning(f"⚠️ Gemini TTS 429 - انتظار {delay}ث...")
                time.sleep(delay)
                delay *= 2
                continue

            if res.status_code == 404:
                logger.warning("⚠️ Gemini TTS غير متاح، جاري استخدام gTTS...")
                return generate_audio_gtts(script)

            res.raise_for_status()
            data = res.json()

            # استخراج الصوت من الرد
            audio_data = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("inlineData", {})
                    .get("data", "")
            )

            if not audio_data:
                logger.error("❌ لم يتم استلام بيانات الصوت")
                return generate_audio_gtts(script)

            # حفظ الصوت
            audio_bytes = base64.b64decode(audio_data)
            TEMP_AUDIO.write_bytes(audio_bytes)
            logger.info(f"✅ تم توليد الصوت ({len(audio_bytes) / 1024:.1f} KB)")
            return True

        except Exception as e:
            logger.error(f"❌ Gemini TTS Error (محاولة {attempt}): {e}")
            if attempt < 3:
                time.sleep(delay)
                delay *= 2

    # الاحتياطي النهائي: gTTS
    return generate_audio_gtts(script)


def generate_audio_gtts(script: str) -> bool:
    """
    احتياطي: يستخدم gTTS إذا فشل Gemini TTS
    """
    try:
        from gtts import gTTS
        logger.info("🎙️ استخدام gTTS كاحتياطي...")
        tts = gTTS(text=script, lang='ar', slow=False)
        tts.save(str(TEMP_AUDIO))
        logger.info("✅ تم توليد الصوت عبر gTTS")
        return True
    except ImportError:
        logger.error("❌ gTTS غير مثبت — pip install gTTS")
        return False
    except Exception as e:
        logger.error(f"❌ gTTS Error: {e}")
        return False

# =========================
# جلب صورة الخبر
# =========================
def get_article_image(article: dict) -> bool:
    """
    يجلب صورة الخبر أو يستخدم Pexels/Unsplash
    """
    def download(url: str) -> bool:
        try:
            res = SESSION.get(url, timeout=20)
            if res.status_code == 200 and "image" in res.headers.get("Content-Type", ""):
                img = Image.open(io.BytesIO(res.content))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                # تحويل للنسبة 9:16
                img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
                img.save(TEMP_FRAME, "JPEG", quality=90)
                return True
        except Exception as e:
            logger.error(f"خطأ تحميل الصورة: {e}")
        return False

    # 1. صورة الخبر الأصلية
    if article.get("image") and download(article["image"]):
        logger.info("✅ تم استخدام صورة الخبر")
        return True

    # 2. Pexels
    if PEXELS_API_KEY:
        try:
            query = " ".join(article["title"].split()[:4])
            res = SESSION.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 5, "orientation": "portrait"},
                timeout=15,
            )
            photos = res.json().get("photos", [])
            if photos and download(photos[0]["src"]["large2x"]):
                logger.info("✅ تم استخدام صورة من Pexels")
                return True
        except Exception as e:
            logger.error(f"❌ Pexels Error: {e}")

    # 3. Unsplash
    if UNSPLASH_ACCESS_KEY:
        try:
            query = " ".join(article["title"].split()[:4])
            res = SESSION.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                params={"query": query, "per_page": 5, "orientation": "portrait"},
                timeout=15,
            )
            results = res.json().get("results", [])
            if results and download(results[0]["urls"]["regular"]):
                logger.info("✅ تم استخدام صورة من Unsplash")
                return True
        except Exception as e:
            logger.error(f"❌ Unsplash Error: {e}")

    # 4. خلفية لونية احتياطية
    logger.warning("⚠️ استخدام خلفية لونية احتياطية")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color=(15, 20, 40))
    img.save(TEMP_FRAME, "JPEG", quality=90)
    return True

# =========================
# إنشاء الفيديو
# =========================
def create_video(script: str) -> bool:
    """
    يدمج الصورة + النص + الصوت في فيديو mp4
    """
    try:
        from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
        logger.info("🎬 بدء إنشاء الفيديو...")

        # ── تحميل الصورة كخلفية ──────────────────────
        background = ImageClip(str(TEMP_FRAME)).with_duration(DURATION)

        # ── إضافة طبقة داكنة شفافة ───────────────────
        overlay = ImageClip(
            _create_overlay_image()
        ).with_duration(DURATION)

        # ── تقسيم النص لأسطر ─────────────────────────
        lines      = textwrap.wrap(script, width=28)
        text_clips = []
        y_pos      = VIDEO_HEIGHT * 0.35

        for i, line in enumerate(lines[:8]):  # أقصى 8 أسطر
            try:
                txt_clip = (
                    TextClip(
                        text     = line,
                        font_size= 72,
                        color    = "white",
                        font     = "Arial",
                        stroke_color="black",
                        stroke_width=2,
                        method   = "caption",
                        size     = (VIDEO_WIDTH - 100, None),
                        text_align= "center",
                    )
                    .with_position(("center", y_pos + i * 90))
                    .with_duration(DURATION)
                    .with_start(i * 0.3)  # ظهور تدريجي
                )
                text_clips.append(txt_clip)
            except Exception as e:
                logger.warning(f"⚠️ تجاوز السطر {i}: {e}")

        # ── دمج كل العناصر ───────────────────────────
        all_clips = [background, overlay] + text_clips
        video     = CompositeVideoClip(all_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

        # ── إضافة الصوت ──────────────────────────────
        if TEMP_AUDIO.exists():
            audio = AudioFileClip(str(TEMP_AUDIO))
            # ضبط مدة الفيديو حسب الصوت
            actual_duration = min(audio.duration + 2, DURATION)
            video = video.with_duration(actual_duration)
            video = video.with_audio(audio)
            logger.info(f"✅ تم إضافة الصوت ({audio.duration:.1f}ث)")

        # ── تصدير الفيديو ────────────────────────────
        logger.info("⏳ جاري تصدير الفيديو...")
        video.write_videofile(
            str(TEMP_VIDEO),
            fps           = FPS,
            codec         = "libx264",
            audio_codec   = "aac",
            preset        = "ultrafast",
            logger        = None,
        )

        logger.info(f"✅ تم إنشاء الفيديو: {TEMP_VIDEO}")
        return True

    except ImportError:
        logger.error("❌ MoviePy غير مثبت — pip install moviepy")
        return False
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء الفيديو: {e}")
        return False


def _create_overlay_image() -> str:
    """
    ينشئ طبقة شفافة داكنة فوق الصورة لتحسين قراءة النص
    """
    overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 140))
    overlay_path = Path("temp_overlay.png")
    overlay.save(overlay_path)
    return str(overlay_path)

# =========================
# نشر الفيديو على فيسبوك
# =========================
def post_video_to_facebook(script: str) -> dict | None:
    """
    ينشر الفيديو على فيسبوك كـ video post
    """
    if not TEMP_VIDEO.exists():
        logger.error("❌ ملف الفيديو غير موجود")
        return None

    # إنشاء caption مناسب
    caption = f"{script}\n\n🔔 تابعونا لأحدث أخبار التقنية يومياً!\n\n#تقنية_بالدارجة #المغرب_التقني #TechNews"

    try:
        logger.info("📤 رفع الفيديو على فيسبوك...")
        fb_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos"

        with TEMP_VIDEO.open("rb") as video_file:
            res = SESSION.post(
                fb_url,
                data={
                    "description":  caption,
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                },
                files={"source": ("video.mp4", video_file, "video/mp4")},
                timeout=120,  # رفع الفيديو يحتاج وقت أطول
            )

        result = res.json()
        if "id" in result:
            logger.info(f"✅ تم نشر الفيديو! ID: {result['id']}")
        else:
            logger.error(f"❌ فشل نشر الفيديو: {result}")

        return result

    except Exception as e:
        logger.error(f"❌ Facebook Video API Error: {e}")
        return None

# =========================
# تنظيف الملفات المؤقتة
# =========================
def cleanup():
    for f in [TEMP_AUDIO, TEMP_FRAME, TEMP_VIDEO, Path("temp_overlay.png")]:
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass
    logger.info("🧹 تم تنظيف الملفات المؤقتة")

# =========================
# الدالة الرئيسية
# =========================
def main():
    logger.info("=" * 50)
    logger.info("🎬 بدء دورة نشر الفيديو")
    logger.info("=" * 50)

    try:
        # ── 1. جلب خبر جديد ──────────────────────────
        article = get_news_for_video()
        if not article:
            logger.error("❌ لا يوجد خبر متاح للفيديو")
            return

        logger.info(f"📰 خبر الفيديو: {article['title'][:70]}...")

        # ── 2. توليد نص الفيديو ───────────────────────
        script = generate_video_script(article["title"])
        if not script:
            logger.error("❌ فشل توليد نص الفيديو")
            return

        # ── 3. توليد الصوت ───────────────────────────
        audio_ok = generate_audio(script)
        if not audio_ok:
            logger.warning("⚠️ فشل الصوت — سيتم إنشاء فيديو بدون صوت")

        # ── 4. جلب الصورة ────────────────────────────
        get_article_image(article)

        # ── 5. إنشاء الفيديو ──────────────────────────
        video_ok = create_video(script)
        if not video_ok:
            logger.error("❌ فشل إنشاء الفيديو")
            return

        # ── 6. نشر على فيسبوك ─────────────────────────
        result = post_video_to_facebook(script)

        if result and "id" in result:
            # حفظ الخبر كمنشور
            posted = load_video_posted()
            posted.add(article["norm_link"])
            save_video_posted(posted)
            logger.info("✅ دورة الفيديو اكتملت بنجاح!")
        else:
            logger.error("❌ فشل نشر الفيديو على فيسبوك")

    finally:
        cleanup()

    logger.info("=" * 50)
    logger.info("🏁 انتهت دورة نشر الفيديو")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()

