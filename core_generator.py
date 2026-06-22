import os
import json
import re
import sys
import asyncio
import urllib.parse
import requests
from dotenv import load_dotenv
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# Monkey patch for legacy libraries using deprecated PIL.Image.ANTIALIAS
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Monkey patch for Windows console encoding (cp949) issues with emojis
try:
    if sys.stdout and getattr(sys.stdout, 'encoding', 'utf-8') != 'utf-8':
        sys.stdout.reconfigure(errors='replace')
except Exception:
    pass
try:
    if sys.stderr and getattr(sys.stderr, 'encoding', 'utf-8') != 'utf-8':
        sys.stderr.reconfigure(errors='replace')
except Exception:
    pass
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    VideoFileClip,
    VideoClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips
)
import numpy as np
import time

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Create temporary work directories
TEMP_DIR = "temp_assets"
os.makedirs(TEMP_DIR, exist_ok=True)

AUDIO_ASSETS_DIR = "audio_assets"
BGM_DIR = os.path.join(AUDIO_ASSETS_DIR, "bgm")
SFX_DIR = os.path.join(AUDIO_ASSETS_DIR, "sfx")

os.makedirs(BGM_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)

# default royalty free loop links
BGM_URLS = {
    "epic_orchestral": "http://codeskulptor-demos.commondatastorage.googleapis.com/GalaxyInvaders/theme_01.mp3",
    "dark_mystery": "http://codeskulptor-demos.commondatastorage.googleapis.com/descent/background%20music.mp3",
    "sad_piano": "http://commondatastorage.googleapis.com/codeskulptor-demos/DDR_assets/Kangaroo_MusiQue_-_The_Neverwritten_Role_Playing_Game.mp3",
    "intense_suspense": "http://codeskulptor-demos.commondatastorage.googleapis.com/GalaxyInvaders/theme_01.mp3"
}

SFX_URLS = {
    "sword_clash": "http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/missile.mp3",
    "thunder": "http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/explosion.mp3",
    "fire_crackle": "http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/thrust.mp3",
    "horse_gallop": "http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/thrust.mp3",
    "wind_howl": "http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/thrust.mp3"
}


SKIN_CONFIGS = {
    "🎬 역사 다큐멘터리 (Historical Documentary)": {
        "persona": "넷플릭스 역사 다큐멘터리 전문 감독이자 연출가",
        "narration_style": "웅장하고 신뢰감 넘치는 구어체 존댓말, 역사적 무게감과 깊이가 느껴지는 다큐멘터리 전문 성우 톤",
        "visual_style": "초고화질 극실사 영화 스틸컷, 극적인 조명과 그림자, 사실적인 디테일, 역사적 고증 준수",
        "recommended_bgm": "dark_mystery"
    },
    "💡 동기부여 & 자기계발 (Motivation & Self-Development)": {
        "persona": "사람들에게 깊은 영감을 주는 라이프 코치이자 동기부여 강연가",
        "narration_style": "짧고 강력한 단문 형태, 청중을 집중시키는 힘차고 자신감 넘치는 강한 어조, 직접 질문을 던지는 호소력 있는 말투",
        "visual_style": "에너제틱하고 현대적인 비주얼, 밝은 조명 대비, 극적인 야외 전경 및 목표를 향해 나아가는 인물의 역동적인 클로즈업",
        "recommended_bgm": "epic_orchestral"
    },
    "🔬 과학 & 일반 상식 (Science & Trivia)": {
        "persona": "지식을 흥미롭고 위트 있게 설명해 주는 전문 과학 유튜버",
        "narration_style": "호기심을 유발하고 유용한 지식을 또박또박 설명해 주는 톤, 대중적이고 친근하며 흥미를 주는 설명조",
        "visual_style": "깔끔하고 세련된 3D 그래픽 느낌, 과학적 구조나 인포그래픽 요소가 살짝 결합된 정돈되고 밝은 이미지",
        "recommended_bgm": "intense_suspense"
    },
    "📖 소설 & 판타지 스토리텔링 (Fiction & Storytelling)": {
        "persona": "감성적이고 따뜻하며 흥미진진한 판타지 소설 작가",
        "narration_style": "한 편의 동화나 소설책을 낭독해 주듯 감정이 풍부하고 부드러운 목소리, 청중이 스토리에 완전 몰입할 수 있는 연극적 톤",
        "visual_style": "환상적이고 몽환적인 판타지 아트 스타일, 따뜻하고 부드러운 파스텔톤 빛과 색채, 감성적인 일러스트레이션 풍",
        "recommended_bgm": "sad_piano"
    },
    "👻 공포 & 미스터리 극장 (Horror & Mystery)": {
        "persona": "기묘한 미스터리와 오싹한 괴담을 이야기하는 어둠 속의 스토리텔러",
        "narration_style": "낮고 음산하게 읊조리는 톤, 긴장감을 극대화하는 서늘한 어조, 느릿한 호흡과 나지막이 속삭이는 듯한 오싹한 화법",
        "visual_style": "어둡고 기괴한 고딕 스타일, 짙은 안개와 극적인 실루엣, 창백한 조명 대비, 스릴러 영화의 공포스러운 분위기",
        "recommended_bgm": "dark_mystery"
    }
}


def download_audio_asset(url, output_path):
    """Download a file from url and save to output_path if not already exists."""
    if os.path.exists(output_path):
        return True
    try:
        print(f"[Audio Asset] Downloading default asset: {url}...")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"[Audio Asset Warning] Failed to download {url}: {e}")
    return False


def prepare_default_audio_assets():
    """Ensure all default audio assets are downloaded and ready."""
    print("[Audio Asset] Checking and downloading audio library assets...")
    for mood, url in BGM_URLS.items():
        dest = os.path.join(BGM_DIR, f"{mood}.mp3")
        download_audio_asset(url, dest)
    for sfx_name, url in SFX_URLS.items():
        dest = os.path.join(SFX_DIR, f"{sfx_name}.mp3")
        download_audio_asset(url, dest)


# Keywords for subtitle text highlighting (Minimal History Style)
SUBTITLE_KEYWORDS = {
    "혈액형", "말라리아", "페스트", "진화", "생존", "돌연변이", "인류", "역사", "비밀", "질병", 
    "바이러스", "감염", "수혈", "콜레라", "노벨상", "유전자", "면역", "병원균", "사망률", "저항력",
    "A형", "B형", "O형", "AB형", "적혈구", "항원", "항체", "유전", "발견", "치명적", "기록", "전쟁",
    "황열병", "매독", "코로나", "흑사병", "생명", "수혈사고", "생명력", "자연선택", "도태"
}

def is_keyword_word(word):
    """Determine if a word contains a key evolutionary/historical keyword or digits."""
    # Strip common postpositions or punctuation for matching
    cleaned = re.sub(r'[은는이가을를의과와에로으로은는이]$', '', word)
    cleaned = re.sub(r'[^a-zA-Z0-9가-힣]', '', cleaned) # alphanumeric only
    
    # Check against our set of keywords
    for kw in SUBTITLE_KEYWORDS:
        if kw in cleaned:
            return True
            
    # Highlight numbers/years/percentages (e.g., 1901년, 10%)
    if any(char.isdigit() for char in cleaned):
        return True
        
    return False


def ensure_korean_font(font_style="gothic"):
    """Ensure a Korean TTF font is downloaded and available locally in the project directory."""
    if font_style == "serif":
        local_font_path = "nanum_myeongjo.ttf"
        url = "https://github.com/google/fonts/raw/main/ofl/nanummyeongjo/NanumMyeongjo-Regular.ttf"
    else:
        local_font_path = "nanum_gothic.ttf"
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        
    if os.path.exists(local_font_path) and os.path.getsize(local_font_path) > 100000:
        return local_font_path
    
    print(f"[Font] Downloading {font_style} font dynamically: {url}...")
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            with open(local_font_path, "wb") as f:
                f.write(response.content)
            print(f"[Font] {font_style} downloaded successfully!")
            return local_font_path
    except Exception as e:
        print(f"[Font Error] Failed to download {font_style} font: {e}")
    return None


