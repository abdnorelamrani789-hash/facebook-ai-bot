import os, re, json, time, wave, base64, random, logging, requests, textwrap, io
import feedparser
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from PIL import Image, ImageDraw, ImageFont

# --------------------- Logging ---------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --------------------- Env Variables ---------------------
FB_PAGE_ID           = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY         = os.getenv("NEWS_API_KEY")
PEXELS_API_KEY       = os.getenv("PEXELS_API_KEY")
UNSPLASH_ACCESS_KEY  = os.getenv("UNSPLASH_ACCESS_KEY")

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise EnvironmentError("❌ متغيرات البيئة المطلوبة غير موجودة")

# --------------------- Constants ---------------------
VIDEO_POSTED_FILE = Path("video_posted_news.json")
TEMP_AUDIO        = Path("temp_audio.wav")
TEMP_FRAME        = Path("temp_frame.jpg")
TEMP_VIDEO        = Path("temp_video.mp4")
MODEL_NAME        = "gemini-2.5-flash"

VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
FPS          = 24
DURATION     = 40

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/133.0.0.0"})

# --------------------- JSON helpers ---------------------
def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.load(path.open("r", encoding="utf-8"))
        except:
            return default
    return default

def _save_json(path: Path, data):
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ {path.name}: {e}")

def normalize_link(url: str) -> str:
    if not url: return ""
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, '', '', '')).rstrip('/')

# --------------------- Posted news ---------------------
def load_video_posted() -> set:
    data = _load_json(VIDEO_POSTED_FILE, [])
    return set(data if isinstance(data, list) else [])

def save_video_posted(posted: set):
    _save_json(VIDEO_POSTED_FILE, list(posted))

# --------------------- PCM → WAV ---------------------
def pcm_to_wav(pcm_bytes: bytes, output_path: Path,
               sample_rate: int = 24000,
               channels: int = 1,
               bit_depth: int = 16) -> bool:
    try:
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(bit_depth // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
        logger.info(f"✅ PCM → WAV ({len(pcm_bytes)/1024:.1f} KB)")
        return True
    except Exception as e:
        logger.error(f"❌ PCM to WAV Error: {e}")
        return False

# --------------------- Font Arabic ---------------------
def get_arabic_font(size: int = 60):
    fonts = [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for f in fonts:
        if Path(f).exists():
            try:
                font = ImageFont.truetype(f, size)
                logger.info(f"✅ Font: {Path(f).name}")
                return font
            except:
                continue
    logger.warning("⚠️ استخدام default font")
    return ImageFont.load_default()

# --------------------- Get news ---------------------
def get_news_for_video() -> dict | None:
    posted = load_video_posted()

    # NewsAPI أولاً
    if NEWS_API_KEY:
        logger.info("📡 جلب الأخبار من NewsAPI...")
        try:
            res = SESSION.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        "technology OR AI OR smartphone OR innovation",
                    "language": "en",
                    "pageSize": 20,
                    "sortBy":   "publishedAt",
                    "apiKey":   NEWS_API_KEY
                },
                timeout=15
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
                    "image":     chosen.get("urlToImage", "")
                }
        except Exception as e:
            logger.error(f"❌ NewsAPI Error: {e}")

    # RSS احتياطي
    rss_sources = [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
    ]
    random.shuffle(rss_sources)
    for url in rss_sources:
        try:
            resp = SESSION.get(url, timeout=15)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:10]:
                if not getattr(entry, 'link', None): continue
                norm = normalize_link(entry.link)
                if norm not in posted:
                    logger.info(f"✅ خبر من RSS: {entry.title[:60]}...")
                    return {
                        "title":     entry.title,
                        "link":      entry.link,
                        "norm_link": norm,
                        "image":     ""
                    }
        except Exception as e:
            logger.error(f"❌ RSS Error: {e}")

    logger.error("❌ لم يُعثر على خبر جديد")
    return None

