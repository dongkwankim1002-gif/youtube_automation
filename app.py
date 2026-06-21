import os
import sys
import streamlit as st
import threading
from dotenv import load_dotenv

# Monkey patch for PIL.Image.ANTIALIAS (needed for MoviePy 1.x / PIL 10.x+ compatibility)
from PIL import Image
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Monkey patch for Windows console encoding (cp949) issues with emojis
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(errors='replace')
    except Exception:
        pass

# Set page config to dark theme with responsive width
st.set_page_config(
    page_title="High-End Cinematic AI Video Factory",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling for UI
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff4b4b, #ff7676);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        color: #a0a0a0;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .status-card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #1e1e1e;
        border: 1px solid #333;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Force load environment variables
load_dotenv()

# Sidebar: Configuration
st.sidebar.markdown("## ⚙️ 설정 & API Keys")

# Check if .env file exists and API keys are set
gemini_key = os.getenv("GEMINI_API_KEY", "")
elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
fal_key = os.getenv("FAL_API_KEY", "") or os.getenv("FAL_KEY", "")
openai_key = os.getenv("OPENAI_API_KEY", "")
pexels_key = os.getenv("PEXELS_API_KEY", "")

# Core API Keys
api_gemini = st.sidebar.text_input("Gemini API Key", value=gemini_key, type="password")
if api_gemini:
    os.environ["GEMINI_API_KEY"] = api_gemini

has_valid_gemini = api_gemini and not api_gemini.startswith("AQ.invalid") and api_gemini != "your_gemini_api_key_here"

if has_valid_gemini:
    st.sidebar.success("✅ Gemini 2.5 Pro 연결 준비 완료")
else:
    st.sidebar.warning("⚠️ 작동 가능한 Gemini API Key가 필요합니다")

st.sidebar.markdown("---")

# 1. TTS Provider Configuration
st.sidebar.markdown("### 🎙️ 성우 나레이션 (TTS)")
tts_provider_display = st.sidebar.selectbox(
    "TTS 엔진 선택", 
    ["ElevenLabs (시네마틱 성우)", "Edge-TTS (무료 나레이션)"]
)
tts_provider = "elevenlabs" if "ElevenLabs" in tts_provider_display else "edge"

api_eleven = ""
tts_voice_id = ""

if tts_provider == "elevenlabs":
    api_eleven = st.sidebar.text_input("ElevenLabs API Key", value=elevenlabs_key, type="password")
    if api_eleven:
        os.environ["ELEVENLABS_API_KEY"] = api_eleven
        
    voice_selection_eleven = st.sidebar.selectbox(
        "성우 보이스 선택", 
        ["Adam (남성 - 중후함/신뢰)", "Rachel (여성 - 차분함/나레이션)", "Antoni (남성 - 깊음/예고편)", "Bella (여성 - 밝음/낭독)", "커스텀 보이스 ID"]
    )
    if voice_selection_eleven == "커스텀 보이스 ID":
        tts_voice_id = st.sidebar.text_input("커스텀 보이스 ID 입력", value="pNInz6obpgq5mWzIA5FD")
    else:
        voice_map = {
            "Adam (남성 - 중후함/신뢰)": "pNInz6obpgq5mWzIA5FD",
            "Rachel (여성 - 차분함/나레이션)": "21m00Tcm4TlvDq8ikWAM",
            "Antoni (남성 - 깊음/예고편)": "ErXwobaYiN019PkySvjV",
            "Bella (여성 - 밝음/낭독)": "EXAVITQu4vr4xnSDxMaL"
        }
        tts_voice_id = voice_map[voice_selection_eleven]
else:
    voice_selection_edge = st.sidebar.selectbox("나레이터 선택 (Edge-TTS)", ["남성 (InJoon)", "여성 (SunHi)"])
    tts_voice_id = "ko-KR-InJoonNeural" if "남성" in voice_selection_edge else "ko-KR-SunHiNeural"

st.sidebar.markdown("---")

# 2. Image Provider Configuration
st.sidebar.markdown("### 🎨 비주얼 이미지 생성")
img_provider_display = st.sidebar.selectbox(
    "이미지 생성 모델",
    ["Flux.1 Dev (fal.ai/초고해상도 역사화)", "DALL-E 3 (OpenAI/고화질 삽화)", "Pollinations.ai (무료/빠름)"]
)

image_provider = "pollinations"
fal_api_key = ""
openai_api_key = ""

if "Flux.1" in img_provider_display:
    image_provider = "fal-ai"
    fal_api_key = st.sidebar.text_input("Fal.ai API Key", value=fal_key, type="password")
    if fal_api_key:
        os.environ["FAL_API_KEY"] = fal_api_key
        os.environ["FAL_KEY"] = fal_api_key
elif "DALL-E 3" in img_provider_display:
    image_provider = "dall-e-3"
    openai_api_key = st.sidebar.text_input("OpenAI API Key", value=openai_key, type="password")
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key

st.sidebar.markdown("---")

# 3. Video Format & Upload configuration
st.sidebar.markdown("### 🎥 동영상 포맷 & 업로드")
format_option = st.sidebar.selectbox("비디오 포맷", ["쇼츠 (9:16 세로형)", "일반 영상 (16:9 가로형)"])
privacy_option = st.sidebar.selectbox("유튜브 업로드 보안 설정", ["비공개 (Private)", "공개 (Public)", "일부공개 (Unlisted)"])

is_shorts = (format_option == "쇼츠 (9:16 세로형)")
privacy_status = "private" if "비공개" in privacy_option else ("public" if "공개" in privacy_option else "unlisted")

# Main Interface UI
st.markdown("<h1 class='main-title'>🎬 High-End Cinematic AI Video Factory</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>최고 품질의 성우 나레이션, 초고화질 AI 이미지, 역동적 카메라 연출이 결합된 시네마틱 동영상 자동화 생산기</p>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1.2])

with col1:
    st.markdown("### 1. 주제 입력")
    topic = st.text_input("만들고 싶은 시네마틱 콘텐츠의 주제를 입력하세요:", placeholder="예시: 나폴레옹의 워털루 전투 패배 원인 3가지")
    
    generate_btn = st.button("🚀 시네마틱 비디오 자동 제작 시작!", use_container_width=True)

# State Management for outputs
if "final_video_path" not in st.session_state:
    st.session_state.final_video_path = None
if "script_data" not in st.session_state:
    st.session_state.script_data = None
if "thumbnail_path" not in st.session_state:
    st.session_state.thumbnail_path = None

if generate_btn:
    if not topic:
        st.error("주제를 입력해주세요!")
    elif not os.environ.get("GEMINI_API_KEY"):
        st.error("Gemini API Key를 사이드바나 .env 파일에 입력해주세요!")
    else:
        status_box = st.empty()
        
        with st.status("🎬 시네마틱 비디오 제작 공장 가동 중...", expanded=True) as status:
            try:
                # Import core generator inside action to prevent import conflicts
                import core_generator
                
                # 1단계: 대본 작성
                status.write("📝 1단계: Gemini 2.5 Pro를 활용해 영화 시나리오 기획 및 대본 작성 중...")
                script_data = core_generator.generate_script_from_gemini(topic, is_shorts)
                st.session_state.script_data = script_data
                
                # 2단계: 비디오 합성 시작
                status.write("⚙️ 2단계: 성우 나레이션 및 AI 이미지 생성, 효과음 믹싱 중...")
                output_filename = "final_output.mp4"
                
                # Run full video pipeline
                status.write("💾 3단계: MoviePy 비디오 렌더링 시작 (Ken Burns 카메라 무빙 및 BGM Ducking 적용)...")
                
                import shutil
                # We dynamically build the video using core_generator with our settings
                video_path, script_data = core_generator.generate_full_video(
                    topic, 
                    is_shorts=is_shorts, 
                    output_filename=output_filename,
                    tts_provider=tts_provider,
                    tts_voice_id=tts_voice_id,
                    tts_api_key=api_eleven if api_eleven else elevenlabs_key,
                    image_provider=image_provider,
                    fal_key=fal_api_key if fal_api_key else fal_key,
                    openai_key=openai_api_key if openai_api_key else openai_key,
                    pregenerated_script=script_data
                )
                
                # Copy final output to keep a stable file name
                stable_video_path = "output_render.mp4"
                shutil.copy(video_path, stable_video_path)
                st.session_state.final_video_path = stable_video_path
                
                # 4단계: 썸네일 생성
                status.write("🖼️ 4단계: Pillow를 사용하여 텍스트 외곽선이 강조된 맞춤 썸네일 합성 중...")
                thumbnail_path = "thumbnail_output.png"
                
                # Generate custom background for thumbnail
                from PIL import Image, ImageDraw, ImageFont
                core_generator.generate_cinematic_image(
                    f"A dramatic and historical scene representing {topic}, digital art, masterpiece, realistic, cinematic lighting",
                    "temp_thumb_bg.jpg",
                    is_shorts=False,  # Thumbnails are 16:9
                    provider=image_provider,
                    fal_key=fal_api_key if fal_api_key else fal_key,
                    openai_key=openai_api_key if openai_api_key else openai_key
                )
                
                # Draw stylized text on background
                thumb_bg = Image.open("temp_thumb_bg.jpg")
                thumb_bg = thumb_bg.resize((1280, 720)) # Standard YouTube thumbnail size
                draw = ImageDraw.Draw(thumb_bg)
                
                # Load Korean Bold Font
                font = core_generator.get_system_font(font_size=80)
                
                # Clean up title for overlay
                clean_title = script_data.get("title", topic)
                lines = core_generator.wrap_text(clean_title, font, 1100, draw)
                
                # Position lines vertically in the center/upper area
                current_y = 180
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font) if hasattr(draw, "textbbox") else draw.textsize(line, font=font)
                    line_w = bbox[2] - bbox[0] if hasattr(draw, "textbbox") else bbox[0]
                    line_h = bbox[3] - bbox[1] if hasattr(draw, "textbbox") else bbox[1]
                    
                    x = (1280 - line_w) // 2
                    
                    # High quality outline shadow
                    stroke_w = 6
                    for dx in range(-stroke_w, stroke_w+1):
                        for dy in range(-stroke_w, stroke_w+1):
                            draw.text((x+dx, current_y+dy), line, font=font, fill=(0, 0, 0, 255))
                            
                    # Draw yellow/white premium text
                    draw.text((x, current_y), line, font=font, fill=(255, 235, 59, 255))
                    current_y += line_h + 20
                    
                thumb_bg.save(thumbnail_path)
                st.session_state.thumbnail_path = thumbnail_path
                
                # Clean up thumbnail temp bg
                try:
                    os.remove("temp_thumb_bg.jpg")
                except Exception:
                    pass
                
                status.update(label="🎉 영상 및 썸네일 제작 완료!", state="complete", expanded=False)
                st.success("시네마틱 비디오 제작 공정이 성공적으로 마무리되었습니다!")
                
            except Exception as e:
                status.update(label="❌ 영상 제작 중 오류 발생", state="error")
                st.error(f"오류 상세: {e}")

# Left column outputs display
if st.session_state.final_video_path:
    with col1:
        st.markdown("### 🎬 완성된 영상 미리보기")
        st.video(st.session_state.final_video_path)
        
        # Display script details
        st.markdown("### 📝 기획서 & 대본 상세")
        if st.session_state.script_data:
            with st.expander("영상 메타데이터 및 대본 보기", expanded=True):
                st.write(f"**제목**: {st.session_state.script_data.get('title')}")
                st.write(f"**설명**: {st.session_state.script_data.get('description')}")
                st.write(f"**태그**: {', '.join(st.session_state.script_data.get('tags', []))}")
                st.write(f"**배경음악 분위기**: {st.session_state.script_data.get('overall_bgm_mood')}")
                st.write("---")
                for i, scene in enumerate(st.session_state.script_data.get("scenes", [])):
                    st.markdown(f"**씬 {i+1} 나레이션:**")
                    st.info(scene.get("narration"))
                    st.markdown(f"- **카메라 연출:** {scene.get('camera_movement', {}).get('type')} ({scene.get('camera_movement', {}).get('speed')})")
                    st.markdown(f"- **효과음(SFX):** {scene.get('sfx_trigger')} ({scene.get('sfx_timing')})")

# Right column settings & actions
with col2:
    if st.session_state.thumbnail_path:
        st.markdown("### 🖼️ 패키징된 썸네일")
        st.image(st.session_state.thumbnail_path, use_column_width=True)
        
    if st.session_state.final_video_path and st.session_state.thumbnail_path:
        st.markdown("### 📢 YouTube 채널로 전송")
        st.info("유튜브 자동 업로드를 위해서는 `client_secrets.json` 파일이 루트 폴더에 준비되어야 합니다.")
        
        # Checking client secrets file
        secrets_exist = os.path.exists("client_secrets.json")
        if not secrets_exist:
            st.warning("⚠️ `client_secrets.json` 파일이 없습니다. OAuth 인증 설정을 확인하세요.")
            
        upload_btn = st.button("📢 유튜브에 비디오 즉시 업로드", disabled=not secrets_exist, use_container_width=True)
        
        if upload_btn:
            with st.spinner("📡 유튜브 API 연동 및 업로드 처리 중... (인증 브라우저를 확인하세요)"):
                try:
                    import youtube_uploader
                    
                    # 1. Upload Video
                    vid_id = youtube_uploader.upload_video(
                        video_path=st.session_state.final_video_path,
                        title=st.session_state.script_data.get("title", topic),
                        description=st.session_state.script_data.get("description", ""),
                        tags=st.session_state.script_data.get("tags", []),
                        category_id="22",  # Default category
                        privacy_status=privacy_status
                    )
                    
                    # 2. Upload Thumbnail
                    youtube_uploader.upload_thumbnail(vid_id, st.session_state.thumbnail_path)
                    
                    st.success(f"🎉 유튜브 예약/업로드에 성공했습니다! 비디오 ID: {vid_id}")
                    st.markdown(f"🔗 [유튜브 영상 링크](https://youtu.be/{vid_id})")
                except Exception as e:
                    st.error(f"유튜브 업로드 실패: {e}")