def get_system_font(font_size=50, font_style="gothic"):
    """Retrieve a usable Korean font from local workspace or Windows system fonts."""
    # 1. First priority: Check local custom font
    local_font = "nanum_myeongjo.ttf" if font_style == "serif" else "nanum_gothic.ttf"
    if os.path.exists(local_font):
        try:
            return ImageFont.truetype(local_font, font_size)
        except Exception:
            pass
            
    # 2. Second priority: Attempt dynamic download fallback
    downloaded_font = ensure_korean_font(font_style)
    if downloaded_font and os.path.exists(downloaded_font):
        try:
            return ImageFont.truetype(downloaded_font, font_size)
        except Exception:
            pass

    # 3. Third priority: Windows system font search paths
    if font_style == "serif":
        font_paths = [
            "C:\\Windows\\Fonts\\batang.ttc",       # Batang (Serif default)
            "C:\\Windows\\Fonts\\malgun.ttf",       # Malgun Gothic
            "C:\\Windows\\Fonts\\gulim.ttc"         # Gulim
        ]
    else:
        font_paths = [
            "C:\\Windows\\Fonts\\malgun.ttf",       # Malgun Gothic (Windows default)
            "C:\\Windows\\Fonts\\malgunbd.ttf",     # Malgun Gothic Bold
            "C:\\Windows\\Fonts\\batang.ttc",       # Batang
            "C:\\Windows\\Fonts\\gulim.ttc"         # Gulim
        ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue
    # Fallback to default PIL font if no Korean system font found
    return ImageFont.load_default()


def wrap_text(text, font, max_width, draw):
    """Wrap Korean text to fit inside max_width dynamically."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        # Calculate width of current line
        line_text = " ".join(current_line)
        # Compatibility check for Pillow versions
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), line_text, font=font)
            width = bbox[2] - bbox[0]
        else:
            width, _ = draw.textsize(line_text, font=font)
            
        if width > max_width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(line_text)
                current_line = []
                
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def create_subtitle_image(text, width=1080, height=1920, font_size=48, output_path="subtitle.png", position="bottom", font_style="gothic"):
    """Create a transparent PNG containing styled Korean subtitle text with word-level gold highlighting."""
    # Create transparent image
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    font = get_system_font(font_size, font_style=font_style)
    
    # Wrap text to fit screen width (with safety padding)
    max_text_width = int(width * 0.85)
    lines = wrap_text(text, font, max_text_width, draw)
    
    # Calculate text height for vertical placement
    line_heights = []
    for line in lines:
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
        else:
            _, h = draw.textsize(line, font=font)
            line_heights.append(h)
            
    total_text_height = sum(line_heights) + (15 * (len(lines) - 1))  # 15px line spacing
    
    # Subtitle position
    if position == "center":
        start_y = int(height * 0.5) - (total_text_height // 2)
    else: # bottom
        start_y = int(height * 0.75) - (total_text_height // 2)
    
    current_y = start_y
    for i, line in enumerate(lines):
        # Calculate x to center text
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
        else:
            line_w, line_h = draw.textsize(line, font=font)
            
        x = (width - line_w) // 2
        
        # Draw background shadow rectangle
        padding = 15
        rect_x0 = x - padding
        rect_y0 = current_y - padding
        rect_x1 = x + line_w + padding
        rect_y1 = current_y + line_h + padding
        draw.rounded_rectangle([rect_x0, rect_y0, rect_x1, rect_y1], radius=10, fill=(0, 0, 0, 150))
        
        # Draw actual text with word-level highlight
        words_in_line = line.split(" ")
        curr_x = x
        for word in words_in_line:
            highlight = is_keyword_word(word)
            # Gold color for keywords, White for standard text
            color = (255, 215, 0, 255) if highlight else (255, 255, 255, 255)
            
            draw.text((curr_x, current_y), word, font=font, fill=color)
            
            # Measure word and trailing space to update horizontal offset
            if hasattr(draw, "textbbox"):
                word_bbox = draw.textbbox((0, 0), word, font=font)
                word_w = word_bbox[2] - word_bbox[0]
                space_bbox = draw.textbbox((0, 0), " ", font=font)
                space_w = space_bbox[2] - space_bbox[0]
            else:
                word_w, _ = draw.textsize(word, font=font)
                space_w, _ = draw.textsize(" ", font=font)
                
            curr_x += word_w + space_w
            
        current_y += line_h + 15
        
    image.save(output_path)
    return output_path


async def generate_tts_async(text, output_path, voice="ko-KR-InJoonNeural", rate="-12%"):
    """Synthesize speech using Microsoft Edge TTS asynchronously with custom speed rate."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


def generate_tts(text, output_path, voice="ko-KR-InJoonNeural", rate="-12%"):
    """Sync wrapper for the Edge TTS async function."""
    asyncio.run(generate_tts_async(text, output_path, voice, rate=rate))


def generate_elevenlabs_tts(text, output_path, voice_id="pNInz6obpgq5mWzIA5FD", api_key=None, stability=0.75, clarity=0.75, style=0.0):
    """Synthesize speech using ElevenLabs REST API with detailed parameter tuning."""
    if not api_key or api_key == "your_elevenlabs_api_key_here" or api_key.strip() == "":
        raise ValueError("ElevenLabs API Key is missing or invalid.")
        
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": clarity,
            "style": style
        }
    }
    response = requests.post(url, json=data, headers=headers, timeout=30)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        return True
    else:
        raise Exception(f"ElevenLabs TTS failed: Status {response.status_code}, {response.text}")


def generate_google_tts(text, output_path, voice_name="ko-KR-Neural2-A", api_key=None, rate="-12%"):
    """Synthesize speech using Google Cloud Text-to-Speech REST API."""
    k = api_key or os.getenv("GEMINI_API_KEY")
    if not k:
        raise ValueError("Google API key is missing for TTS.")
        
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={k}"
    headers = {"Content-Type": "application/json"}
    
    # Map friendly names to actual API voice codes
    voice_map = {
        "ko-KR-Neural2-A (남성 - 표준)": "ko-KR-Neural2-A",
        "ko-KR-Neural2-B (여성 - 표준)": "ko-KR-Neural2-B",
        "ko-KR-Wavenet-A (남성 - 중후함)": "ko-KR-Wavenet-A",
        "ko-KR-Journey-F (여성 - 친근함)": "ko-KR-Journey-F",
        "ko-KR-Studio-O (남성 - 뉴스 성우)": "ko-KR-Studio-O"
    }
    
    actual_voice = voice_map.get(voice_name, voice_name)
    if not actual_voice:
        actual_voice = "ko-KR-Neural2-A"
        
    # Determine language code
    lang_code = "ko-KR"
    parts = actual_voice.split("-")
    if len(parts) >= 2:
        lang_code = f"{parts[0]}-{parts[1]}"
        
    # Convert rate to float speakingRate (1.0 is normal, 0.88 is -12% slow)
    float_rate = 1.0
    if isinstance(rate, str) and rate.endswith("%"):
        try:
            percent = float(rate.replace("%", ""))
            float_rate = 1.0 + (percent / 100.0)
        except Exception:
            float_rate = 0.88
    else:
        try:
            float_rate = float(rate)
        except Exception:
            float_rate = 0.88
            
    payload = {
        "input": {"text": text},
        "voice": {
            "languageCode": lang_code,
            "name": actual_voice
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": float_rate
        }
    }
    
    print(f"[Google TTS] Generating voiceover for '{text[:25]}...' using voice {actual_voice} at speed {float_rate}...")
    response = requests.post(url, json=payload, headers=headers, timeout=20)
    if response.status_code == 200:
        import base64
        audio_content = response.json().get("audioContent")
        if audio_content:
            audio_bytes = base64.b64decode(audio_content)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return True
        else:
            raise Exception("Google TTS response did not contain audioContent.")
    else:
        raise Exception(f"Google TTS synthesis failed: Status {response.status_code}, {response.text}")