# --------------------- ✅ Video script (Gemini حقيقي) ---------------------
def generate_video_script(title: str) -> str | None:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    )
    prompt = f"""
أنت "سمير" — مقدم أخبار تقنية مغربي شاب، تقدم فيديو Reels قصير على فيسبوك.

الخبر: "{title}"

اكتب نص فيديو قصير بالدارجة المغربية يُقرأ في 35-40 ثانية (80-100 كلمة فقط).

الهيكل:
- جملة تشويقية تخلي الواحد يوقف التمرير
- شرح مبسط للخبر في 3 جمل قصيرة
- دعوة للمتابعة: "اتابعونا باش توصلكم آخر أخبار التقنية كل يوم"

القواعد:
- دارجة مغربية طبيعية 100%
- 80 إلى 100 كلمة فقط
- بدون markdown أو نجوم أو أرقام في البداية

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
                timeout=60
            )
            if res.status_code == 429:
                time.sleep(delay); delay *= 2; continue
            res.raise_for_status()
            script = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            script = re.sub(r'\*\*(.*?)\*\*', r'\1', script)
            script = re.sub(r'\*(.*?)\*',     r'\1', script)
            script = re.sub(r'#+\s*',          '',    script)
            logger.info(f"✅ تم توليد النص ({len(script.split())} كلمة)")
            return script
        except Exception as e:
            logger.error(f"❌ Gemini Error (محاولة {attempt}): {e}")
            if attempt < 3: time.sleep(delay); delay *= 2
    return None

# --------------------- ✅ Audio (Gemini TTS حقيقي) ---------------------
def generate_audio(script: str) -> bool:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-preview-tts:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": script}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": "Kore"}
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
                timeout=60
            )
            if res.status_code == 429:
                time.sleep(delay); delay *= 2; continue
            if res.status_code == 404:
                logger.warning("⚠️ Gemini TTS غير متاح، جاري استخدام gTTS...")
                return generate_audio_gtts(script)
            res.raise_for_status()
            audio_data = (
                res.json()
                   .get("candidates", [{}])[0]
                   .get("content", {})
                   .get("parts", [{}])[0]
                   .get("inlineData", {})
                   .get("data", "")
            )
            if not audio_data:
                return generate_audio_gtts(script)
            # ✅ Gemini TTS → PCM → WAV
            pcm_bytes = base64.b64decode(audio_data)
            return pcm_to_wav(pcm_bytes, TEMP_AUDIO)
        except Exception as e:
            logger.error(f"❌ TTS Error (محاولة {attempt}): {e}")
            if attempt < 3: time.sleep(delay); delay *= 2
    return generate_audio_gtts(script)

def generate_audio_gtts(script: str) -> bool:
    try:
        from gtts import gTTS
        global TEMP_AUDIO
        TEMP_AUDIO = Path("temp_audio_gtts.mp3")
        logger.info("🎙️ استخدام gTTS كاحتياطي...")
        gTTS(text=script, lang='ar', slow=False).save(str(TEMP_AUDIO))
        logger.info("✅ تم توليد الصوت عبر gTTS")
        return True
    except Exception as e:
        logger.error(f"❌ gTTS Error: {e}")
        return False

# --------------------- Image ---------------------
def get_article_image(article: dict) -> bool:
    def download(url: str) -> bool:
        try:
            res = SESSION.get(url, timeout=20)
            if res.status_code == 200 and "image" in res.headers.get("Content-Type", ""):
                img = Image.open(io.BytesIO(res.content))
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
                img.save(TEMP_FRAME, "JPEG", quality=90)
                return True
        except: pass
        return False

    if article.get("image") and download(article["image"]):
        logger.info("✅ صورة الخبر الأصلية"); return True

    if PEXELS_API_KEY:
        try:
            query = " ".join(article["title"].split()[:4])
            res = SESSION.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 5, "orientation": "portrait"},
                timeout=15
            )
            photos = res.json().get("photos", [])
            if photos and download(photos[0]["src"]["large2x"]):
                logger.info("✅ صورة من Pexels"); return True
        except Exception as e:
            logger.error(f"❌ Pexels Error: {e}")

    if UNSPLASH_ACCESS_KEY:
        try:
            query = " ".join(article["title"].split()[:4])
            res = SESSION.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                params={"query": query, "per_page": 5, "orientation": "portrait"},
                timeout=15
            )
            results = res.json().get("results", [])
            if results and download(results[0]["urls"]["regular"]):
                logger.info("✅ صورة من Unsplash"); return True
        except Exception as e:
            logger.error(f"❌ Unsplash Error: {e}")

    # خلفية لونية احتياطية
    logger.warning("⚠️ استخدام خلفية لونية احتياطية")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color=(15, 20, 40))
    img.save(TEMP_FRAME, "JPEG", quality=90)
    return True

# --------------------- Frames ---------------------
def create_frames_with_text(script: str, num_frames: int = 5) -> list:
    frames = []
    lines = textwrap.wrap(script, width=25)
    font_large = get_arabic_font(65)
    font_small = get_arabic_font(45)

    for i in range(num_frames):
        lines_to_show = lines[:min(i + 2, len(lines))]
        base_img = Image.open(TEMP_FRAME).copy()

        # طبقة داكنة
        overlay  = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 150))
        base_img = base_img.convert("RGBA")
        base_img = Image.alpha_composite(base_img, overlay).convert("RGB")
        draw     = ImageDraw.Draw(base_img)

        y_start = VIDEO_HEIGHT * 0.35
        for j, line in enumerate(lines_to_show):
            y    = int(y_start + j * 90)
            font = font_large if j == 0 else font_small
            # ظل
            draw.text((VIDEO_WIDTH // 2 + 3, y + 3), line, font=font, fill=(0, 0, 0, 180), anchor="mm")
            # نص أبيض
            draw.text((VIDEO_WIDTH // 2, y), line, font=font, fill="white", anchor="mm")

        frames.append(base_img)
    return frames

# --------------------- ✅ Create video (moviepy v2 API) ---------------------
def create_video(script: str) -> bool:
    try:
        # ✅ moviepy v2: import مباشر بدون .editor
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
        logger.info("🎬 بدء إنشاء الفيديو...")

        frames         = create_frames_with_text(script, 5)
        frame_duration = DURATION / len(frames)
        clips          = []

        for i, frame in enumerate(frames):
            fpath = Path(f"temp_frame_{i}.jpg")
            frame.save(fpath, "JPEG", quality=90)
            # ✅ moviepy v2: with_duration بدل set_duration
            clips.append(ImageClip(str(fpath)).with_duration(frame_duration))

        video = concatenate_videoclips(clips, method="compose")

        if TEMP_AUDIO.exists():
            try:
                audio = AudioFileClip(str(TEMP_AUDIO))
                # ✅ moviepy v2: with_audio و with_duration بدل set_audio و set_duration
                video = video.with_duration(min(audio.duration + 1, DURATION))
                video = video.with_audio(audio)
                logger.info(f"✅ تم إضافة الصوت ({audio.duration:.1f}ث)")
            except Exception as e:
                logger.warning(f"⚠️ فشل إضافة الصوت: {e}")

        logger.info("⏳ جاري تصدير الفيديو...")
        video.write_videofile(
            str(TEMP_VIDEO),
            fps         = FPS,
            codec       = "libx264",
            audio_codec = "aac",
            preset      = "ultrafast",
            logger      = None,
            ffmpeg_params=[
                "-pix_fmt",   "yuv420p",
                "-profile:v", "baseline",
                "-level",     "3.0",
                "-movflags",  "+faststart",
                "-b:a",       "128k",
            ]
        )

        # تنظيف الفريمات المؤقتة
        for i in range(len(frames)):
            Path(f"temp_frame_{i}.jpg").unlink(missing_ok=True)

        size_mb = TEMP_VIDEO.stat().st_size / (1024 * 1024)
        logger.info(f"✅ تم إنشاء الفيديو! ({size_mb:.1f} MB)")
        return True

    except ImportError:
        logger.error("❌ MoviePy غير مثبت — pip install moviepy")
        return False
    except Exception as e:
        logger.error(f"❌ Create video error: {e}")
        return False

# --------------------- Post video to Facebook (Resumable Upload) ---------------------
def post_video_to_facebook(script: str) -> dict | None:
    if not TEMP_VIDEO.exists():
        logger.error("❌ ملف الفيديو غير موجود")
        return None

    video_size = TEMP_VIDEO.stat().st_size
    caption    = (
        f"{script}\n\n"
        f"🔔 تابعونا لأحدث أخبار التقنية يومياً!\n"
        f"#تقنية_بالدارجة #المغرب_التقني #TechNews #تكنولوجيا"
    )
    init_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos"

    try:
        # 1️⃣ Start
        logger.info("📤 [1/3] تهيئة رفع الفيديو...")
        init_res  = SESSION.post(init_url, data={
            "upload_phase": "start",
            "file_size":    video_size,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }, timeout=30)
        init_data = init_res.json()

        session_id   = init_data.get("upload_session_id")
        video_id     = init_data.get("video_id")
        start_offset = int(init_data.get("start_offset", 0))
        end_offset   = int(init_data.get("end_offset",   video_size))

        if not session_id:
            logger.error(f"❌ فشل تهيئة الرفع: {init_data}")
            return None
        logger.info(f"✅ Session ID: {session_id}")

        # 2️⃣ Transfer (chunk by chunk)
        logger.info("📤 [2/3] رفع بيانات الفيديو...")
        with TEMP_VIDEO.open("rb") as f:
            while start_offset < video_size:
                f.seek(start_offset)
                chunk = f.read(end_offset - start_offset)
                transfer_res  = SESSION.post(init_url, data={
                    "upload_phase":      "transfer",
                    "upload_session_id": session_id,
                    "start_offset":      start_offset,
                    "access_token":      FB_PAGE_ACCESS_TOKEN
                }, files={"video_file_chunk": ("video.mp4", chunk, "video/mp4")},
                timeout=180)
                transfer_data = transfer_res.json()

                if "error" in transfer_data:
                    logger.error(f"❌ فشل رفع الـ chunk: {transfer_data}")
                    return None

                new_start = int(transfer_data.get("start_offset", start_offset))
                new_end   = int(transfer_data.get("end_offset",   new_start))

                # منع اللوب اللانهائي
                if new_start == start_offset:
                    break
                start_offset = new_start
                end_offset   = new_end

        logger.info("✅ تم رفع الفيديو")

        # 3️⃣ Finish
        logger.info("📤 [3/3] نشر الفيديو...")
        finish_res  = SESSION.post(init_url, data={
            "upload_phase":      "finish",
            "upload_session_id": session_id,
            "description":       caption,
            "access_token":      FB_PAGE_ACCESS_TOKEN
        }, timeout=60)
        result = finish_res.json()

        if result.get("success") or result.get("id"):
            final_id = result.get("id") or video_id
            logger.info(f"✅ تم نشر الفيديو! ID: {final_id}")
            return {"id": final_id}
        else:
            logger.error(f"❌ فشل نشر الفيديو: {result}")
            return None

    except Exception as e:
        logger.error(f"❌ Facebook Video API Error: {e}")
        return None

# --------------------- Cleanup ---------------------
def cleanup():
    files = [TEMP_AUDIO, TEMP_FRAME, TEMP_VIDEO, Path("temp_audio_gtts.mp3")]
    for i in range(10):
        files.append(Path(f"temp_frame_{i}.jpg"))
    for f in files:
        f.unlink(missing_ok=True)
    logger.info("🧹 تم تنظيف الملفات المؤقتة")

# --------------------- Main ---------------------
def main():
    logger.info("=" * 50)
    logger.info("🎬 بدء دورة نشر الفيديو")
    logger.info("=" * 50)

    try:
        # 1. جلب الخبر
        article = get_news_for_video()
        if not article:
            logger.error("❌ لا يوجد خبر متاح"); return

        logger.info(f"📰 {article['title'][:70]}...")

        # 2. توليد النص
        script = generate_video_script(article["title"])
        if not script:
            logger.error("❌ فشل توليد النص"); return

        # 3. توليد الصوت
        if not generate_audio(script):
            logger.warning("⚠️ فشل الصوت — فيديو بدون صوت")

        # 4. الصورة
        get_article_image(article)

        # 5. إنشاء الفيديو
        if not create_video(script):
            logger.error("❌ فشل إنشاء الفيديو"); return

        # 6. النشر
        result = post_video_to_facebook(script)
        if result and result.get("id"):
            posted = load_video_posted()
            posted.add(article["norm_link"])
            save_video_posted(posted)
            logger.info("✅ دورة الفيديو اكتملت بنجاح!")
        else:
            logger.error("❌ فشل النشر على فيسبوك")

    finally:
        cleanup()

    logger.info("=" * 50)
    logger.info("🏁 انتهت دورة نشر الفيديو")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()

