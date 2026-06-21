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


def ensure_korean_font():
    """Ensure a Korean TTF font is downloaded and available locally in the project directory."""
    local_font_path = "nanum_gothic.ttf"
    if os.path.exists(local_font_path) and os.path.getsize(local_font_path) > 100000:
        return local_font_path
    
    url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    print(f"[Font] Downloading NanumGothic font dynamically: {url}...")
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            with open(local_font_path, "wb") as f:
                f.write(response.content)
            print("[Font] NanumGothic downloaded successfully!")
            return local_font_path
    except Exception as e:
        print(f"[Font Error] Failed to download NanumGothic font: {e}")
    return None


def get_system_font(font_size=50):
    """Retrieve a usable Korean font from local workspace or Windows system fonts."""
    # 1. First priority: Check local NanumGothic font
    local_font = "nanum_gothic.ttf"
    if os.path.exists(local_font):
        try:
            return ImageFont.truetype(local_font, font_size)
        except Exception:
            pass
            
    # 2. Second priority: Attempt dynamic download fallback
    downloaded_font = ensure_korean_font()
    if downloaded_font and os.path.exists(downloaded_font):
        try:
            return ImageFont.truetype(downloaded_font, font_size)
        except Exception:
            pass

    # 3. Third priority: Windows system font search paths
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


def create_subtitle_image(text, width=1080, height=1920, font_size=48, output_path="subtitle.png", position="bottom"):
    """Create a transparent PNG containing styled Korean subtitle text at the bottom or center."""
    # Create transparent image
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    font = get_system_font(font_size)
    
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
        
        # Draw actual text
        draw.text((x, current_y), line, font=font, fill=(255, 255, 255, 255))
        
        current_y += line_h + 15
        
    image.save(output_path)
    return output_path