def generate_voice_over(text, output_path, provider="edge", voice_id=None, api_key=None, rate="-12%",
                        v4_voice_stability=0.75, v4_voice_clarity=0.75, v4_voice_style=0.0):
    """Synthesize speech with selected provider and fallback to edge-tts if it fails."""
    if provider == "google":
        try:
            print(f"[TTS] Attempting Google Cloud TTS with voice {voice_id}...")
            v_id = voice_id if voice_id and "-" in voice_id else "ko-KR-Neural2-A"
            generate_google_tts(text, output_path, voice_name=v_id, api_key=api_key, rate=rate)
            print("[TTS] Google Cloud TTS succeeded!")
            return "google"
        except Exception as e:
            print(f"[TTS Warning] Google Cloud TTS failed: {e}. Falling back to Microsoft Edge TTS...")
            
    elif provider == "elevenlabs":
        try:
            print(f"[TTS] Attempting ElevenLabs TTS with voice {voice_id}...")
            vid = voice_id if voice_id else "pNInz6obpgq5mWzIA5FD"
            generate_elevenlabs_tts(text, output_path, voice_id=vid, api_key=api_key,
                                    stability=v4_voice_stability, clarity=v4_voice_clarity, style=v4_voice_style)
            print("[TTS] ElevenLabs TTS succeeded!")
            return "elevenlabs"
        except Exception as e:
            print(f"[TTS Warning] ElevenLabs TTS failed: {e}. Falling back to Microsoft Edge TTS...")
            
    # Default to Edge-TTS
    edge_voice = voice_id if voice_id and voice_id.startswith("ko-KR") and "Neural" in voice_id else "ko-KR-InJoonNeural"
    generate_tts(text, output_path, voice=edge_voice, rate=rate)
    print(f"[TTS] Microsoft Edge TTS ({edge_voice}) succeeded!")
    return "edge"


def generate_script_from_gemini(topic, is_shorts=True, character_desc="", visual_style="", content_skin="🎬 역사 다큐멘터리 (Historical Documentary)"):
    """Use Gemini 2.5 Pro to structure a high-fidelity cinematic script containing visual, camera, BGM, and SFX directives."""
    from google import genai
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in .env file.")
        
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    duration_guide = "1분 이내 (쇼츠 포맷, 씬 4~5개 분량)" if is_shorts else "5분 내외 (일반 영상 포맷, 씬 10~15개 분량)"
    layout_guide = "세로형 (9:16)" if is_shorts else "가로형 (16:9)"
    
    # Retrieve configuration for selected skin
    skin_info = SKIN_CONFIGS.get(content_skin, SKIN_CONFIGS["🎬 역사 다큐멘터리 (Historical Documentary)"])
    persona = skin_info["persona"]
    narration_style = skin_info["narration_style"]
    recommended_visual = skin_info["visual_style"]
    recommended_bgm = skin_info["recommended_bgm"]
    
    consistency_guide = ""
    if character_desc:
        consistency_guide += f"\n- 주요 등장인물 묘사: {character_desc}\n  (중요: 캐릭터가 등장하는 모든 씬의 'visual_prompt'에는 해당 인물의 이름과 함께 위 묘사의 세부 외모 특징들을 반드시 구체적으로 기술하여 이미지 모델이 일관된 외모로 그리도록 하십시오.)"
    if visual_style:
        consistency_guide += f"\n- 비주얼 화풍 및 아트 스타일: {visual_style}\n  (중요: 모든 씬의 'visual_prompt'는 이 비주얼 화풍 가이드라인을 반영하여 통일성 있게 묘사해 주십시오.)"
    
    prompt = f"""
    당신은 {persona}입니다.
    주제: "{topic}"에 대해 시청자가 숨을 죽이고 몰입할 수 있는 최고의 시네마틱 비디오 시나리오를 설계해 주세요.
    분량 가이드: {duration_guide}
    영상 비율: {layout_guide}
    기본 비주얼 연출 스타일: {recommended_visual}
    {consistency_guide}

    [대본 구성 및 연출 지침 (Minimal History Style)]:
    1. 인트로 훅 (Scene 1): 일반적인 상식이나 당연한 것에 의문을 제기하는 강렬한 미스터리 질문으로 시작하여 시청자를 사로잡으십시오. (예: "혈액형은 단순히 병원에서 확인하는 수혈용 정보가 아닙니다. 그것은 수백만 년 동안...")
    2. 전개 (중간 Scene들): 인물들의 생존의 사투, 역사적 발견 과정, 또는 자연적 인과관계를 영화적인 긴장감을 가지고 시간순 혹은 논리적 구조로 추적하십시오.
    3. 아웃트로 (마지막 Scene): 단순 요약이 아닌, 역사적 혹은 인문학적 깊이를 지닌 철학적 성찰과 여운을 남기는 여운으로 장엄하게 마무리하십시오.
    4. 대본 분량 제어: 느린 발화 속도(-12% 감속)에 어울리도록, 각 씬의 나레이션(narration) 문장은 너무 길지 않고 정돈된 2~3문장 이내(쇼츠 기준 공백 포함 60~80자 내외, 일반 영상 기준 120~150자 내외)로 끊어 주십시오.

    반드시 아래 JSON 형식으로만 응답하세요. 다른 설명이나 텍스트는 일체 생략하고 순수 JSON 데이터만 반환해야 합니다.

    {{
      "title": "시청자의 시선을 강탈하는 제목 (클릭률 극대화)",
      "description": "동영상 요약본 및 관련 핵심 해시태그",
      "tags": ["태그1", "태그2", "태그3", "태그4"],
      "overall_bgm_mood": "전체 영상의 BGM 분위기 (예: '{recommended_bgm}'을 추천하지만, 상황에 맞게 'epic_orchestral', 'dark_mystery', 'sad_piano', 'intense_suspense' 중 택1)",
      "scenes": [
        {{
          "narration": "이 장면에 들어갈 한국어 나레이션 문장 ({narration_style})",
          "visual_prompt": "이 장면에 어울리는 영어 이미지 생성 프롬프트 (Flux/DALL-E 3용, 주제에 맞고 {recommended_visual} 스타일이 살도록 구체적으로 묘사)",
          "camera_movement": {{
            "type": "zoom_in / zoom_out / pan_left / pan_right / pan_up / pan_down",
            "speed": "slow / medium"
          }},
          "sfx_trigger": "이 장면에 들어갈 최적의 효과음 종류 (예: 'sword_clash', 'thunder', 'wind_howl', 'horse_gallop', 'fire_crackle', 'none' 중 택1)",
          "sfx_timing": "start / middle / end"
        }}
      ]
    }}
    """
    
    max_retries = 3
    response_text = ""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt
            )
            response_text = response.text.strip()
            break
        except Exception as e:
            if ("503" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[Warning] Gemini API busy ({e}). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise e
    
    if response_text.startswith("```json"):
        response_text = re.sub(r"^```json\s*", "", response_text)
        response_text = re.sub(r"\s*```$", "", response_text)
    elif response_text.startswith("```"):
        response_text = re.sub(r"^```\s*", "", response_text)
        response_text = re.sub(r"\s*```$", "", response_text)
        
    try:
        data = json.loads(response_text)
        return data
    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error: {e}\nRaw Output: {response_text}")
        return {
            "title": f"{topic}의 비밀",
            "description": f"{topic}에 대한 흥미로운 역사 탐구 #역사 #상식",
            "tags": [topic, "역사", "비밀", "미스터리"],
            "overall_bgm_mood": "dark_mystery",
            "scenes": [
                {
                    "narration": f"우리가 잘 모르는 {topic}에 대한 놀라운 이야기, 지금 시작합니다.",
                    "visual_prompt": f"A historic and dramatic landscape representing {topic}, digital art, highly detailed, cinematic lighting",
                    "camera_movement": {
                        "type": "zoom_in",
                        "speed": "slow"
                    },
                    "sfx_trigger": "none",
                    "sfx_timing": "start"
                }
            ]
        }


def download_fal_ai_image(prompt, output_path, is_shorts=True, api_key=None):
    """Download a Flux.1 Dev generated image via Fal.ai API using raw requests polling."""
    if not api_key or api_key == "your_fal_api_key_here" or api_key.strip() == "":
        raise ValueError("Fal.ai API key is missing.")
        
    model_endpoint = "fal-ai/flux/dev"
    url = f"https://queue.fal.run/{model_endpoint}"
    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json"
    }
    
    image_size = "9:16" if is_shorts else "16:9"
    payload = {
        "prompt": prompt,
        "image_size": image_size,
        "sync_mode": False
    }
    
    print(f"[Fal.ai] Submitting image request for: {prompt[:40]}...")
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code != 200:
        raise Exception(f"Fal.ai submit failed with status {response.status_code}: {response.text}")
        
    data = response.json()
    status_url = data.get("status_url")
    if not status_url:
        raise Exception(f"Fal.ai submit response did not return status_url: {data}")
        
    max_retries = 30
    for i in range(max_retries):
        status_resp = requests.get(status_url, headers=headers, timeout=10)
        if status_resp.status_code != 200:
            print(f"[Fal.ai Warning] Poll failed, retrying... Status: {status_resp.status_code}")
            time.sleep(2)
            continue
            
        status_data = status_resp.json()
        status = status_data.get("status")
        print(f"[Fal.ai] Polling... Status: {status}")
        
        if status == "COMPLETED":
            images = status_data.get("images") or status_data.get("output", {}).get("images", [])
            if images:
                img_url = images[0].get("url")
                print(f"[Fal.ai] Download link obtained: {img_url}")
                img_resp = requests.get(img_url, timeout=20)
                if img_resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(img_resp.content)
                    return True
                else:
                    raise Exception(f"Failed to download image from URL: {img_url}")
            else:
                raise Exception(f"Fal.ai COMPLETED but no images in output: {status_data}")
        elif status in ["FAILED", "ERROR"]:
            raise Exception(f"Fal.ai task failed: {status_data}")
            
        time.sleep(2)
        
    raise Exception("Fal.ai image generation timed out after 60 seconds.")


