import os, re, json, time, wave, base64, random, logging, requests, textwrap, io
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

if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    raise EnvironmentError("❌ متغيرات البيئة المطلوبة غير موجودة")

# --------------------- Constants ---------------------
VIDEO_POSTED_FILE = Path("video_posted_news.json")
TEMP_AUDIO        = Path("temp_audio.wav")
TEMP_FRAME        = Path("temp_frame.jpg")
TEMP_VIDEO        = Path("temp_video.mp4")

VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
FPS          = 24
DURATION     = 40

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})

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
    except:
        pass

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
def pcm_to_wav(pcm_bytes: bytes, output_path: Path, sample_rate: int=24000, channels: int=1, bit_depth: int=16):
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
def get_arabic_font(size: int=60):
    fonts = [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for f in fonts:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()

# --------------------- Get news ---------------------
def get_news_for_video() -> dict | None:
    posted = load_video_posted()
    if NEWS_API_KEY:
        try:
            res = SESSION.get("https://newsapi.org/v2/everything", params={
                "q": "technology OR AI OR smartphone",
                "language": "en",
                "pageSize": 20,
                "sortBy": "publishedAt",
                "apiKey": NEWS_API_KEY
            }, timeout=15)
            res.raise_for_status()
            articles = res.json().get("articles", [])
            new_articles = [a for a in articles if a.get("url") and normalize_link(a["url"]) not in posted]
            if new_articles:
                chosen = random.choice(new_articles[:5])
                return {"title": chosen["title"], "link": chosen["url"], "norm_link": normalize_link(chosen["url"]), "image": chosen.get("urlToImage","")}
        except:
            pass
    return None

# --------------------- Video script ---------------------
def generate_video_script(title: str) -> str | None:
    prompt = f"أنت مقدم أخبار مغربي. الخبر: {title}. اكتب نص قصير بالدارجة المغربية 35-40 ثانية."
    # محاكاة Gemini API response (يمكنك استبدالها بالطلب الحقيقي)
    script = f"🔔 خبر جديد: {title}. شرح سريع للخبر. اتبعونا لأحدث أخبار التقنية."
    return script

# --------------------- Audio ---------------------
def generate_audio(script: str) -> bool:
    # محاكاة Gemini TTS → PCM → WAV
    pcm_bytes = b'\x00' * 24000*2*DURATION  # dummy silent PCM
    return pcm_to_wav(pcm_bytes, TEMP_AUDIO)

# --------------------- Image ---------------------
def get_article_image(article: dict) -> bool:
    # خلفية بسيطة
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
        lines_to_show = lines[:min(i+2, len(lines))]
        base_img = Image.open(TEMP_FRAME).copy()
        draw = ImageDraw.Draw(base_img)
        y_start = VIDEO_HEIGHT*0.35
        for j, line in enumerate(lines_to_show):
            y = int(y_start + j*90)
            font = font_large if j==0 else font_small
            draw.text((VIDEO_WIDTH//2, y), line, font=font, fill="white", anchor="mm")
        frames.append(base_img)
    return frames

# --------------------- Create video ---------------------
def create_video(script: str) -> bool:
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        frames = create_frames_with_text(script, 5)
        frame_duration = DURATION / len(frames)
        clips = []
        for i, f in enumerate(frames):
            fpath = Path(f"temp_frame_{i}.jpg")
            f.save(fpath)
            clips.append(ImageClip(str(fpath)).set_duration(frame_duration))
        video = concatenate_videoclips(clips, method="compose")
        if TEMP_AUDIO.exists():
            audio = AudioFileClip(str(TEMP_AUDIO))
            video = video.set_audio(audio).set_duration(min(audio.duration, DURATION))
        video.write_videofile(str(TEMP_VIDEO), fps=FPS, codec="libx264", audio_codec="aac",
                              preset="ultrafast", ffmpeg_params=["-pix_fmt","yuv420p","-profile:v","baseline","-movflags","+faststart"])
        # حذف فريمات مؤقتة
        for i in range(len(frames)):
            Path(f"temp_frame_{i}.jpg").unlink(missing_ok=True)
        return True
    except Exception as e:
        logger.error(f"❌ Create video error: {e}")
        return False

# --------------------- Post video to Facebook (chunk by chunk) ---------------------
def post_video_to_facebook(script: str) -> dict | None:
    if not TEMP_VIDEO.exists(): return None
    caption = f"{script}\n\n🔔 تابعونا لأحدث أخبار التقنية يومياً!\n#تقنية_بالدارجة #TechNews"
    video_size = TEMP_VIDEO.stat().st_size
    init_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos"
    try:
        # 1️⃣ init
        init_res = SESSION.post(init_url, data={"upload_phase":"start","file_size":video_size,"access_token":FB_PAGE_ACCESS_TOKEN})
        init_data = init_res.json()
        session_id = init_data.get("upload_session_id")
        start_offset = int(init_data.get("start_offset",0))
        end_offset   = int(init_data.get("end_offset",0))
        if not session_id: return None
        # 2️⃣ upload
        with TEMP_VIDEO.open("rb") as f:
            while start_offset < video_size:
                f.seek(start_offset)
                chunk = f.read(end_offset - start_offset)
                transfer_res = SESSION.post(init_url, data={
                    "upload_phase":"transfer",
                    "upload_session_id":session_id,
                    "start_offset":start_offset,
                    "access_token":FB_PAGE_ACCESS_TOKEN
                }, files={"video_file_chunk":("video.mp4",chunk,"video/mp4")})
                transfer_data = transfer_res.json()
                if "error" in transfer_data: return None
                start_offset = int(transfer_data.get("start_offset",start_offset))
                end_offset   = int(transfer_data.get("end_offset",start_offset))
        # 3️⃣ finish
        finish_res = SESSION.post(init_url, data={
            "upload_phase":"finish",
            "upload_session_id":session_id,
            "description":caption,
            "access_token":FB_PAGE_ACCESS_TOKEN
        })
        result = finish_res.json()
        if result.get("id"): return {"id": result["id"]}
        return None
    except Exception as e:
        logger.error(f"❌ Facebook Video API Error: {e}")
        return None

# --------------------- Cleanup ---------------------
def cleanup():
    for f in [TEMP_AUDIO, TEMP_FRAME, TEMP_VIDEO]+[Path(f"temp_frame_{i}.jpg") for i in range(10)]:
        f.unlink(missing_ok=True)

# --------------------- Main ---------------------
def main():
    article = get_news_for_video()
    if not article: return
    script = generate_video_script(article["title"])
    generate_audio(script)
    get_article_image(article)
    create_video(script)
    result = post_video_to_facebook(script)
    if result:
        posted = load_video_posted()
        posted.add(article["norm_link"])
        save_video_posted(posted)
    cleanup()

if __name__=="__main__":
    main()