async def generate_tts_async(text, output_path, voice="ko-KR-InJoonNeural"):
    """Synthesize speech using Microsoft Edge TTS asynchronously."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_tts(text, output_path, voice="ko-KR-InJoonNeural"):
    """Sync wrapper for the Edge TTS async function."""
    asyncio.run(generate_tts_async(text, output_path, voice))


def generate_elevenlabs_tts(text, output_path, voice_id="pNInz6obpgq5mWzIA5FD", api_key=None):
    """Synthesize speech using ElevenLabs REST API."""
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
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(url, json=data, headers=headers, timeout=30)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        return True
    else:
        raise Exception(f"ElevenLabs TTS failed: Status {response.status_code}, {response.text}")


def generate_voice_over(text, output_path, provider="edge", voice_id=None, api_key=None):
    """Synthesize speech with selected provider and fallback to edge-tts if it fails."""
    if provider == "elevenlabs":
        try:
            print(f"[TTS] Attempting ElevenLabs TTS with voice {voice_id}...")
            vid = voice_id if voice_id else "pNInz6obpgq5mWzIA5FD"
            generate_elevenlabs_tts(text, output_path, voice_id=vid, api_key=api_key)
            print("[TTS] ElevenLabs TTS succeeded!")
            return "elevenlabs"
        except Exception as e:
            print(f"[TTS Warning] ElevenLabs TTS failed: {e}. Falling back to Microsoft Edge TTS...")
            
    # Default to Edge-TTS
    edge_voice = voice_id if voice_id and voice_id.startswith("ko-KR") else "ko-KR-InJoonNeural"
    generate_tts(text, output_path, voice=edge_voice)
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
    """Download a high-quality AI generated image from Pollinations.ai (Completely Free & No Key)."""
    width = 1080 if is_shorts else 1920
    height = 1920 if is_shorts else 1080
    
    safe_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&seed=42"
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"Pollinations Image Generation Failed: {e}")
    return False


def generate_cinematic_image(prompt, output_path, is_shorts=True, provider="pollinations", fal_key=None, openai_key=None):
    """Download or generate high-quality images with selection of provider and robust fallback to Pollinations."""
    success = False
    
    if provider == "fal-ai":
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


def make_ken_burns_clip(image_path, duration, target_size=(1080, 1920), movement_type="zoom_in", speed="slow"):
    """Creates a VideoClip of an image with Ken Burns camera effect (zoom/pan)."""
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
        
        if movement_type == "zoom_in":
            scale = max_scale - (max_scale - 1.0) * p
        elif movement_type == "zoom_out":
            scale = 1.0 + (max_scale - 1.0) * p
        else:
            scale = 1.10
            
        w_box = w_target * scale
        h_box = h_target * scale
        
        cx = w_large / 2
        cy = h_large / 2
        
        max_shift_x = (w_large - w_box) / 2
        max_shift_y = (h_large - h_box) / 2
        
        if movement_type == "pan_left":
            cx = (w_large / 2) - max_shift_x + (2 * max_shift_x * p)
        elif movement_type == "pan_right":
            cx = (w_large / 2) + max_shift_x - (2 * max_shift_x * p)
        elif movement_type == "pan_up":
            cy = (h_large / 2) - max_shift_y + (2 * max_shift_y * p)
        elif movement_type == "pan_down":
            cy = (h_large / 2) + max_shift_y - (2 * max_shift_y * p)
            
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


def build_scene_video(scene_idx, scene_data, is_shorts=True, 
                      tts_provider="edge", tts_voice_id=None, tts_api_key=None,
                      image_provider="pollinations", fal_key=None, openai_key=None,
                      target_size=None, video_skin="Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)",
                      pexels_key=None, topic=""):
    """Render a single scene: merges narration audio, visuals based on selected technical skin, subtitles, and SFX."""
    print(f"[Scene {scene_idx}] Rendering scene with skin: {video_skin}...")
    
    audio_path = os.path.join(TEMP_DIR, f"audio_{scene_idx}.mp3")
    img_path = os.path.join(TEMP_DIR, f"visual_{scene_idx}.jpg")
    subtitle_path = os.path.join(TEMP_DIR, f"sub_{scene_idx}.png")
    
    # 1. Synthesize narration
    generate_voice_over(scene_data["narration"], audio_path, provider=tts_provider, voice_id=tts_voice_id, api_key=tts_api_key)
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
            video_clip_path = os.path.join(TEMP_DIR, f"video_{scene_idx}.mp4")
            prompt = scene_data.get("visual_prompt", "A dramatic cinematic scene")
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
            video_clip_path = os.path.join(TEMP_DIR, f"stock_{scene_idx}.mp4")
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
        generate_cinematic_image(bg_prompt, img_path, is_shorts=is_shorts, provider=image_provider, fal_key=fal_key, openai_key=openai_key)
        visual_clip = make_ken_burns_clip(img_path, scene_duration, target_size=target_size, movement_type="zoom_in", speed="slow")
        
    # Default fallback / Option 1 / Option 4 background
    if visual_clip is None:
        prompt = scene_data.get("visual_prompt", "A dramatic cinematic scene")
        generate_cinematic_image(prompt, img_path, is_shorts=is_shorts, provider=image_provider, fal_key=fal_key, openai_key=openai_key)
        
        cam_info = scene_data.get("camera_movement", {})
        cam_type = cam_info.get("type", "zoom_in")
        cam_speed = cam_info.get("speed", "slow")
        visual_clip = make_ken_burns_clip(img_path, scene_duration, target_size=target_size, movement_type=cam_type, speed=cam_speed)
        
    # 3. Create Subtitle Overlay
    # Option 5 places subtitle in center
    sub_position = "center" if "Option 5" in video_skin else "bottom"
    create_subtitle_image(scene_data["narration"], width, height, font_size=56 if sub_position == "center" else 42, output_path=subtitle_path, position=sub_position)
    sub_clip = ImageClip(subtitle_path).set_duration(narr_duration)
    
    # 4. Talking Avatar overlay (Option 4)
    avatar_clip = None
    if "Option 4" in video_skin:
        try:
            presenter_prompt = "A professional neat news presenter avatar, close-up portrait, polite expression, front view, studio background, realistic photorealistic, 8k resolution"
            presenter_img_path = os.path.join(TEMP_DIR, f"presenter_{scene_idx}.jpg")
            generate_cinematic_image(presenter_prompt, presenter_img_path, is_shorts=True, provider=image_provider, fal_key=fal_key, openai_key=openai_key)
            
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
                
    scene_audio = CompositeAudioClip(scene_audio_tracks)
    composite_clip = composite_clip.set_audio(scene_audio)
    composite_clip.fps = 24
    
    # Strip mask to prevent MoviePy mask concatenation bugs that cause black screens in subsequent clips
    composite_clip = composite_clip.without_mask()
    
    return composite_clip


def generate_full_video(topic, is_shorts=True, output_filename="final_output.mp4",
                        tts_provider="edge", tts_voice_id=None, tts_api_key=None,
                        image_provider="pollinations", fal_key=None, openai_key=None,
                        pregenerated_script=None, target_size=None,
                        character_desc="", visual_style="",
                        content_skin="🎬 역사 다큐멘터리 (Historical Documentary)",
                        video_skin="Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)",
                        pexels_key=None, progress_callback=None):
    """Entire video pipeline from scripting to final video composition with chosen technical skin."""
    print(f"[Start] Starting Cinematic AI Video Factory Pipeline with technical skin: {video_skin}...")
    
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
        clip = build_scene_video(
            i, scene, is_shorts=is_shorts,
            tts_provider=tts_provider, tts_voice_id=tts_voice_id, tts_api_key=tts_api_key,
            image_provider=image_provider, fal_key=fal_key, openai_key=openai_key,
            target_size=target_size, video_skin=video_skin, pexels_key=pexels_key,
            topic=topic
        )
        scene_clips.append(clip)
        
        # Track scene narration timings for BGM ducking
        narr_duration = clip.audio.clips[0].duration
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
            
            # Loop/fit BGM to total duration
            if bgm_clip.duration < final_clip.duration:
                bgm_clip = bgm_clip.loop(duration=final_clip.duration)
            else:
                bgm_clip = bgm_clip.subclip(0, final_clip.duration)
                
            # Create the dynamic volume filter
            def volume_filter(t):
                if isinstance(t, np.ndarray):
                    v = np.ones_like(t) * 0.25  # Unducked volume (25%)
                    for start, narr_end, end in scenes_timeline:
                        active_mask = (t >= start) & (t <= narr_end)
                        v[active_mask] = 0.08  # Ducked volume (8%)
                    return v[:, np.newaxis]
                else:
                    for start, narr_end, end in scenes_timeline:
                        if start <= t <= narr_end:
                            return 0.08
                    return 0.25
                    
            # Apply volume filter over time
            ducked_bgm = bgm_clip.fl(lambda gf, t: gf(t) * volume_filter(t))
            
            # Mix with narration and SFX
            mixed_audio = CompositeAudioClip([final_clip.audio, ducked_bgm])
            final_clip = final_clip.set_audio(mixed_audio)
        except Exception as e:
            print(f"[BGM Warning] Failed to mix background music: {e}")
            
    # 5. Render final MP4 output
    if progress_callback:
        progress_callback("RENDER")
    print(f"[Render] Rendering final output video: {output_filename}...")
    # Use unique temp audio file path in TEMP_DIR and disable MoviePy automatic deletion to prevent Windows file lock crashes
    temp_audio_path = os.path.join(TEMP_DIR, f"temp-audio-{int(time.time())}.m4a")
    final_clip.write_videofile(
        output_filename,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=temp_audio_path,
        remove_temp=False
    )
    
    # Close clips to release files on Windows
    try:
        final_clip.close()
    except Exception:
        pass
        
    # 6. Cleanup temporary assets
    print("[Cleanup] Cleaning up temporary assets...")
    for file in os.listdir(TEMP_DIR):
        try:
            os.remove(os.path.join(TEMP_DIR, file))
        except Exception:
            pass
            
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