def download_dalle3_image(prompt, output_path, is_shorts=True, api_key=None):
    """Download a DALL-E 3 generated image via OpenAI API."""
    if not api_key or api_key == "your_openai_api_key_here" or api_key.strip() == "":
        raise ValueError("OpenAI API key is missing.")
        
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    size = "1024x1792" if is_shorts else "1792x1024"
    
    print(f"[DALL-E 3] Generating image for: {prompt[:40]}...")
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="standard",
        n=1
    )
    img_url = response.data[0].url
    print(f"[DALL-E 3] Download link obtained: {img_url}")
    
    img_resp = requests.get(img_url, timeout=20)
    if img_resp.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(img_resp.content)
        return True
    else:
        raise Exception(f"Failed to download image from URL: {img_url}")


def download_pollinations_image(prompt, output_path, is_shorts=True):
    """Download a high-quality AI generated image from Pollinations.ai (Completely Free & No Key) with retries."""
    width = 1080 if is_shorts else 1920
    height = 1920 if is_shorts else 1080
    
    # Clean special characters from the prompt that might confuse the API
    clean_prompt = prompt.replace(":", " ").replace("(", " ").replace(")", " ")
    safe_prompt = urllib.parse.quote(clean_prompt)
    
    import random
    
    max_retries = 3
    for attempt in range(max_retries):
        seed = random.randint(1, 100000)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
        
        try:
            print(f"[Pollinations] Attempt {attempt+1}/{max_retries} for url: {url[:80]}...")
            response = requests.get(url, timeout=40)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    print(f"[Pollinations] Success on attempt {attempt+1}!")
                    return True
        except Exception as e:
            print(f"[Pollinations Warning] Attempt {attempt+1} failed: {e}")
            
        time.sleep(2)
        
    return False


def generate_cinematic_image(prompt, output_path, is_shorts=True, provider="pollinations", fal_key=None, openai_key=None, gemini_key=None):
    """Download or generate high-quality images with selection of provider and robust fallback to Pollinations."""
    success = False
    
    if provider == "google":
        try:
            aspect_ratio = "9:16" if is_shorts else "16:9"
            success = download_imagen_image(prompt, output_path, aspect_ratio=aspect_ratio, api_key=gemini_key)
        except Exception as e:
            print(f"[Image Warning] Google Imagen 3 generation failed: {e}. Falling back to Pollinations...")
            
    elif provider == "fal-ai":
        try:
            success = download_fal_ai_image(prompt, output_path, is_shorts, api_key=fal_key)
        except Exception as e:
            print(f"[Image Warning] Fal.ai image generation failed: {e}. Falling back to Pollinations...")
            
    elif provider == "dall-e-3":
        try:
            success = download_dalle3_image(prompt, output_path, is_shorts, api_key=openai_key)
        except Exception as e:
            print(f"[Image Warning] DALL-E 3 image generation failed: {e}. Falling back to Pollinations...")
            
    if not success:
        print("[Image] Generating image via Pollinations.ai...")
        success = download_pollinations_image(prompt, output_path, is_shorts)
        
    if not success or not os.path.exists(output_path):
        print(f"[Image Error] Fallback image download failed. Creating solid dark color background...")
        width, height = (1080, 1920) if is_shorts else (1920, 1080)
        fallback_img = Image.new("RGB", (width, height), (30, 30, 30))
        draw = ImageDraw.Draw(fallback_img)
        draw.rectangle([0, 0, width, 20], fill=(255, 75, 75)) # Red accent bar
        fallback_img.save(output_path, "JPEG")
        success = True
        
    return success


def make_ken_burns_clip(image_path, duration, target_size=(1080, 1920), movement_type="zoom_in", speed="slow", easing="Linear"):
    """Creates a VideoClip of an image with Ken Burns camera effect (zoom/pan) using advanced easing curves."""
    img = Image.open(image_path).convert("RGB")
    w_orig, h_orig = img.size
    w_target, h_target = target_size
    
    scale_base = max(w_target / w_orig, h_target / h_orig)
    
    max_scale = 1.12 if speed == "slow" else 1.22
    
    w_large = int(w_orig * scale_base * max_scale)
    h_large = int(h_orig * scale_base * max_scale)
    img_large = img.resize((w_large, h_large), Image.Resampling.LANCZOS)
    
    def make_frame(t):
        p = t / duration if duration > 0 else 0
        p = min(1.0, max(0.0, p))
        
        # Apply easing function to interpolation value
        if "Cubic" in easing:
            # Cubic Ease-in-out: starts slow, speeds up in middle, ends slow
            if p < 0.5:
                p_eased = 4 * p * p * p
            else:
                p_eased = 1 - (-2 * p + 2)**3 / 2
        elif "Quadratic" in easing:
            # Quadratic Ease-out: starts fast, slows down at the end
            p_eased = 1 - (1 - p) * (1 - p)
        else:
            # Linear: constant speed
            p_eased = p
            
        if movement_type == "zoom_in":
            scale = max_scale - (max_scale - 1.0) * p_eased
        elif movement_type == "zoom_out":
            scale = 1.0 + (max_scale - 1.0) * p_eased
        else:
            scale = 1.10
            
        w_box = w_target * scale
        h_box = h_target * scale
        
        cx = w_large / 2
        cy = h_large / 2
        
        max_shift_x = (w_large - w_box) / 2
        max_shift_y = (h_large - h_box) / 2
        
        if movement_type == "pan_left":
            cx = (w_large / 2) - max_shift_x + (2 * max_shift_x * p_eased)
        elif movement_type == "pan_right":
            cx = (w_large / 2) + max_shift_x - (2 * max_shift_x * p_eased)
        elif movement_type == "pan_up":
            cy = (h_large / 2) - max_shift_y + (2 * max_shift_y * p_eased)
        elif movement_type == "pan_down":
            cy = (h_large / 2) + max_shift_y - (2 * max_shift_y * p_eased)
            
        x0 = int(cx - w_box / 2)
        y0 = int(cy - h_box / 2)
        x1 = x0 + int(w_box)
        y1 = y0 + int(h_box)
        
        x0 = max(0, min(x0, w_large - int(w_box)))
        y0 = max(0, min(y0, h_large - int(h_box)))
        x1 = x0 + int(w_box)
        y1 = y0 + int(h_box)
        
        cropped = img_large.crop((x0, y0, x1, y1))
        final_frame = cropped.resize((w_target, h_target), Image.Resampling.LANCZOS)
        
        return np.array(final_frame)
        
    clip = VideoClip(make_frame, duration=duration)
    clip.size = target_size
    clip.fps = 24
    return clip


def fetch_pexels_stock_video(query, output_path, is_shorts=True, api_key=None):
    """Search and download a stock video from Pexels API matching the query."""
    if not api_key or api_key == "your_pexels_api_key_here" or api_key.strip() == "":
        raise ValueError("Pexels API key is missing.")
        
    url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&per_page=5"
    headers = {"Authorization": api_key}
    
    print(f"[Pexels] Searching stock video for query: {query}...")
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Pexels search failed: {response.status_code}, {response.text}")
        
    data = response.json()
    videos = data.get("videos", [])
    if not videos:
        raise Exception(f"No stock videos found on Pexels for query: {query}")
        
    # Filter for matching aspect ratio if possible
    selected_video_url = None
    for video in videos:
        video_files = video.get("video_files", [])
        # Find a file with suitable resolution/aspect ratio
        for vf in video_files:
            width = vf.get("width") or 0
            height = vf.get("height") or 0
            file_type = vf.get("file_type", "")
            if "mp4" in file_type:
                # For shorts, prefer vertical
                if is_shorts and height > width:
                    selected_video_url = vf.get("link")
                    break
                # For normal, prefer landscape
                elif not is_shorts and width > height:
                    selected_video_url = vf.get("link")
                    break
        if selected_video_url:
            break
            
    # Fallback to first video's first file if no aspect ratio match
    if not selected_video_url and videos:
        video_files = videos[0].get("video_files", [])
        for vf in video_files:
            if "mp4" in vf.get("file_type", ""):
                selected_video_url = vf.get("link")
                break
                
    if not selected_video_url:
        raise Exception(f"No valid MP4 video files found for query: {query}")
        
    print(f"[Pexels] Downloading stock video: {selected_video_url[:60]}...")
    v_resp = requests.get(selected_video_url, timeout=30)
    if v_resp.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(v_resp.content)
        return True
    else:
        raise Exception(f"Failed to download video file: Status {v_resp.status_code}")


def generate_fal_ai_video(prompt, output_path, is_shorts=True, api_key=None):
    """Generate an AI video clip using Luma Dream Machine on Fal.ai."""
    if not api_key or api_key == "your_fal_api_key_here" or api_key.strip() == "":
        raise ValueError("Fal.ai API key is missing.")
        
    model_endpoint = "fal-ai/luma-dream-machine/t2v"
    url = f"https://queue.fal.run/{model_endpoint}"
    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json"
    }
    
    aspect_ratio = "9:16" if is_shorts else "16:9"
    payload = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio
    }
    
    print(f"[Fal.ai Video] Submitting video request for: {prompt[:40]}...")
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code != 200:
        raise Exception(f"Fal.ai Video submit failed with status {response.status_code}: {response.text}")
        
    data = response.json()
    status_url = data.get("status_url")
    if not status_url:
        raise Exception(f"Fal.ai Video submit response did not return status_url: {data}")
        
    max_retries = 60
    for i in range(max_retries):
        status_resp = requests.get(status_url, headers=headers, timeout=10)
        if status_resp.status_code != 200:
            print(f"[Fal.ai Video Warning] Poll failed, retrying... Status: {status_resp.status_code}")
            time.sleep(3)
            continue
            
        status_data = status_resp.json()
        status = status_data.get("status")
        print(f"[Fal.ai Video] Polling... Status: {status}")
        
        if status == "COMPLETED":
            video = status_data.get("video") or status_data.get("output", {}).get("video", {})
            video_url = video.get("url")
            if video_url:
                print(f"[Fal.ai Video] Download link obtained: {video_url}")
                vid_resp = requests.get(video_url, timeout=45)
                if vid_resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(vid_resp.content)
                    return True
                else:
                    raise Exception(f"Failed to download video from URL: {video_url}")
            else:
                raise Exception(f"Fal.ai Video COMPLETED but no video url in output: {status_data}")
        elif status in ["FAILED", "ERROR"]:
            raise Exception(f"Fal.ai Video task failed: {status_data}")
            
        time.sleep(4)
        
    raise Exception("Fal.ai Video generation timed out after 240 seconds.")


def make_circular_avatar(image_path, size=240):
    """Crop an image into a circle with a premium border and return the path."""
    img = Image.open(image_path).convert("RGBA")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Create circular mask
    mask = Image.new("L", (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size, size), fill=255)
    
    # Apply mask to image
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask=mask)
    
    # Draw premium red border
    draw_out = ImageDraw.Draw(output)
    border_w = 6
    draw_out.ellipse((border_w//2, border_w//2, size - border_w//2, size - border_w//2), outline=(255, 75, 75, 255), width=border_w)
    
    out_path = image_path.replace(".jpg", "_avatar.png")
    output.save(out_path, "PNG")
    return out_path


def add_film_grain_filter(clip, intensity=15):
    """Applies a dynamic film grain filter to a clip using integer-based random noise."""
    if intensity <= 0:
        return clip
    
    def filter_func(image):
        h, w, c = image.shape
        max_noise = max(1, int(intensity * 0.25))
        noise = np.random.randint(-max_noise, max_noise + 1, (h, w, c), dtype=np.int16)
        noisy = image.astype(np.int16) + noise
        return np.clip(noisy, 0, 255).astype(np.uint8)
        
    return clip.fl_image(filter_func)


def add_vignette_filter(clip):
    """Applies a dark cinematic vignette effect to the edges of the video."""
    h, w = clip.size[1], clip.size[0]
    
    y = np.linspace(-1.0, 1.0, h)
    x = np.linspace(-1.0, 1.0, w)
    xx, yy = np.meshgrid(x, y)
    d = xx**2 + yy**2
    
    mask = 1.0 - 0.40 * np.minimum(1.0, d)
    mask = mask[:, :, np.newaxis]
    
    def filter_func(image):
        return (image.astype(np.float32) * mask).astype(np.uint8)
        
    return clip.fl_image(filter_func)


def apply_stereo_panning(audio_clip, duration, direction="left_to_right"):
    """Applies stereo panning to an audio clip over its duration using sin/cos power preservation."""
    def pan_filter(gf, t):
        frames = gf(t)
        
        if isinstance(t, np.ndarray):
            p = t / duration
            p = np.clip(p, 0.0, 1.0)
            if direction == "right_to_left":
                p = 1.0 - p
            
            p = p[:, np.newaxis]
            
            if len(frames.shape) == 1:
                frames = np.column_stack((frames, frames))
            elif frames.shape[1] == 1:
                frames = np.hstack((frames, frames))
                
            left_vol = np.cos(p * np.pi / 2)
            right_vol = np.sin(p * np.pi / 2)
            
            panned = np.zeros_like(frames)
            panned[:, 0] = frames[:, 0] * left_vol[:, 0]
            panned[:, 1] = frames[:, 1] * right_vol[:, 0]
            return panned
        else:
            p = t / duration
            p = min(1.0, max(0.0, p))
            if direction == "right_to_left":
                p = 1.0 - p
                
            left_vol = np.cos(p * np.pi / 2)
            right_vol = np.sin(p * np.pi / 2)
            
            if len(frames.shape) == 0:
                frames = np.array([frames, frames])
            elif len(frames.shape) == 1 and frames.shape[0] == 1:
                frames = np.array([frames[0], frames[0]])
            elif len(frames.shape) == 1 and frames.shape[0] == 2:
                pass
            else:
                frames = np.column_stack((frames, frames))
                
            panned = np.array([frames[0] * left_vol, frames[1] * right_vol])
            return panned
            
    return audio_clip.fl(pan_filter)


def apply_compressor_filter(audio_clip, threshold=0.15, ratio=4.0, makeup_gain=1.3):
    """Applies a dynamic range compressor/limiter to the audio clip to make dialogue punchy and professional."""
    def compressor(gf, t):
        frames = gf(t)
        abs_frames = np.abs(frames)
        mask = abs_frames > threshold
        compressed = np.copy(frames)
        
        if np.any(mask):
            excess = abs_frames[mask] - threshold
            compressed_excess = threshold + excess / ratio
            scale = compressed_excess / abs_frames[mask]
            compressed[mask] = frames[mask] * scale
            
        compressed = compressed * makeup_gain
        return np.clip(compressed, -0.99, 0.99)
        
    return audio_clip.fl(compressor)


def download_imagen_image(prompt, output_path, aspect_ratio="9:16", api_key=None):
    """Generate an image using Vertex AI / Google GenAI SDK Imagen 3 model."""
    from google import genai
    
    k = api_key or os.getenv("GEMINI_API_KEY")
    if not k:
        raise ValueError("Google API key (GEMINI_API_KEY) is required for Imagen 3.")
        
    client = genai.Client(api_key=k)
    
    ratio = "9:16"
    if "16:9" in aspect_ratio:
        ratio = "16:9"
    elif "1:1" in aspect_ratio:
        ratio = "1:1"
        
    print(f"[Imagen 3] Requesting image (ratio: {ratio}) for: {prompt[:50]}...")
    
    result = client.models.generate_images(
        model='imagen-3.0-generate-002',
        prompt=prompt,
        config=dict(
            number_of_images=1,
            output_mime_type="image/jpeg",
            aspect_ratio=ratio,
        )
    )
    
    if result.generated_images:
        img_bytes = result.generated_images[0].image.image_bytes
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        print("[Imagen 3] Image generated successfully!")
        return True
    else:
        raise Exception("Imagen 3 API did not return any generated images.")


def upload_file_to_gcs(local_path, bucket_name, destination_blob_name):
    """Uploads a file to Google Cloud Storage bucket."""
    try:
        from google.cloud import storage
        print(f"[GCS] Uploading {local_path} to bucket '{bucket_name}' as '{destination_blob_name}'...")
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        blob.upload_from_filename(local_path)
        url = blob.public_url
        print(f"[GCS] Upload succeeded! public_url: {url}")
        return url
    except Exception as e:
        print(f"[GCS Warning] Failed to upload to GCS: {e}")
        return None


def fetch_script_from_google_sheets(sheet_id):
    """Fetches script scenes from a public or link-shared Google Spreadsheet."""
    import csv
    import io
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    print(f"[Google Sheets] Fetching sheet from export URL: {url}")
    response = requests.get(url, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch Google Sheet: Status {response.status_code}")
    
    csv_file = io.StringIO(response.text)
    reader = csv.DictReader(csv_file)
    
    scenes = []
    for row in reader:
        norm_row = {k.lower().strip(): v for k, v in row.items()}
        
        narration = norm_row.get("narration") or norm_row.get("text") or norm_row.get("대사") or ""
        visual_prompt = norm_row.get("visual_prompt") or norm_row.get("prompt") or norm_row.get("이미지프롬프트") or ""
        
        if not narration and not visual_prompt:
            continue
            
        camera_type = norm_row.get("camera_movement") or norm_row.get("camera") or "zoom_in"
        camera_speed = norm_row.get("camera_speed") or "slow"
        sfx_trigger = norm_row.get("sfx_trigger") or norm_row.get("sfx") or "none"
        sfx_timing = norm_row.get("sfx_timing") or "start"
        
        scenes.append({
            "narration": narration.strip(),
            "visual_prompt": visual_prompt.strip(),
            "camera_movement": {"type": camera_type.strip(), "speed": camera_speed.strip()},
            "sfx_trigger": sfx_trigger.strip(),
            "sfx_timing": sfx_timing.strip()
        })
        
    if not scenes:
        raise Exception("No valid rows containing 'narration' or 'visual_prompt' columns found in Sheet.")
        
    return {
        "title": "Google Sheets AI Video Script",
        "description": "Generated automatically from Google Sheets",
        "tags": ["sheets_auto", "ai_video"],
        "overall_bgm_mood": "epic_orchestral",
        "scenes": scenes
    }


def build_scene_video(scene_idx, scene_data, is_shorts=True, 
                      tts_provider="edge", tts_voice_id=None, tts_api_key=None,
                      image_provider="pollinations", fal_key=None, openai_key=None,
                      target_size=None, video_skin="Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)",
                      pexels_key=None, topic="", content_skin="🎬 역사 다큐멘터리 (Historical Documentary)",
                      temp_dir="temp_assets",
                      v4_easing="Linear", v4_3d_panning=False,
                      v4_voice_stability=0.75, v4_voice_clarity=0.75, v4_voice_style=0.0,
                      gemini_key=None):
    """Render a single scene: merges narration audio, visuals based on selected technical skin, subtitles, and SFX."""
    print(f"[Scene {scene_idx}] Rendering scene with skin: {video_skin} (Easing: {v4_easing}, Panning: {v4_3d_panning})...")
    
    audio_path = os.path.join(temp_dir, f"audio_{scene_idx}.mp3")
    img_path = os.path.join(temp_dir, f"visual_{scene_idx}.jpg")
    subtitle_path = os.path.join(temp_dir, f"sub_{scene_idx}.png")
    
    # Set narration pace rate dynamically based on content skin (historical/horror/fiction should be slow)
    is_slow_skin = "역사" in content_skin or "소설" in content_skin or "공포" in content_skin
    tts_rate = "-12%" if is_slow_skin else "-2%"
    
    # 1. Synthesize narration
    generate_voice_over(
        scene_data["narration"], audio_path, 
        provider=tts_provider, voice_id=tts_voice_id, api_key=tts_api_key, rate=tts_rate,
        v4_voice_stability=v4_voice_stability, v4_voice_clarity=v4_voice_clarity, v4_voice_style=v4_voice_style
    )
    narr_clip = AudioFileClip(audio_path)
    narr_duration = narr_clip.duration
    
    # Add 1.5 seconds breather at the end of the scene for cinematic pacing
    scene_duration = narr_duration + 1.5
    
    if target_size is None:
        target_size = (1080, 1920) if is_shorts else (1920, 1080)
    width, height = target_size
    
    # 2. Get visuals based on selected technical skin
    visual_clip = None
    
    if "Option 2" in video_skin: # AI Video Generation
        try:
            video_clip_path = os.path.join(temp_dir, f"video_{scene_idx}.mp4")
            prompt = scene_data.get("visual_prompt", "A dramatic cinematic scene")
            
            # Apply global visual style guidelines for AI video prompt
            if "역사" in content_skin:
                prompt = f"Moody historical oil painting style, dark academia, dramatic chiaroscuro, {prompt}, cinematic, 8k"
            elif "공포" in content_skin:
                prompt = f"Dark gothic horror scene, misty, dramatic moonlight, {prompt}, scary, 8k"
                
            generate_fal_ai_video(prompt, video_clip_path, is_shorts=is_shorts, api_key=fal_key)
            
            raw_vid_clip = VideoFileClip(video_clip_path)
            if raw_vid_clip.duration < scene_duration:
                visual_clip = raw_vid_clip.loop(duration=scene_duration)
            else:
                visual_clip = raw_vid_clip.subclip(0, scene_duration)
            visual_clip = visual_clip.resize(target_size)
            print(f"[Scene {scene_idx}] Generated AI video clip successfully!")
        except Exception as e:
            print(f"[Scene {scene_idx} Warning] AI video generation failed: {e}. Falling back to Ken Burns image...")
            visual_clip = None
            
    elif "Option 3" in video_skin: # Stock Video Matching
        try:
            video_clip_path = os.path.join(temp_dir, f"stock_{scene_idx}.mp4")
            prompt = scene_data.get("visual_prompt", "")
            
            # Form search query from prompt descriptors
            search_query = topic if topic else "cinematic"
            if prompt:
                search_query = prompt.split(",")[0]
                
            fetch_pexels_stock_video(search_query, video_clip_path, is_shorts=is_shorts, api_key=pexels_key)
            
            raw_vid_clip = VideoFileClip(video_clip_path)
            if raw_vid_clip.duration < scene_duration:
                visual_clip = raw_vid_clip.loop(duration=scene_duration)
            else:
                visual_clip = raw_vid_clip.subclip(0, scene_duration)
            visual_clip = visual_clip.resize(target_size)
            print(f"[Scene {scene_idx}] Fetched stock video successfully!")
        except Exception as e:
            print(f"[Scene {scene_idx} Warning] Stock video search failed: {e}. Falling back to Ken Burns image...")
            visual_clip = None
            
    elif "Option 5" in video_skin: # Typography (Abstract background)
        # Generate abstract background image
        bg_prompt = "Abstract elegant liquid gradient background, smooth dark colors, high resolution, minimalist"
        generate_cinematic_image(bg_prompt, img_path, is_shorts=is_shorts, provider=image_provider, fal_key=fal_key, openai_key=openai_key, gemini_key=gemini_key)
        visual_clip = make_ken_burns_clip(img_path, scene_duration, target_size=target_size, movement_type="zoom_in", speed="slow", easing=v4_easing)
        
    # Default fallback / Option 1 / Option 4 background
    if visual_clip is None:
        prompt = scene_data.get("visual_prompt", "A dramatic cinematic scene")
        
        # Apply global visual style guidelines dynamically for AI images
        if "역사" in content_skin:
            prompt = f"Masterpiece, oil painting style, dark academia atmosphere, dramatic chiaroscuro lighting, deep contrast:1.2, {prompt}, moody historical illustration, highly detailed, cinematic texture, 8k, muted colors, soft vignetting"
        elif "공포" in content_skin:
            prompt = f"Dark gothic horror illustration, misty foggy atmosphere, dramatic moonlight, spooky shadows, {prompt}, masterpiece, 8k, highly detailed, chilling ambiance"
        elif "소설" in content_skin:
            prompt = f"Fantasy watercolor illustration, soft dreamlike warm light, pastel color palette, emotional scenery, {prompt}, masterpiece, highly detailed, fairytale aesthetic"
            
        generate_cinematic_image(prompt, img_path, is_shorts=is_shorts, provider=image_provider, fal_key=fal_key, openai_key=openai_key, gemini_key=gemini_key)
        
        cam_info = scene_data.get("camera_movement", {})
        cam_type = cam_info.get("type", "zoom_in")
        cam_speed = cam_info.get("speed", "slow")
        visual_clip = make_ken_burns_clip(img_path, scene_duration, target_size=target_size, movement_type=cam_type, speed=cam_speed, easing=v4_easing)
        
    # 3. Create Subtitle Overlay
    # Option 5 places subtitle in center
    sub_position = "center" if "Option 5" in video_skin else "bottom"
    is_serif = "역사" in content_skin or "소설" in content_skin or "공포" in content_skin
    f_style = "serif" if is_serif else "gothic"
    create_subtitle_image(scene_data["narration"], width, height, font_size=56 if sub_position == "center" else 42, output_path=subtitle_path, position=sub_position, font_style=f_style)
    sub_clip = ImageClip(subtitle_path).set_duration(narr_duration)
    
    # 4. Talking Avatar overlay (Option 4)
    avatar_clip = None
    if "Option 4" in video_skin:
        try:
            presenter_prompt = "A professional neat news presenter avatar, close-up portrait, polite expression, front view, studio background, realistic photorealistic, 8k resolution"
            presenter_img_path = os.path.join(temp_dir, f"presenter_{scene_idx}.jpg")
            generate_cinematic_image(presenter_prompt, presenter_img_path, is_shorts=True, provider=image_provider, fal_key=fal_key, openai_key=openai_key, gemini_key=gemini_key)
            
            avatar_path = make_circular_avatar(presenter_img_path, size=260)
            raw_avatar_clip = ImageClip(avatar_path).set_duration(scene_duration)
            
            if is_shorts:
                avatar_pos = (width // 2 - 130, int(height * 0.72) - 320)
            else:
                avatar_pos = (width - 340, height - 340)
                
            avatar_clip = raw_avatar_clip.set_position(avatar_pos)
            print(f"[Scene {scene_idx}] Overlayed talking avatar badge successfully!")
        except Exception as e:
            print(f"[Scene {scene_idx} Warning] Failed to generate avatar badge: {e}")
            
    # Composite all visual tracks
    visual_tracks = [visual_clip]
    if avatar_clip:
        visual_tracks.append(avatar_clip)
    visual_tracks.append(sub_clip.set_start(0))
    
    composite_clip = CompositeVideoClip(visual_tracks, size=target_size).set_duration(scene_duration)
    
    # 4. Sound Design (Narration + SFX mixing)
    scene_audio_tracks = [narr_clip.set_start(0)]
    
    sfx_trigger = scene_data.get("sfx_trigger", "none")
    sfx_timing = scene_data.get("sfx_timing", "start")
    
    if sfx_trigger != "none":
        sfx_file = os.path.join(SFX_DIR, f"{sfx_trigger}.mp3")
        if os.path.exists(sfx_file):
            try:
                sfx_clip = AudioFileClip(sfx_file).volumex(0.35) # 35% volume for SFX
                sfx_dur = min(sfx_clip.duration, scene_duration)
                sfx_clip = sfx_clip.subclip(0, sfx_dur)
                
                # Apply 3D stereo panning if enabled
                if v4_3d_panning:
                    direction = "right_to_left" if "left" in cam_type or "out" in cam_type else "left_to_right"
                    sfx_clip = apply_stereo_panning(sfx_clip, sfx_dur, direction=direction)
                    print(f"[Scene {scene_idx}] Applied stereo panning ({direction}) to SFX '{sfx_trigger}'")
                
                # Determine placement time
                if sfx_timing == "start":
                    start_time = 0
                elif sfx_timing == "middle":
                    start_time = narr_duration / 2
                else: # end
                    start_time = max(0, narr_duration - sfx_dur)
                    
                sfx_clip = sfx_clip.set_start(start_time)
                scene_audio_tracks.append(sfx_clip)
                print(f"[Scene {scene_idx}] Mixed SFX '{sfx_trigger}' at {start_time:.2f}s")
            except Exception as e:
                print(f"[Scene {scene_idx} Warning] Failed to mix SFX: {e}")
                
    scene_audio = CompositeAudioClip(scene_audio_tracks).set_duration(scene_duration)
    composite_clip = composite_clip.set_audio(scene_audio)
    composite_clip.fps = 24
    
    # Bake composite clip to intermediate file to resolve MoviePy nested timeline composition bugs fundamentally
    scene_output_path = os.path.join(temp_dir, f"scene_output_{scene_idx}.mp4")
    temp_audio_path = os.path.join(temp_dir, f"temp-scene-audio-{scene_idx}-{int(time.time())}.m4a")
    
    print(f"[Scene {scene_idx}] Baking composite clip to {scene_output_path}...")
    composite_clip.write_videofile(
        scene_output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=temp_audio_path,
        remove_temp=False
    )
    
    # Explicit resource cleanup to prevent Windows/Linux file locks and memory leaks
    try:
        composite_clip.close()
    except Exception:
        pass
    try:
        narr_clip.close()
    except Exception:
        pass
    if 'visual_clip' in locals() and visual_clip is not None:
        try:
            visual_clip.close()
        except Exception:
            pass
    if 'sub_clip' in locals() and sub_clip is not None:
        try:
            sub_clip.close()
        except Exception:
            pass
    if 'avatar_clip' in locals() and avatar_clip is not None:
        try:
            avatar_clip.close()
        except Exception:
            pass
    if 'sfx_clip' in locals() and 'sfx_clip' in globals() and sfx_clip is not None:
        try:
            sfx_clip.close()
        except Exception:
            pass
            
    baked_clip = VideoFileClip(scene_output_path)
    return baked_clip, narr_duration


def generate_full_video(topic, is_shorts=True, output_filename="final_output.mp4",
                        tts_provider="edge", tts_voice_id=None, tts_api_key=None,
                        image_provider="pollinations", fal_key=None, openai_key=None,
                        pregenerated_script=None, target_size=None,
                        character_desc="", visual_style="",
                        content_skin="🎬 역사 다큐멘터리 (Historical Documentary)",
                        video_skin="Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)",
                        pexels_key=None, progress_callback=None,
                        temp_dir=None,
                        v4_easing="Linear", v4_film_grain=0, v4_vignette=False,
                        v4_3d_panning=False, v4_compressor=False,
                        v4_voice_stability=0.75, v4_voice_clarity=0.75, v4_voice_style=0.0,
                        v5_gcs_bucket=""):
    """Entire video pipeline from scripting to final video composition with chosen technical skin."""
    print(f"[Start] Starting Cinematic AI Video Factory Pipeline with technical skin: {video_skin}...")
    
    # Create unique temp assets folder if not specified to prevent race condition in multi-user environments
    import uuid
    if temp_dir is None:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_assets_{int(time.time())}_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)
    
    if progress_callback:
        progress_callback("PREPARE")
        
    # Ensure default sound libraries are ready
    prepare_default_audio_assets()
    
    # 1. Generate Script
    if pregenerated_script:
        script_data = pregenerated_script
        print("[Script] Using pre-generated script.")
    else:
        script_data = generate_script_from_gemini(topic, is_shorts, character_desc, visual_style, content_skin)
        print(f"[Script] Script Generated! Title: {script_data['title']}")
    
    # 2. Build individual scene video clips
    scene_clips = []
    scenes_timeline = []
    current_time = 0.0
    
    for i, scene in enumerate(script_data["scenes"]):
        if progress_callback:
            progress_callback("SCENE", i, len(script_data["scenes"]))
        clip, narr_duration = build_scene_video(
            i, scene, is_shorts=is_shorts,
            tts_provider=tts_provider, tts_voice_id=tts_voice_id, tts_api_key=tts_api_key,
            image_provider=image_provider, fal_key=fal_key, openai_key=openai_key,
            target_size=target_size, video_skin=video_skin, pexels_key=pexels_key,
            topic=topic, content_skin=content_skin, temp_dir=temp_dir,
            v4_easing=v4_easing, v4_3d_panning=v4_3d_panning,
            v4_voice_stability=v4_voice_stability, v4_voice_clarity=v4_voice_clarity, v4_voice_style=v4_voice_style,
            gemini_key=os.getenv("GEMINI_API_KEY")
        )
        scene_clips.append(clip)
        
        # Track scene narration timings for BGM ducking
        scene_duration = clip.duration
        
        scenes_timeline.append((current_time, current_time + narr_duration, current_time + scene_duration))
        current_time += scene_duration
        
    # 3. Concatenate all scenes into a single video
    if progress_callback:
        progress_callback("MERGE")
    print("[Merge] Concatenating scenes...")
    # Force all clips to have the exact same fps to prevent concatenation frame rate mismatches
    aligned_clips = [c.set_fps(24) for c in scene_clips]
    
    # [Andrej Karpathy Style: First-principles timeline alignment]
    # In MoviePy 1.x, concatenate_videoclips(..., method="compose") wraps the subclips inside a single large 
    # CompositeVideoClip and offsets their start times (clip.set_start(t)). When the subclips are themselves 
    # nested CompositeVideoClips (e.g., background + subtitles + talking avatar overlays), the timeline 
    # translations (t - start) get double-applied or desynchronized, causing later scenes to render as black/corrupted frames.
    # By using method="chain" (the default), MoviePy sequentially chains the frames of successive clips directly.
    # This completely bypasses the nested timeline mapping bug. Since all our clips are strictly resized to the
    # target size and set to 24 FPS, method="chain" is clean, robust, and extremely fast.
    final_clip = concatenate_videoclips(aligned_clips, method="chain")
    
    # Apply post-processing visual filters
    if v4_vignette:
        print("[Video Vignette] Applying master vignette filter to final clip...")
        final_clip = add_vignette_filter(final_clip)
        
    if v4_film_grain > 0:
        print(f"[Video Film Grain] Applying master film grain filter (intensity: {v4_film_grain}) to final clip...")
        final_clip = add_film_grain_filter(final_clip, intensity=v4_film_grain)
    
    # 4. Cinematic BGM Ducking Mixer
    bgm_mood = script_data.get("overall_bgm_mood", "epic_orchestral")
    bgm_path = os.path.join(BGM_DIR, f"{bgm_mood}.mp3")
    
    if not os.path.exists(bgm_path):
        bgm_path = "bgm.mp3" if os.path.exists("bgm.mp3") else None
        
    if bgm_path and os.path.exists(bgm_path):
        try:
            if progress_callback:
                progress_callback("BGM")
            print(f"[BGM] Mixing and Ducking Background Music (Mood: {bgm_mood})...")
            bgm_clip = AudioFileClip(bgm_path)
            
            # Loop/fit BGM to total duration using MoviePy's afx.audio_loop
            import moviepy.audio.fx.all as afx
            if bgm_clip.duration < final_clip.duration:
                bgm_clip = afx.audio_loop(bgm_clip, duration=final_clip.duration)
            else:
                bgm_clip = bgm_clip.subclip(0, final_clip.duration)
                
            def get_single_volume(t_val):
                vol = 0.22  # Base volume (22%)
                fade_duration = 0.8
                for start, narr_end, end in scenes_timeline:
                    if start - fade_duration <= t_val <= narr_end + fade_duration:
                        if t_val < start:
                            # Fade out: linear interpolation from 0.22 down to 0.05
                            v_val = 0.22 - (0.22 - 0.05) * (t_val - (start - fade_duration)) / fade_duration
                        elif t_val > narr_end:
                            # Fade in: linear interpolation from 0.05 up to 0.22
                            v_val = 0.05 + (0.22 - 0.05) * (t_val - narr_end) / fade_duration
                        else:
                            # Inside narration: full duck
                            v_val = 0.05
                        vol = min(vol, v_val)
                return max(0.05, min(0.22, vol))

            # Create the dynamic volume filter
            def volume_filter(t):
                if isinstance(t, np.ndarray):
                    v = np.ones_like(t) * 0.22
                    for start, narr_end, end in scenes_timeline:
                        fade_duration = 0.8
                        # 1. Fade out region: [start - fade_duration, start]
                        fade_out_mask = (t >= start - fade_duration) & (t < start)
                        if np.any(fade_out_mask):
                            fade_out_vals = 0.22 - (0.22 - 0.05) * (t[fade_out_mask] - (start - fade_duration)) / fade_duration
                            v[fade_out_mask] = np.minimum(v[fade_out_mask], fade_out_vals)
                            
                        # 2. Narration region: [start, narr_end]
                        narr_mask = (t >= start) & (t <= narr_end)
                        v[narr_mask] = np.minimum(v[narr_mask], 0.05)
                        
                        # 3. Fade in region: [narr_end, narr_end + fade_duration]
                        fade_in_mask = (t > narr_end) & (t <= narr_end + fade_duration)
                        if np.any(fade_in_mask):
                            fade_in_vals = 0.05 + (0.22 - 0.05) * (t[fade_in_mask] - narr_end) / fade_duration
                            v[fade_in_mask] = np.minimum(v[fade_in_mask], fade_in_vals)
                            
                    return v[:, np.newaxis]
                else:
                    return get_single_volume(t)
                    
            # Apply volume filter over time
            ducked_bgm = bgm_clip.fl(lambda gf, t: gf(t) * volume_filter(t))
            
            # Mix with narration and SFX
            mixed_audio = CompositeAudioClip([final_clip.audio, ducked_bgm])
            if v4_compressor:
                print("[Audio Compressor] Applying master compressor/limiter to mixed audio...")
                mixed_audio = apply_compressor_filter(mixed_audio)
            final_clip = final_clip.set_audio(mixed_audio)
        except Exception as e:
            print(f"[BGM Warning] Failed to mix background music: {e}")
            
    # 5. Render final MP4 output
    if progress_callback:
        progress_callback("RENDER")
    print(f"[Render] Rendering final output video: {output_filename}...")
    # Use unique temp audio file path in temp_dir and disable MoviePy automatic deletion to prevent Windows file lock crashes
    temp_audio_path = os.path.join(temp_dir, f"temp-audio-{int(time.time())}.m4a")
    final_clip.write_videofile(
        output_filename,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=temp_audio_path,
        remove_temp=False
    )
    
    # Close clips to release files on Windows/Linux and prevent file locking during cleanup
    try:
        final_clip.close()
    except Exception:
        pass
    for c in scene_clips:
        try:
            c.close()
        except Exception:
            pass
        
    # 6. Cleanup temporary assets directory completely to release disk space in multi-user/server setups
    print(f"[Cleanup] Cleaning up temporary assets directory: {temp_dir}...")
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"[Cleanup Warning] Failed to delete temp directory {temp_dir}: {e}")
            
    # 7. Upload to Google Cloud Storage if bucket name is set
    if v5_gcs_bucket and v5_gcs_bucket.strip() != "":
        print(f"[GCS Integration] Attempting GCS upload to bucket '{v5_gcs_bucket}'...")
        destination_blob = f"videos/{os.path.basename(output_filename)}"
        gcs_url = upload_file_to_gcs(output_filename, v5_gcs_bucket, destination_blob)
        if gcs_url:
            script_data["gcs_url"] = gcs_url
            
    if progress_callback:
        progress_callback("DONE")
    print("[Success] Video Production Completed Successfully!")
    return output_filename, script_data


if __name__ == "__main__":
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print("Warning: Please set a valid GEMINI_API_KEY in your .env file to test.")
    else:
        test_topic = "율곡 이이의 십만양병설과 역사적 논쟁"
        generate_full_video(test_topic, is_shorts=True, output_filename="test_shorts.mp4")
