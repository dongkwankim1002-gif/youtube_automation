import os
import sys
import shutil
import time
import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Monkey patch for PIL.Image.ANTIALIAS (needed for MoviePy 1.x / PIL 10.x+ compatibility)
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

# Set page config
st.set_page_config(
    page_title="High-End Cinematic AI Video Factory",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff4b4b, #ff7676);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #a0a0a0;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    .dashboard-card {
        padding: 1.5rem;
        border-radius: 12px;
        background-color: #1a1a1a;
        border: 1px solid #333;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .dashboard-card:hover {
        border-color: #ff4b4b;
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.15);
    }
    .status-card {
        padding: 1.2rem;
        border-radius: 10px;
        background-color: #1a1a1a;
        border: 1px solid #333;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Force load environment variables
load_dotenv()

# Force reload core_generator to bypass Streamlit Community Cloud module caching
import importlib
import core_generator
importlib.reload(core_generator)


def cleanup_old_files(max_age_seconds=600):
    """Scan root directory and clean up dynamic output render/thumbnail files older than 10 minutes."""
    import time
    current_time = time.time()
    for f in os.listdir("."):
        if os.path.isfile(f):
            is_render = (
                f.startswith("final_output_") or 
                f.startswith("output_render_") or 
                f.startswith("thumbnail_output_") or 
                f.startswith("v2_output_") or 
                f.startswith("v1_output_")
            )
            if is_render:
                try:
                    file_age = current_time - os.path.getmtime(f)
                    if file_age > max_age_seconds:
                        os.remove(f)
                except Exception:
                    pass

# Load environment keys quietly for fallback
gemini_key = os.getenv("GEMINI_API_KEY", "")
elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
fal_key = os.getenv("FAL_API_KEY", "") or os.getenv("FAL_KEY", "")
openai_key = os.getenv("OPENAI_API_KEY", "")
pexels_key = os.getenv("PEXELS_API_KEY", "")

# --- GLOBAL SESSION STATE INITIALIZATION ---
if "step" not in st.session_state:
    st.session_state.step = "input"
if "content_genre" not in st.session_state:
    st.session_state.content_genre = "🎬 역사 다큐멘터리 (Historical Documentary)"
if "video_skin" not in st.session_state:
    st.session_state.video_skin = "Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)"
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "character_desc" not in st.session_state:
    st.session_state.character_desc = ""
if "visual_style" not in st.session_state:
    st.session_state.visual_style = "시네마틱 실사 영화 스틸컷 (Dramatic Cinematic Shot)"
if "custom_style" not in st.session_state:
    st.session_state.custom_style = ""
if "script_data" not in st.session_state:
    st.session_state.script_data = None
if "final_video_path" not in st.session_state:
    st.session_state.final_video_path = None
if "thumbnail_path" not in st.session_state:
    st.session_state.thumbnail_path = None

# API Keys configured in UI
if "api_gemini" not in st.session_state:
    st.session_state.api_gemini = ""
if "api_eleven" not in st.session_state:
    st.session_state.api_eleven = ""
if "api_fal" not in st.session_state:
    st.session_state.api_fal = ""
if "api_openai" not in st.session_state:
    st.session_state.api_openai = ""
if "api_pexels" not in st.session_state:
    st.session_state.api_pexels = ""

# Render options
if "is_shorts" not in st.session_state:
    st.session_state.is_shorts = True
if "privacy_status" not in st.session_state:
    st.session_state.privacy_status = "private"
if "target_size" not in st.session_state:
    st.session_state.target_size = (540, 960)
if "format_option" not in st.session_state:
    st.session_state.format_option = "쇼츠 (9:16 세로형)"
if "quality_option" not in st.session_state:
    st.session_state.quality_option = "540p (Cloud 최적화 - 서버용)"
if "privacy_option" not in st.session_state:
    st.session_state.privacy_option = "비공개 (Private)"

# Provider configurations
if "tts_provider" not in st.session_state:
    st.session_state.tts_provider = "edge"
if "tts_voice_id" not in st.session_state:
    st.session_state.tts_voice_id = "ko-KR-InJoonNeural"
if "image_provider" not in st.session_state:
    st.session_state.image_provider = "pollinations"

# v3.0.0 specific states
if "active_menu" not in st.session_state:
    st.session_state.active_menu = "Home"
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "Standard User"

# v4.0.0 Specific state parameters
if "v4_easing" not in st.session_state:
    st.session_state.v4_easing = "Cubic Ease-in-out"
if "v4_film_grain" not in st.session_state:
    st.session_state.v4_film_grain = 15
if "v4_vignette" not in st.session_state:
    st.session_state.v4_vignette = True
if "v4_3d_panning" not in st.session_state:
    st.session_state.v4_3d_panning = True
if "v4_compressor" not in st.session_state:
    st.session_state.v4_compressor = True
if "v4_voice_stability" not in st.session_state:
    st.session_state.v4_voice_stability = 0.75
if "v4_voice_clarity" not in st.session_state:
    st.session_state.v4_voice_clarity = 0.75
if "v4_voice_style" not in st.session_state:
    st.session_state.v4_voice_style = 0.00

# v5.0.0 Specific state parameters (Google Native)
if "v5_sheet_id" not in st.session_state:
    st.session_state.v5_sheet_id = ""
if "v5_gtts_voice" not in st.session_state:
    st.session_state.v5_gtts_voice = "ko-KR-Neural2-A"
if "v5_imagen_aspect" not in st.session_state:
    st.session_state.v5_imagen_aspect = "9:16"
if "v5_gcs_bucket" not in st.session_state:
    st.session_state.v5_gcs_bucket = "my-video-factory-bucket"
if "v5_visual_model" not in st.session_state:
    st.session_state.v5_visual_model = "Google Imagen 3 (고품질 이미지 + 모션 연출)"
if "gemini_exhausted" not in st.session_state:
    st.session_state.gemini_exhausted = False
if "v5_active_styles" not in st.session_state:
    st.session_state.v5_active_styles = ["시네마틱 실사 (Cinematic Realism)"]
if "v5_style_strengths" not in st.session_state:
    st.session_state.v5_style_strengths = {
        "시네마틱 실사 (Cinematic Realism)": 0.8,
        "코믹/웹툰 (Comic / Webtoon)": 0.7,
        "뉴스/다큐 보도 (News & Documentary)": 0.7,
        "호러/미스터리 (Horror & Mystery)": 0.7,
        "큐티/러블리 (Cute & Lovely)": 0.7,
        "애니메이션 (Anime / Animation)": 0.7,
        "역사화 유화 (Historical Oil Painting)": 0.7,
        "수채화 판타지 (Watercolor Fantasy)": 0.7
    }
if "v5_custom_style_desc" not in st.session_state:
    st.session_state.v5_custom_style_desc = ""


def compile_v5_style():
    style_parts = []
    for style in st.session_state.v5_active_styles:
        strength = st.session_state.v5_style_strengths.get(style, 0.7)
        desc = ""
        if style == "시네마틱 실사 (Cinematic Realism)":
            desc = f"cinematic realism movie style (strength: {strength:.1f})"
        elif style == "코믹/웹툰 (Comic / Webtoon)":
            desc = f"vibrant comic webtoon art style (strength: {strength:.1f})"
        elif style == "뉴스/다큐 보도 (News & Documentary)":
            desc = f"realistic news photojournalism broadcast style (strength: {strength:.1f})"
        elif style == "호러/미스터리 (Horror & Mystery)":
            desc = f"dark gothic horror mystery style (strength: {strength:.1f})"
        elif style == "큐티/러블리 (Cute & Lovely)":
            desc = f"cute lovely pastel graphic style (strength: {strength:.1f})"
        elif style == "애니메이션 (Anime / Animation)":
            desc = f"modern digital 2D anime animation style (strength: {strength:.1f})"
        elif style == "역사화 유화 (Historical Oil Painting)":
            desc = f"fine art oil painting canvas texture (strength: {strength:.1f})"
        elif style == "수채화 판타지 (Watercolor Fantasy)":
            desc = f"soft watercolor dreamlike fantasy illustration (strength: {strength:.1f})"
        if desc:
            style_parts.append(desc)
            
    if st.session_state.v5_custom_style_desc.strip():
        style_parts.append(st.session_state.v5_custom_style_desc.strip())
        
    compiled = ", ".join(style_parts)
    if not compiled:
        compiled = "cinematic photo style"
    st.session_state.visual_style = compiled



# --- 🎬 렌더링 실시간 시각화 진행 표시기 (Real-time Progress Indicator) ---
def get_progress_callback(placeholder):
    def progress_callback(step, index=None, total=None):
        steps = {
            "PREPARE": ("active", "waiting", "waiting", "waiting", "waiting", 10, "⚙️ 오디오 애셋 라이브러리 및 폰트 준비 중..."),
            "SCENE": ("complete", "active", "waiting", "waiting", "waiting", 15, "🎬 씬 개별 비디오 제작 중..."),
            "MERGE": ("complete", "complete", "active", "waiting", "waiting", 80, "🔗 생성된 씬 비디오 클립 연결 및 해상도 조정 중..."),
            "BGM": ("complete", "complete", "complete", "active", "waiting", 88, "🎵 BGM 결합 및 나레이션 오토 덕킹(Ducking) 중..."),
            "RENDER": ("complete", "complete", "complete", "complete", "active", 95, "📼 최종 H.264 MP4 비디오 렌더링 파일 출력 중..."),
            "DONE": ("complete", "complete", "complete", "complete", "complete", 100, "🎉 영상 제작 완료!")
        }
        
        status_info = steps.get(step, ("waiting", "waiting", "waiting", "waiting", "waiting", 0, "준비 중..."))
        s1, s2, s3, s4, s5, progress_val, desc = status_info
        
        if step == "SCENE" and index is not None and total is not None:
            progress_val = int(15 + (index / total) * 60)
            desc = f"🎬 {total}개 씬 중 {index+1}번째 씬 비디오 제작 중 ({index+1}/{total})..."
            
        def get_badge(status):
            if status == "active":
                return "<span style='color: #ff4b4b; font-weight: bold; animation: blink 1.5s infinite;'>⚡ 진행 중</span>"
            elif status == "complete":
                return "<span style='color: #00e676; font-weight: bold;'>✅ 완료</span>"
            else:
                return "<span style='color: #888;'>⏳ 대기 중</span>"
                
        def get_class(status):
            if status == "active":
                return "render-step active"
            elif status == "complete":
                return "render-step complete"
            else:
                return "render-step"

        html_content = f"""
        <style>
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            @keyframes blink {{
                0% {{ opacity: 0.4; }}
                50% {{ opacity: 1; }}
                100% {{ opacity: 0.4; }}
            }}
            .render-container {{
                background: linear-gradient(135deg, #1e1e2e, #11111b);
                border: 2px solid #ff4b4b;
                border-radius: 15px;
                padding: 2rem;
                box-shadow: 0 8px 32px rgba(255, 75, 75, 0.15);
                margin-bottom: 2rem;
            }}
            .render-header {{
                display: flex;
                align-items: center;
                gap: 1.5rem;
                margin-bottom: 1.5rem;
                border-bottom: 1px solid #333;
                padding-bottom: 1.2rem;
            }}
            .render-spinner {{
                border: 5px solid rgba(255, 75, 75, 0.1);
                width: 55px;
                height: 55px;
                border-radius: 50%;
                border-left-color: #ff4b4b;
                animation: spin 1s linear infinite;
            }}
            .render-step {{
                padding: 0.9rem 1.2rem;
                border-radius: 10px;
                background: #181824;
                margin-bottom: 0.8rem;
                border-left: 5px solid #333;
                display: flex;
                justify-content: space-between;
                align-items: center;
                transition: all 0.3s ease;
            }}
            .render-step.active {{
                border-left-color: #ff4b4b;
                background: #2b1f24;
                box-shadow: 0 0 15px rgba(255, 75, 75, 0.15);
            }}
            .render-step.complete {{
                border-left-color: #00e676;
                background: #1b261e;
            }}
            .step-title {{
                font-weight: 600;
                font-size: 1.05rem;
            }}
        </style>
        <div class='render-container'>
            <div class='render-header'>
                {f"<div class='render-spinner'></div>" if step != "DONE" else "<span style='font-size:2.2rem;'>🎉</span>"}
                <div>
                    <h3 style='margin:0; color:#ff4b4b; font-size:1.6rem; font-weight:800;'>🎬 AI 비디오 제작 파이프라인 가동 중</h3>
                    <p style='margin:0.2rem 0 0 0; color:#a0a0c0; font-size:0.98rem;'>{desc}</p>
                </div>
            </div>
            
            <div style='margin-bottom: 1.5rem;'>
                <div style='display:flex; justify-content:space-between; color:#a0a0c0; font-size:0.9rem; margin-bottom:0.4rem;'>
                    <span>제작 진행률</span>
                    <strong>{progress_val}%</strong>
                </div>
                <div style='background-color:#2a2a3a; height:12px; border-radius:6px; overflow:hidden;'>
                    <div style='background-color:#ff4b4b; width:{progress_val}%; height:100%; border-radius:6px; transition:width 0.5s ease-in-out;'></div>
                </div>
            </div>
            
            <div class='{get_class(s1)}'>
                <span class='step-title'>🎙️ 1단계: 기본 오디오 애셋 로딩 및 준비</span>
                {get_badge(s1)}
            </div>
            <div class='{get_class(s2)}'>
                <span class='step-title'>🎨 2단계: 씬별 성우 나레이션 & 이미지 비주얼 생성</span>
                {get_badge(s2)}
            </div>
            <div class='{get_class(s3)}'>
                <span class='step-title'>🔗 3단계: 비주얼 클립 해상도 매칭 및 영상 병합</span>
                {get_badge(s3)}
            </div>
            <div class='{get_class(s4)}'>
                <span class='step-title'>🎵 4단계: 시네마틱 BGM 결합 및 볼륨 오토 덕킹</span>
                {get_badge(s4)}
            </div>
            <div class='{get_class(s5)}'>
                <span class='step-title'>📼 5단계: 최종 MP4 비디오 렌더링 파일 인코딩 및 출력</span>
                {get_badge(s5)}
            </div>
        </div>
        """
        flat_html = "\n".join([line.strip() for line in html_content.split("\n")])
        placeholder.markdown(flat_html, unsafe_allow_html=True)
        
    return progress_callback


def render_production_flow(version):
    """
    Renders the Edit, Render, and Result steps for a unified production pipeline.
    version is one of: "v4.0.0", "v5.0.0"
    """
    if st.session_state.step == "edit":
        st.markdown(f"### 📝 2단계: 대본 및 연출 디테일 수정 ({version})")
        
        if st.session_state.script_data is None:
            st.warning("생성된 대본이 없습니다. 처음 단계로 돌아갑니다.")
            st.session_state.step = "input"
            st.rerun()
            
        script_data = st.session_state.script_data
        
        st.markdown("#### ⚙️ 전체 설정")
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            script_data["title"] = st.text_input("유튜브 동영상 제목", value=script_data.get("title", ""), key=f"v_title_{version}")
            script_data["description"] = st.text_area("동영상 설명 (Description)", value=script_data.get("description", ""), key=f"v_desc_{version}")
        with col_t2:
            tags_str = st.text_input("태그 (쉼표로 구분)", value=", ".join(script_data.get("tags", [])), key=f"v_tags_{version}")
            script_data["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
            
            bgm_moods = ["epic_orchestral", "dark_mystery", "sad_piano", "intense_suspense"]
            bgm_mood = script_data.get("overall_bgm_mood", "epic_orchestral")
            if bgm_mood not in bgm_moods:
                bgm_moods.append(bgm_mood)
            script_data["overall_bgm_mood"] = st.selectbox("배경음악 무드", bgm_moods, index=bgm_moods.index(bgm_mood), key=f"v_bgm_{version}")

        st.markdown("---")
        st.markdown("#### 🎬 씬(Scene)별 상세 편집")
        
        scenes = script_data.get("scenes", [])
        for i, scene in enumerate(scenes):
            with st.container(border=True):
                st.markdown(f"##### 🎥 Scene {i+1}")
                col_ed1, col_ed2 = st.columns([2, 1.2])
                
                with col_ed1:
                    scene["narration"] = st.text_area(f"씬 {i+1} 나레이션 대사 (한국어)", value=scene.get("narration", ""), key=f"scene_narr_{version}_{i}")
                    scene["visual_prompt"] = st.text_area(f"씬 {i+1} 이미지 생성 프롬프트 (영어)", value=scene.get("visual_prompt", ""), key=f"scene_prompt_{version}_{i}")
                    
                with col_ed2:
                    camera_info = scene.get("camera_movement", {})
                    camera_types = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]
                    cam_type = camera_info.get("type", "zoom_in")
                    if cam_type not in camera_types:
                        camera_types.append(cam_type)
                    
                    selected_cam_type = st.selectbox(f"카메라 연출", camera_types, index=camera_types.index(cam_type), key=f"scene_cam_type_{version}_{i}")
                    
                    camera_speeds = ["slow", "medium"]
                    cam_speed = camera_info.get("speed", "slow")
                    if cam_speed not in camera_speeds:
                        camera_speeds.append(cam_speed)
                    selected_cam_speed = st.selectbox(f"카메라 속도", camera_speeds, index=camera_speeds.index(cam_speed), key=f"scene_cam_speed_{version}_{i}")
                    scene["camera_movement"] = {"type": selected_cam_type, "speed": selected_cam_speed}
                    
                    sfx_list = ["none", "sword_clash", "thunder", "wind_howl", "horse_gallop", "fire_crackle"]
                    sfx_trigger = scene.get("sfx_trigger", "none")
                    if sfx_trigger not in sfx_list:
                        sfx_list.append(sfx_trigger)
                        
                    selected_sfx = st.selectbox(f"효과음(SFX)", sfx_list, index=sfx_list.index(sfx_trigger), key=f"scene_sfx_{version}_{i}")
                    
                    sfx_timings = ["start", "middle", "end"]
                    sfx_timing = scene.get("sfx_timing", "start")
                    if sfx_timing not in sfx_timings:
                        sfx_timings.append(sfx_timing)
                    selected_sfx_timing = st.selectbox(f"효과음 타이밍", sfx_timings, index=sfx_timings.index(sfx_timing), key=f"scene_sfx_timing_{version}_{i}")
                    scene["sfx_trigger"] = selected_sfx
                    scene["sfx_timing"] = selected_sfx_timing
                    
                    if st.button(f"🗑️ Scene {i+1} 삭제", key=f"del_scene_{version}_{i}"):
                        scenes.pop(i)
                        st.session_state.script_data["scenes"] = scenes
                        st.rerun()
                        
        col_act1, col_act2, col_act3 = st.columns([1, 1, 2])
        with col_act1:
            if st.button("➕ 씬 추가", key=f"add_scene_btn_{version}"):
                new_scene = {
                    "narration": "새로운 장면 나레이션을 입력하세요.",
                    "visual_prompt": "A cinematic shot of a scene, detailed, photorealistic",
                    "camera_movement": {"type": "zoom_in", "speed": "slow"},
                    "sfx_trigger": "none",
                    "sfx_timing": "start"
                }
                scenes.append(new_scene)
                st.session_state.script_data["scenes"] = scenes
                st.rerun()
        with col_act2:
            if st.button("↩️ 대본 초기화 및 처음으로", key=f"reset_scene_btn_{version}"):
                st.session_state.script_data = None
                st.session_state.step = "input"
                st.rerun()
        with col_act3:
            if st.button("🚀 3단계: 최종 비디오 렌더링 시작!", use_container_width=True, type="primary", key=f"start_render_btn_{version}"):
                st.session_state.step = "render"
                st.rerun()

    elif st.session_state.step == "render":
        st.markdown(f"### ⚙️ 3단계: 비디오 렌더링 및 파일 합성 ({version})")
        if st.session_state.script_data is None:
            st.warning("렌더링할 대본 데이터가 없습니다.")
            st.session_state.step = "input"
            st.rerun()
            
        progress_area = st.empty()
        cb = get_progress_callback(progress_area)
        
        try:
            import core_generator
            
            active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
            active_eleven_key = st.session_state.api_eleven if st.session_state.api_eleven else elevenlabs_key
            active_fal_key = st.session_state.api_fal if st.session_state.api_fal else fal_key
            active_openai_key = st.session_state.api_openai if st.session_state.api_openai else openai_key
            active_pexels_key = st.session_state.api_pexels if st.session_state.api_pexels else pexels_key
            
            os.environ["GEMINI_API_KEY"] = active_gemini_key
            if active_eleven_key:
                os.environ["ELEVENLABS_API_KEY"] = active_eleven_key
            if active_fal_key:
                os.environ["FAL_API_KEY"] = active_fal_key
                os.environ["FAL_KEY"] = active_fal_key
            if active_openai_key:
                os.environ["OPENAI_API_KEY"] = active_openai_key
            if active_pexels_key:
                os.environ["PEXELS_API_KEY"] = active_pexels_key

            # Run background cleanup of old dynamic files (older than 10 mins)
            cleanup_old_files()
            
            import uuid
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex[:8]
            
            # Make dynamic uniquely isolatable names for temp dir and outputs
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_assets_{timestamp}_{unique_id}")
            output_filename = f"final_output_{timestamp}_{unique_id}.mp4"
            
            # version-specific parameters mapping
            v4_easing = "Linear"
            v4_film_grain = 0
            v4_vignette = False
            v4_3d_panning = False
            v4_compressor = False
            v4_stability = 0.75
            v4_clarity = 0.75
            v4_style = 0.0
            
            v5_gcs_bucket = ""
            v5_video_skin = st.session_state.video_skin
            
            # Set up parameters based on version selection
            if version == "v4.0.0":
                v4_easing = st.session_state.v4_easing
                v4_film_grain = st.session_state.v4_film_grain
                v4_vignette = st.session_state.v4_vignette
                v4_3d_panning = st.session_state.v4_3d_panning
                v4_compressor = st.session_state.v4_compressor
                v4_stability = st.session_state.v4_voice_stability
                v4_clarity = st.session_state.v4_voice_clarity
                v4_style = st.session_state.v4_voice_style
                
                tts_provider = st.session_state.tts_provider
                tts_voice_id = st.session_state.tts_voice_id
                image_provider = st.session_state.image_provider
            
            elif version == "v5.0.0":
                # Google Native
                tts_provider = "google"
                voice_raw = st.session_state.v5_gtts_voice
                voice_parts = voice_raw.split(" ")
                tts_voice_id = voice_parts[0] if len(voice_parts) > 0 else "ko-KR-Neural2-A"
                image_provider = "google"
                v5_gcs_bucket = st.session_state.v5_gcs_bucket
                
                # Dynamically set is_shorts and target_size based on selected aspect ratio (optimized for Streamlit Cloud 1GB RAM)
                if "9:16" in st.session_state.v5_imagen_aspect:
                    st.session_state.is_shorts = True
                    st.session_state.target_size = (540, 960)
                elif "16:9" in st.session_state.v5_imagen_aspect:
                    st.session_state.is_shorts = False
                    st.session_state.target_size = (960, 540)
                else: # 1:1
                    st.session_state.is_shorts = False
                    st.session_state.target_size = (640, 640)
                    
                # Dynamically map video_skin based on visual model
                if "Veo" in st.session_state.v5_visual_model:
                    v5_video_skin = "Option 2: AI 비디오 직접 생성 (Google Veo)"
                else:
                    v5_video_skin = "Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)"

            # Prevent Out-Of-Memory (OOM) crashes on Streamlit Cloud 1GB RAM limit by capping resolution
            width, height = st.session_state.target_size
            if width * height > 1280 * 720:
                print(f"[OOM Protection] Capping resolution from {width}x{height} to 720p equivalent to prevent crash.")
                if width > height:
                    st.session_state.target_size = (1280, 720)
                else:
                    st.session_state.target_size = (720, 1280)

            video_path, script_res_data = core_generator.generate_full_video(
                st.session_state.topic, 
                is_shorts=st.session_state.is_shorts, 
                output_filename=output_filename,
                tts_provider=tts_provider,
                tts_voice_id=tts_voice_id,
                tts_api_key=active_eleven_key if tts_provider == "elevenlabs" else active_gemini_key,
                image_provider=image_provider,
                fal_key=active_fal_key,
                openai_key=active_openai_key,
                pregenerated_script=st.session_state.script_data,
                target_size=st.session_state.target_size,
                content_skin=st.session_state.content_genre,
                video_skin=v5_video_skin if version == "v5.0.0" else st.session_state.video_skin,
                pexels_key=active_pexels_key,
                progress_callback=cb,
                temp_dir=temp_dir,
                v4_easing=v4_easing,
                v4_film_grain=v4_film_grain,
                v4_vignette=v4_vignette,
                v4_3d_panning=v4_3d_panning,
                v4_compressor=v4_compressor,
                v4_voice_stability=v4_stability,
                v4_voice_clarity=v4_clarity,
                v4_voice_style=v4_style,
                v5_gcs_bucket=v5_gcs_bucket,
                version=version
            )
            
            st.session_state.script_data = script_res_data
            
            stable_video_path = f"output_render_{timestamp}_{unique_id}.mp4"
            shutil.copy(video_path, stable_video_path)
            st.session_state.final_video_path = stable_video_path
            
            # Clean up the initial raw render filename to keep directory clean
            try:
                os.remove(output_filename)
            except Exception:
                pass
            
            cb("RENDER")  # Update to final render (Thumbnails & Packaging)
            thumbnail_path = f"thumbnail_output_{timestamp}_{unique_id}.png"
            temp_thumb_bg_path = f"temp_thumb_bg_{timestamp}_{unique_id}.jpg"
            
            core_generator.generate_cinematic_image(
                f"A dramatic and historical scene representing {st.session_state.topic}, digital art, masterpiece, realistic, cinematic lighting",
                temp_thumb_bg_path,
                is_shorts=False,
                provider=image_provider,
                fal_key=active_fal_key,
                openai_key=active_openai_key,
                gemini_key=active_gemini_key
            )
            
            thumb_bg = Image.open(temp_thumb_bg_path)
            thumb_bg = thumb_bg.resize((1280, 720))
            draw = ImageDraw.Draw(thumb_bg)
            font = core_generator.get_system_font(font_size=80)
            
            clean_title = st.session_state.script_data.get("title", st.session_state.topic)
            lines = core_generator.wrap_text(clean_title, font, 1100, draw)
            
            current_y = 180
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font) if hasattr(draw, "textbbox") else draw.textsize(line, font=font)
                line_w = bbox[2] - bbox[0] if hasattr(draw, "textbbox") else bbox[0]
                line_h = bbox[3] - bbox[1] if hasattr(draw, "textbbox") else bbox[1]
                x = (1280 - line_w) // 2
                
                stroke_w = 6
                for dx in range(-stroke_w, stroke_w+1):
                    for dy in range(-stroke_w, stroke_w+1):
                        draw.text((x+dx, current_y+dy), line, font=font, fill=(0, 0, 0, 255))
                        
                draw.text((x, current_y), line, font=font, fill=(255, 235, 59, 255))
                current_y += line_h + 20
                
            thumb_bg.save(thumbnail_path)
            st.session_state.thumbnail_path = thumbnail_path
            
            try:
                os.remove(temp_thumb_bg_path)
            except Exception:
                pass
                
            cb("DONE")
            time.sleep(1.5)
            st.session_state.step = "result"
            st.rerun()
        except Exception as e:
            st.error(f"❌ 영상 제작 중 오류 발생: {e}")
            err_msg = str(e)
            if version == "v5.0.0" and ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "credits are depleted" in err_msg):
                st.warning("⚠️ **Gemini API 키 오류 감지**: 구글 AI 스튜디오 선불 크레딧이 부족합니다. 결제 상태를 확인하거나 새 API 키를 등록하세요.")
                new_key = st.text_input("🔑 새로운 Gemini API Key 입력:", type="password", key=f"new_gemini_key_render_{version}")
                if st.button("💾 API Key 업데이트 및 저장", key=f"save_key_render_{version}", use_container_width=True, type="primary"):
                    if new_key.strip():
                        st.session_state.api_gemini = new_key.strip()
                        st.session_state.gemini_exhausted = False
                        st.success("API Key가 업데이트되었습니다! 편집 단계로 돌아가 다시 렌더링해 주세요.")
                        time.sleep(1.2)
                        st.session_state.step = "edit"
                        st.rerun()
                    else:
                        st.warning("유효한 API Key를 입력해 주세요.")
            if st.button("↩️ 편집 단계로 돌아가기", key=f"err_back_btn_{version}"):
                st.session_state.step = "edit"
                st.rerun()

    elif st.session_state.step == "result":
        st.markdown(f"### 🎉 4단계: 비디오 제작 및 업로드 결과 ({version})")
        col_res1, col_res2 = st.columns([2, 1.2])
        
        with col_res1:
            if st.session_state.final_video_path:
                st.markdown("### 🎬 완성된 영상 미리보기")
                st.video(st.session_state.final_video_path)
                
                st.markdown("### 📝 최종 기획서 및 대본")
                with st.expander("영상 메타데이터 및 대본 보기", expanded=True):
                    st.write(f"**제목**: {st.session_state.script_data.get('title')}")
                    st.write(f"**설명**: {st.session_state.script_data.get('description')}")
                    st.write(f"**태그**: {', '.join(st.session_state.script_data.get('tags', []))}")
                    st.write(f"**배경음악 분위기**: {st.session_state.script_data.get('overall_bgm_mood')}")
                    
                    if version == "v5.0.0" and "gcs_url" in st.session_state.script_data:
                        st.write("---")
                        st.markdown(f"🟢 **Google Cloud Storage 업로드 성공!**")
                        st.markdown(f"🔗 [GCS 다운로드 파일 링크]({st.session_state.script_data['gcs_url']})")
                        
                    st.write("---")
                    for i, scene in enumerate(st.session_state.script_data.get("scenes", [])):
                        st.markdown(f"**씬 {i+1} 나레이션:**")
                        st.info(scene.get("narration"))
                        st.markdown(f"- **카메라 연출:** {scene.get('camera_movement', {}).get('type')} ({scene.get('camera_movement', {}).get('speed')})")
                        st.markdown(f"- **효과음(SFX):** {scene.get('sfx_trigger')} ({scene.get('sfx_timing')})")
                        
        with col_res2:
            if st.session_state.thumbnail_path:
                st.markdown("### 🖼️ 패키징된 썸네일")
                st.image(st.session_state.thumbnail_path, use_column_width=True)
                
            st.markdown("### 📢 YouTube 채널로 전송")
            st.info("유튜브 자동 업로드를 위해서는 `client_secrets.json` 파일이 루트 폴더에 준비되어야 합니다.")
            
            secrets_exist = os.path.exists("client_secrets.json")
            if not secrets_exist:
                st.warning("⚠️ `client_secrets.json` 파일이 없습니다. OAuth 인증 설정을 확인하세요.")
                
            upload_btn = st.button("📢 유튜브에 비디오 즉시 업로드", disabled=not secrets_exist, use_container_width=True, key=f"yt_up_btn_{version}")
            
            if upload_btn:
                with st.spinner("📡 유튜브 API 연동 및 업로드 처리 중..."):
                    try:
                        import youtube_uploader
                        vid_id = youtube_uploader.upload_video(
                            video_path=st.session_state.final_video_path,
                            title=st.session_state.script_data.get("title", st.session_state.topic),
                            description=st.session_state.script_data.get("description", ""),
                            tags=st.session_state.script_data.get("tags", []),
                            category_id="22",
                            privacy_status=st.session_state.privacy_status
                        )
                        youtube_uploader.upload_thumbnail(vid_id, st.session_state.thumbnail_path)
                        st.success(f"🎉 유튜브 업로드 성공! 비디오 ID: {vid_id}")
                        st.markdown(f"🔗 [유튜브 영상 링크](https://youtu.be/{vid_id})")
                    except Exception as e:
                        st.error(f"유튜브 업로드 실패: {e}")
                        
            st.markdown("---")
            if st.button("↩️ 처음으로 (새 비디오 만들기)", use_container_width=True, key=f"finish_btn_{version}"):
                st.session_state.script_data = None
                st.session_state.final_video_path = None
                st.session_state.thumbnail_path = None
                st.session_state.step = "input"
                st.rerun()


# --- 📂 VERSION SWITCHER AT THE VERY TOP ---
st.markdown("""
<div style='background: linear-gradient(135deg, #1e1e2e, #11111b); padding: 1.5rem; border-radius: 12px; border: 2px solid #ff4b4b; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(255, 75, 75, 0.15);'>
    <div style='display: flex; align-items: center; gap: 0.8rem;'>
        <span style='font-size: 2rem;'>📂</span>
        <div>
            <h3 style='margin:0; color:#ff4b4b; font-size:1.6rem; font-weight:800;'>개발 이력 모니터링 및 단계별 버전 스위처</h3>
            <p style='margin:0.2rem 0 0 0; color:#a0a0c0; font-size:0.98rem;'>
                초기 프로토타입(v1.0)부터 장르 스킨(v2.0), 보안 SaaS(v3.0), 최고품질 시네마틱 스튜디오(v4.0), 그리고 구글 올인원 에코시스템(v5.0)의 아키텍처 진화 단계를 실시간으로 전환할 수 있습니다.
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

selected_version = st.radio(
    "🔍 활성화할 애플리케이션 버전을 선택하세요 (버전 클릭 시 즉시 화면이 전환됩니다):",
    [
        "v5.0.0 (구글 네이티브 올인원 에코시스템 - 차세대)",
        "v4.0.0 (시네마틱 스튜디오 프로페셔널 - 고품질 단계)",
        "v3.0.0 (보안 & SaaS 통합 대시보드 - 현재 단계)",
        "v2.0.0 (컨텐츠 장르 및 제작 스킨 추가 - 이전 단계)",
        "v1.0.0 (초기 뼈대 및 설정 사이드바 - 최초 단계)"
    ],
    index=0,
    horizontal=True,
    help="선택한 단계의 UI와 기능 규격으로 화면이 즉시 재구성됩니다."
)

st.markdown("---")


# =========================================================================
# ==================== v5.0.0: 구글 네이티브 올인원 에코시스템 ====================
# =========================================================================
if "v5.0.0" in selected_version:
    # Sidebar layout for v5.0.0: Google Cloud branding & API Health checks
    with st.sidebar:
        st.markdown("### ☁️ Google Cloud Portal")
        st.caption("v5.0.0 Google-Native Edition")
        st.markdown("---")
        
        st.markdown("#### 📡 Google Cloud API Health")
        # Visual health checks using green/red badges
        st.markdown("🟢 **Gemini 2.5 Pro** (Active)")
        st.markdown("🟢 **Imagen 3 (Vertex AI)** (Connected)")
        st.markdown("🟢 **Google Cloud TTS (Wavenet)** (Active)")
        st.markdown("🟢 **Google Cloud Storage** (Connected)")
        st.markdown("🟢 **YouTube Data API v3** (Authorized)")
        st.markdown("🟡 **Google Sheets API** (Pending Key)")
        
        st.markdown("---")
        st.caption("Google Cloud Platform Ecosystem | DLP Active")

    # Main body navigation tabs for v5.0.0
    nav_cols = st.columns([1.2, 1.2, 1.2, 1.2, 1.5])
    with nav_cols[0]:
        if st.button("🏠 구글 홈 대시보드", use_container_width=True, type="primary" if st.session_state.active_menu == "Home" else "secondary"):
            st.session_state.active_menu = "Home"
            st.rerun()
    with nav_cols[1]:
        if st.button("🎬 Vertex AI 스튜디오", use_container_width=True, type="primary" if st.session_state.active_menu == "Studio" else "secondary"):
            st.session_state.active_menu = "Studio"
            st.rerun()
    with nav_cols[2]:
        if st.button("📁 GCS 자산보관함", use_container_width=True, type="primary" if st.session_state.active_menu == "Library" else "secondary"):
            st.session_state.active_menu = "Library"
            st.rerun()
    with nav_cols[3]:
        if st.button("👤 구글 마이페이지", use_container_width=True, type="primary" if st.session_state.active_menu == "Profile" else "secondary"):
            st.session_state.active_menu = "Profile"
            st.rerun()
    with nav_cols[4]:
        if st.button("⚙️ GCP 연동 설정 (보안)", use_container_width=True, type="primary" if st.session_state.active_menu == "Settings" else "secondary"):
            st.session_state.active_menu = "Settings"
            st.rerun()

    st.markdown("---")

    # Page 1: Google Home
    if st.session_state.active_menu == "Home":
        st.markdown("### 🏠 구글 네이티브 올인원 에코시스템")
        st.markdown("모든 파이프라인(대본, 성우, 비주얼 생성, 저장, 배포)이 Google Cloud 및 YouTube 환경에서 완결되는 미래형 아키텍처입니다.")
        
        st.markdown("""
        <div style='background: linear-gradient(135deg, #1A73E8, #34A853); padding: 1.5rem; border-radius: 12px; border: 1px solid #ffffff33; margin-bottom: 1.5rem;'>
            <h4 style='margin:0; color:#fff; font-weight:700;'>💡 v5.0.0 구글 네이티브 핵심 개념</h4>
            <p style='margin:0.5rem 0 0 0; color:#e0e0e0; font-size:0.95rem;'>
                로컬이나 타사 API를 거치지 않고, 대본은 <b>Gemini 2.5 Pro</b>, 이미지는 <b>Imagen 3</b>, 나레이션은 <b>Google Cloud TTS</b>, 저장소는 <b>GCS</b>, 배포는 <b>YouTube</b>로 결합하여 하나의 완벽한 구글 솔루션을 구축합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(label="GCS 버킷 상태", value="🟢 연결 완료", delta="my-video-factory-bucket")
        with c2:
            st.metric(label="동기화된 Google Sheet", value="🟢 대기 중", delta="연동 ID 미설정")
        with c3:
            st.metric(label="오늘의 업로드 한도", value="4 / 6 (YouTube)")

    # Page 2: Studio
    elif st.session_state.active_menu == "Studio":
        if st.session_state.step == "input":
            st.markdown("### 🎬 Vertex AI 비디오 팩토리 스튜디오")
            
            col1, col2 = st.columns([2, 1.2])
            with col1:
                if st.session_state.gemini_exhausted:
                    st.error("🚨 **Gemini API 키 크레딧 소진**: 구글 AI 스튜디오 선불 크레딧이 소진되었거나 호출 한도가 초과되었습니다.")
                    new_key = st.text_input("🔑 새로운 Gemini API Key 입력:", type="password", key="new_gemini_key_input_v5")
                    if st.button("💾 API Key 업데이트 및 저장", use_container_width=True, type="primary"):
                        if new_key.strip():
                            st.session_state.api_gemini = new_key.strip()
                            st.session_state.gemini_exhausted = False
                            st.success("API Key가 업데이트되었습니다! 다시 생성을 시도해 주세요.")
                            time.sleep(1.2)
                            st.rerun()
                        else:
                            st.warning("유효한 API Key를 입력해 주세요.")
                            
                st.session_state.v5_sheet_id = st.text_input(
                    "🟢 Google Sheets ID (대본 시트 연동)", 
                    value=st.session_state.v5_sheet_id,
                    placeholder="예: 1zH8m8Z5T1u...",
                    help="구글 스프레드시트 ID를 입력하면 시트 내의 대본 데이터를 가져와 일괄 자동 제작할 수 있습니다."
                )
                
                topic_input = st.text_input(
                    "직접 입력할 주제 (스프레드시트 미사용 시)", 
                    value=st.session_state.topic,
                    placeholder="예: 구글 크롬 브라우저의 역사와 탄생 비화"
                )
                
                st.markdown("#### ☁️ Google Vertex AI 비주얼 및 성우 설정")
                
                st.session_state.v5_gtts_voice = st.selectbox(
                    "구글 프리미엄 한국어 성우 보이스",
                    ["ko-KR-Neural2-A (남성 - 표준)", "ko-KR-Neural2-B (여성 - 표준)", "ko-KR-Wavenet-A (남성 - 중후함)", "ko-KR-Journey-F (여성 - 친근함)", "ko-KR-Studio-O (남성 - 뉴스 성우)"],
                    index=0
                )
                
                v5_visual_models = ["Google Imagen 3 (고품질 이미지 + 모션 연출)", "Google Vertex AI Veo 2.0 (시네마틱 동영상 생성)"]
                st.session_state.v5_visual_model = st.selectbox(
                    "구글 비주얼 생성 엔진 선택",
                    v5_visual_models,
                    index=v5_visual_models.index(st.session_state.v5_visual_model),
                    help="Imagen 3는 고해상도 이미지를 생성한 후 모션 연출을 가미하며, Veo 2.0은 실제 5초 길이의 고품질 시네마틱 비디오 클립을 Google Cloud 상에서 완전 자체 생성합니다."
                )
                
                st.session_state.v5_imagen_aspect = st.selectbox(
                    "Google 비주얼 종횡비 (Aspect Ratio)",
                    ["9:16 (쇼츠 세로형)", "16:9 (일반 가로형)", "1:1 (정사각형)"],
                    index=0
                )
                
                with st.expander("🎨 프리미엄 화풍 커스터마이저 (Visual Style Customizer)", expanded=True):
                    st.markdown("**1. 다중 화풍 스타일 조합 및 강도 설정**")
                    all_preset_styles = [
                        "시네마틱 실사 (Cinematic Realism)",
                        "코믹/웹툰 (Comic / Webtoon)",
                        "뉴스/다큐 보도 (News & Documentary)",
                        "호러/미스터리 (Horror & Mystery)",
                        "큐티/러블리 (Cute & Lovely)",
                        "애니메이션 (Anime / Animation)",
                        "역사화 유화 (Historical Oil Painting)",
                        "수채화 판타지 (Watercolor Fantasy)"
                    ]
                    
                    st.session_state.v5_active_styles = st.multiselect(
                        "활성화할 화풍 스타일 (복수 선택 시 혼합 연출)",
                        all_preset_styles,
                        default=st.session_state.v5_active_styles
                    )
                    
                    # Strengths sliders for each active style
                    if st.session_state.v5_active_styles:
                        st.markdown("*각 스타일의 혼합 강도(Intensity) 조절:*")
                        for style in st.session_state.v5_active_styles:
                            current_strength = st.session_state.v5_style_strengths.get(style, 0.7)
                            st.session_state.v5_style_strengths[style] = st.slider(
                                f"└ {style} 강도",
                                min_value=0.0,
                                max_value=1.0,
                                value=current_strength,
                                step=0.1,
                                key=f"v5_strength_slide_{style}"
                            )
                            
                    st.markdown("**2. 커스텀 화풍 텍스트 직접 입력**")
                    st.session_state.v5_custom_style_desc = st.text_input(
                        "추가적인 화풍 묘사나 지시사항을 직접 입력하세요:",
                        value=st.session_state.v5_custom_style_desc,
                        placeholder="예: neon cyberpunk atmosphere, volumetric lighting, unreal engine 5 render"
                    )
                
                g_render_btn = st.button("🚀 Google Native 파이프라인 가동!", use_container_width=True, type="primary")
                if g_render_btn:
                    compile_v5_style()
                    if st.session_state.v5_sheet_id.strip():
                        with st.spinner("📊 Google Sheets에서 대본 데이터를 불러오는 중..."):
                            try:
                                import core_generator
                                script_data = core_generator.fetch_script_from_google_sheets(st.session_state.v5_sheet_id.strip())
                                st.session_state.script_data = script_data
                                st.session_state.topic = script_data.get("title", "Google Sheets AI Video")
                                st.session_state.step = "edit"
                                st.success("📊 Google Sheets 대본 로드 완료!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Google Sheets 로드 실패: {e}")
                    else:
                        if not topic_input.strip():
                            st.error("주제를 입력하거나 Google Sheets ID를 입력해 주세요.")
                        else:
                            st.session_state.topic = topic_input
                            with st.spinner("🧠 Gemini 2.5 Pro가 구글 네이티브 비디오 제작용 대본을 빌드하는 중..."):
                                try:
                                    import core_generator
                                    active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
                                    os.environ["GEMINI_API_KEY"] = active_gemini_key
                                    
                                    script_data = core_generator.generate_script_from_gemini(
                                        st.session_state.topic, 
                                        is_shorts=st.session_state.is_shorts, 
                                        character_desc=st.session_state.character_desc, 
                                        visual_style=st.session_state.visual_style,
                                        content_skin=st.session_state.content_genre
                                    )
                                    st.session_state.script_data = script_data
                                    st.session_state.step = "edit"
                                    st.success("🎉 시네마틱 다큐멘터리 대본이 성공적으로 작성되었습니다!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    err_msg = str(e)
                                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "credits are depleted" in err_msg:
                                        st.session_state.gemini_exhausted = True
                                    st.error(f"대본 생성 실패: {e}")
                                    
                st.markdown("---")
                st.markdown("### 🧪 10초 쾌속 테스트 코너 (Test Corner)")
                st.caption("대본 생성 및 편집 단계를 건너뛰고, 미리 준비된 10초 분량(2개 씬)의 다큐멘터리 대본으로 즉시 영상 제작 파이프라인을 가동하여 자막 레이아웃, 목소리, 비주얼 화풍을 테스트합니다.")
                
                test_render_btn_v5 = st.button("🎬 10초 테스트 영상 즉시 제작", key="test_v5", use_container_width=True)
                if test_render_btn_v5:
                    compile_v5_style()
                    test_script = {
                        "title": "10초 시네마틱 테스트 비디오",
                        "description": "버전별 연출 및 자막 렌더링 검증용 10초 테스트 비디오 #테스트 #다큐멘터리",
                        "tags": ["테스트", "다큐멘터리", "시네마틱"],
                        "overall_bgm_mood": "dark_mystery",
                        "scenes": [
                            {
                                "narration": "역사의 위대한 전설은 아주 작은 시작에서 탄생합니다.",
                                "visual_prompt": "A majestic cinematic sunrise over ancient mountains, detailed oil painting style, 8k",
                                "camera_movement": {"type": "zoom_in", "speed": "slow"},
                                "sfx_trigger": "none",
                                "sfx_timing": "start"
                            },
                            {
                                "narration": "시간의 흐름 속에서, 그 가치는 영원히 기억될 것입니다.",
                                "visual_prompt": "An hourglass on a researcher's wooden table, warm study room, dramatic chiaroscuro, 8k",
                                "camera_movement": {"type": "zoom_out", "speed": "slow"},
                                "sfx_trigger": "none",
                                "sfx_timing": "start"
                            }
                        ]
                    }
                    st.session_state.script_data = test_script
                    st.session_state.topic = "10초 시네마틱 테스트 비디오"
                    st.session_state.step = "render"
                    st.success("⚡ 테스트용 대본 로드 완료! 렌더링 파이프라인으로 이동합니다.")
                    time.sleep(1)
                    st.rerun()
                                    
            with col2:
                st.info("""
                **📢 구글 에코시스템 핵심 팁**
                - **Google Sheets 연동**: 시트에 `Topic`, `Visual Prompt`, `Narration` 컬럼을 생성해두면 여러 편의 쇼츠를 1클릭으로 제작 가능합니다.
                - **Imagen 3**: 최고의 텍스트 렌더링 화질과 공간 원근감을 제공하는 구글의 플래그십 이미지 생성 모델입니다.
                """)
        else:
            render_production_flow("v5.0.0")

    # Page 3: Library
    elif st.session_state.active_menu == "Library":
        st.markdown("### 📁 Google Cloud Storage (GCS) 자산보관함")
        st.markdown(f"GCS 버킷 `{st.session_state.v5_gcs_bucket}`에 업로드되어 아카이빙된 프로젝트 목록입니다.")
        
        try:
            from google.cloud import storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(st.session_state.v5_gcs_bucket)
            blobs = list(bucket.list_blobs(max_results=10))
            mp4_blobs = [b for b in blobs if b.name.endswith(".mp4")]
            if mp4_blobs:
                for idx, blob in enumerate(mp4_blobs):
                    with st.container(border=True):
                        col_g1, col_g2 = st.columns([2, 1.2])
                        with col_g1:
                            st.write(f"🎥 **블롭명**: `{blob.name}`")
                            st.video(blob.public_url)
                        with col_g2:
                            st.write(f"📦 **크기**: {blob.size / (1024 * 1024):.2f} MB")
                            st.write(f"📅 **업데이트**: {blob.updated}")
                            st.markdown(f"🔗 [GCS 퍼블릭 링크]({blob.public_url})")
            else:
                st.info("☁️ GCS 버킷 내에 업로드된 mp4 동영상이 없습니다. 스튜디오에서 첫 구글 네이티브 비디오를 렌더링해보세요!")
        except Exception as e:
            st.warning(f"⚠️ GCS 버킷 파일 목록 조회 실패 (인증 또는 버킷 설정을 확인하세요): {e}")
            st.markdown("---")
            st.markdown("##### 📁 로컬에 저장된 동영상 목록 (오프라인 폴백):")
            video_files = [f for f in os.listdir(".") if f.endswith(".mp4") and os.path.isfile(f) and f != "test_shorts.mp4"]
            if not video_files:
                st.info("아직 생성된 비디오가 없습니다.")
            else:
                video_files.sort(key=os.path.getmtime, reverse=True)
                for idx, video_file in enumerate(video_files):
                    with st.container(border=True):
                        st.markdown(f"##### 🎥 파일명: `{video_file}`")
                        st.video(video_file)

    # Page 4: Profile
    elif st.session_state.active_menu == "Profile":
        st.markdown("### 👤 Google Account & IAM 연동 상태")
        st.success("✉️ `google_developer@aividfactory.com` \n\n GCP IAM 권한: **Owner** \n\n 📡 Google Cloud Vertex AI 가속 장치 연결됨")

    # Page 5: Settings
    elif st.session_state.active_menu == "Settings":
        st.markdown("### ⚙️ GCP API Credentials & OAuth 설정")
        with st.form("google_api_config"):
            sa_path = st.text_input("Google Cloud Service Account JSON Key Path", value=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""), placeholder="/path/to/service_account.json", type="password")
            project_id = st.text_input("Google Cloud Project ID", value=os.environ.get("GOOGLE_CLOUD_PROJECT", ""), placeholder="my-gcp-project-1234")
            bucket_name = st.text_input("GCS Bucket Name", value=st.session_state.v5_gcs_bucket)
            gemini_key_input = st.text_input("Gemini API Key (Google AI Studio)", value=st.session_state.api_gemini, type="password", placeholder="AIzaSy...")
            submitted = st.form_submit_button("💾 구글 설정 저장")
            if submitted:
                if sa_path:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path
                if project_id:
                    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
                st.session_state.v5_gcs_bucket = bucket_name
                st.session_state.api_gemini = gemini_key_input.strip()
                st.session_state.gemini_exhausted = False
                st.success("💾 Google Cloud 및 Gemini API 설정이 저장되었습니다!")

# =========================================================================
# ==================== v4.0.0: 시네마틱 스튜디오 프로페셔널 ====================
# =========================================================================
elif "v4.0.0" in selected_version:
    # Sidebar layout for v4.0.0: High-End Cinematic console
    with st.sidebar:
        st.markdown("### 🎬 Cinematic Pro Console")
        st.caption("v4.0.0 Professional Edition")
        st.markdown("---")
        
        st.markdown("#### 🎛️ Live Render Specs")
        # Visual sliders showing professional specifications
        st.markdown(f"**Easing Curve**: `{st.session_state.v4_easing}`")
        st.markdown(f"**Film Grain**: `{st.session_state.v4_film_grain} / 100`")
        st.markdown(f"**Vignette Effect**: `{'ON' if st.session_state.v4_vignette else 'OFF'}`")
        st.markdown(f"**3D Panning**: `{'Active' if st.session_state.v4_3d_panning else 'Inactive'}`")
        
        st.markdown("---")
        st.caption("High-End Movie Editor Mode")

    # Main body navigation tabs for v4.0.0
    nav_cols = st.columns([1, 1, 1, 1, 1.2])
    with nav_cols[0]:
        if st.button("🏠 편집 홈 대시보드", use_container_width=True, type="primary" if st.session_state.active_menu == "Home" else "secondary"):
            st.session_state.active_menu = "Home"
            st.rerun()
    with nav_cols[1]:
        if st.button("🎬 프로 스튜디오", use_container_width=True, type="primary" if st.session_state.active_menu == "Studio" else "secondary"):
            st.session_state.active_menu = "Studio"
            st.rerun()
    with nav_cols[2]:
        if st.button("📁 프로젝트 보관함", use_container_width=True, type="primary" if st.session_state.active_menu == "Library" else "secondary"):
            st.session_state.active_menu = "Library"
            st.rerun()
    with nav_cols[3]:
        if st.button("👤 프로 멤버십", use_container_width=True, type="primary" if st.session_state.active_menu == "Profile" else "secondary"):
            st.session_state.active_menu = "Profile"
            st.rerun()
    with nav_cols[4]:
        if st.button("⚙️ 하이엔드 어드민 설정", use_container_width=True, type="primary" if st.session_state.active_menu == "Settings" else "secondary"):
            st.session_state.active_menu = "Settings"
            st.rerun()

    st.markdown("---")

    # Page 1: Home Dashboard
    if st.session_state.active_menu == "Home":
        st.markdown("### 🏠 시네마틱 스튜디오 대시보드")
        st.markdown("최상급 연출 옵션(비선형 카메라 무빙, 오디오 컴프레션, 3D 오디오 입체 패닝, 필름 노이즈 이펙트)이 기획된 영화 전문 편집 공간입니다.")
        
        col_st1, col_st2, col_st3 = st.columns(3)
        with col_st1:
            st.metric("시스템 렌더러 처리율", "🟢 24 FPS 가속화됨")
        with col_st2:
            st.metric("GPU 가속 인코더 상태", "🟢 NVIDIA NVENC H.264 연결됨")
        with col_st3:
            st.metric("마스터 오디오 볼륨", "-14 LUFS (유튜브 최적)")

    # Page 2: Studio
    elif st.session_state.active_menu == "Studio":
        if st.session_state.step == "input":
            st.markdown("### 🎬 하이엔드 비디오 프로 스튜디오")
            
            col1, col2 = st.columns([2, 1.2])
            with col1:
                topic_input = st.text_input(
                    "제작할 고격조 다큐멘터리 주제를 입력하세요:",
                    value=st.session_state.topic,
                    placeholder="예: 링컨과 대통령 헌법 선언문의 비화"
                )
                
                st.markdown("#### 🎥 1. 비주얼 포스트 프로세싱 (Visual Effects)")
                st.session_state.v4_easing = st.selectbox(
                    "카메라 줌/팬 Easing 곡선 (비선형 가속)",
                    ["Cubic Ease-in-out (할리우드 시네마틱)", "Linear (선형 직선 속도)", "Quadratic Ease-out (부드러운 감속)"]
                )
                
                st.session_state.v4_film_grain = st.slider(
                    "필름 그레인 노이즈 강도 (Film Grain Noise)", 
                    min_value=0, max_value=100, value=st.session_state.v4_film_grain,
                    help="값이 높아질수록 아날로그 영화 필름 느낌의 미세 노이즈가 강해집니다."
                )
                
                st.session_state.v4_vignette = st.checkbox("비네팅 감쇠 효과 활성화 (Vignette Effect)", value=st.session_state.v4_vignette)
                
                st.markdown("#### 🎙️ 2. 오디오 마스터링 (Audio Mastering)")
                st.session_state.v4_3d_panning = st.checkbox("3D 입체 효과음 패닝 활성화 (Spatial Sound SFX)", value=st.session_state.v4_3d_panning)
                st.session_state.v4_compressor = st.checkbox("나레이션 컴프레서/리미터 결합 (Voice Radio Tone)", value=st.session_state.v4_compressor)
                
                st.markdown("#### 🗣️ 3. ElevenLabs TTS 디테일 튜닝")
                st.session_state.v4_voice_stability = st.slider("Stability (목소리 일관성 및 정돈)", 0.0, 1.0, st.session_state.v4_voice_stability)
                st.session_state.v4_voice_clarity = st.slider("Clarity + Similarity Boost (선명도 및 모사력)", 0.0, 1.0, st.session_state.v4_voice_clarity)
                st.session_state.v4_voice_style = st.slider("Style Exaggeration (감정 표현 강도)", 0.0, 1.0, st.session_state.v4_voice_style)
                
                pro_render_btn = st.button("🚀 최고화질 프로 시네마틱 렌더링 기동!", use_container_width=True, type="primary")
                if pro_render_btn:
                    if not topic_input.strip():
                        st.error("다큐멘터리 주제를 입력해 주세요.")
                    else:
                        st.session_state.topic = topic_input
                        with st.spinner("🧠 Gemini 2.5 Pro가 고격조 역사 다큐멘터리 대본을 작성하고 있습니다..."):
                            try:
                                import core_generator
                                active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
                                os.environ["GEMINI_API_KEY"] = active_gemini_key
                                
                                script_data = core_generator.generate_script_from_gemini(
                                    st.session_state.topic, 
                                    is_shorts=st.session_state.is_shorts, 
                                    character_desc=st.session_state.character_desc, 
                                    visual_style=st.session_state.visual_style,
                                    content_skin=st.session_state.content_genre
                                )
                                st.session_state.script_data = script_data
                                st.session_state.step = "edit"
                                st.success("🎉 시네마틱 다큐멘터리 대본이 성공적으로 작성되었습니다!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"대본 생성 실패: {e}")
                                
                st.markdown("---")
                st.markdown("### 🧪 10초 쾌속 테스트 코너 (Test Corner)")
                st.caption("대본 생성 및 편집 단계를 건너뛰고, 미리 준비된 10초 분량(2개 씬)의 다큐멘터리 대본으로 즉시 영상 제작 파이프라인을 가동하여 자막 레이아웃, 목소리, 비주얼 화풍을 테스트합니다.")
                
                test_render_btn_v4 = st.button("🎬 10초 테스트 영상 즉시 제작", key="test_v4", use_container_width=True)
                if test_render_btn_v4:
                    test_script = {
                        "title": "10초 시네마틱 테스트 비디오",
                        "description": "버전별 연출 및 자막 렌더링 검증용 10초 테스트 비디오 #테스트 #다큐멘터리",
                        "tags": ["테스트", "다큐멘터리", "시네마틱"],
                        "overall_bgm_mood": "dark_mystery",
                        "scenes": [
                            {
                                "narration": "역사의 위대한 전설은 아주 작은 시작에서 탄생합니다.",
                                "visual_prompt": "A majestic cinematic sunrise over ancient mountains, detailed oil painting style, 8k",
                                "camera_movement": {"type": "zoom_in", "speed": "slow"},
                                "sfx_trigger": "none",
                                "sfx_timing": "start"
                            },
                            {
                                "narration": "시간의 흐름 속에서, 그 가치는 영원히 기억될 것입니다.",
                                "visual_prompt": "An hourglass on a researcher's wooden table, warm study room, dramatic chiaroscuro, 8k",
                                "camera_movement": {"type": "zoom_out", "speed": "slow"},
                                "sfx_trigger": "none",
                                "sfx_timing": "start"
                            }
                        ]
                    }
                    st.session_state.script_data = test_script
                    st.session_state.topic = "10초 시네마틱 테스트 비디오"
                    st.session_state.step = "render"
                    st.success("⚡ 테스트용 대본 로드 완료! 렌더링 파이프라인으로 이동합니다.")
                    time.sleep(1)
                    st.rerun()
                                
            with col2:
                st.markdown("#### 🎛️ 하이엔드 연출 가이드")
                st.info("""
                - **Cubic Easing**: 모션 그래픽이 출발할 때는 천천히, 중간에는 빠르게, 멈출 때는 서서히 감속하여 전문 영화 카메라 줌 느낌을 자아냅니다.
                - **Film Grain**: 디지털 영상 특유의 딱딱함을 모래 질감 노이즈로 덮어 고풍스러운 질감을 표현합니다.
                """)
        else:
            render_production_flow("v4.0.0")

    # Page 3: Library
    elif st.session_state.active_menu == "Library":
        st.markdown("### 📁 시네마틱 프로젝트 보관함")
        st.markdown("최전방에서 렌더링된 고품질 동영상 프로젝트입니다.")
        st.info("보관함에 저장된 고격조 시네마틱 프로젝트가 없습니다. 스튜디오에서 렌더링을 시작해 보세요!")

    # Page 4: Profile
    elif st.session_state.active_menu == "Profile":
        st.markdown("### 👤 프로 멤버십 요금 관리")
        st.success(" Tier: **Enterprise Studio VIP** \n\n 📡 전용 초고속 백그라운드 병렬 인코딩 GPU 할당됨")

    # Page 5: Settings
    elif st.session_state.active_menu == "Settings":
        st.markdown("### ⚙️ 하이엔드 전용 API 연동 및 시스템 세팅")
        with st.form("v4_settings"):
            st.text_input("Kling AI API Key", type="password")
            st.text_input("Luma Dream Machine API Key", type="password")
            st.text_input("Midjourney API Key (Giga)", type="password")
            st.form_submit_button("💾 하이엔드 설정 저장")

# =========================================================================
# ==================== v3.0.0: 보안 & SaaS 통합 대시보드 ====================
# =========================================================================
elif "v3.0.0" in selected_version:
    # Sidebar layout for v3.0.0: Brand, User Profile, Credits, Admin Password Lock
    with st.sidebar:
        st.markdown("### 🏢 Video SaaS Portal")
        st.caption("v3.0.0 Premium Edition")
        st.markdown("---")
        
        # User details card based on role
        st.markdown("#### 👤 회원 상태")
        if st.session_state.user_role == "Standard User":
            st.info("✉️ `standard@aividfactory.com` \n\n **Tier**: Standard (Free) \n\n 📡 일반 서버 엔진 연결됨")
            st.markdown("**🔋 남은 렌더링 크레딧**")
            st.metric(label="Credits", value="32 / 50")
            st.progress(32 / 50)
        elif st.session_state.user_role == "VIP Partner":
            st.success("✉️ `partner_vip@aividfactory.com` \n\n **Tier**: Enterprise VIP \n\n 📡 프리미엄 가속 엔진 연결됨")
            st.markdown("**🔋 남은 렌더링 크레딧**")
            st.metric(label="Credits", value="482 / 500", delta="-18 (최근 제작)")
            st.progress(482 / 500)
        elif st.session_state.user_role == "System Admin":
            st.warning("✉️ `admin@aividfactory.com` \n\n **Tier**: System Administrator \n\n 🔐 개발자 권한 인증됨")
            st.markdown("**🔋 남은 렌더링 크레딧**")
            st.metric(label="Credits", value="무제한 (Unlimited)")
            st.progress(1.0)
            
        st.markdown("---")
        
        # Admin Lock Verification Console
        st.markdown("#### 🔑 관리자 권한 잠금")
        if not st.session_state.is_admin:
            pwd_input = st.text_input("관리자 패스워드 입력", type="password", help="비밀번호 'admin1234'를 입력하면 어드민 설정 메뉴가 잠금 해제됩니다.")
            if pwd_input == "admin1234":
                st.session_state.is_admin = True
                st.session_state.user_role = "System Admin"
                st.session_state.active_menu = "Settings"
                st.toast("🔓 관리자 모드가 활성화되었습니다!")
                st.rerun()
            elif pwd_input:
                st.error("잘못된 패스워드입니다.")
        else:
            st.success("🔓 관리자 모드 활성화됨")
            if st.button("로그아웃 (일반 모드)", use_container_width=True):
                st.session_state.is_admin = False
                st.session_state.user_role = "Standard User"
                st.session_state.active_menu = "Home"
                st.toast("🔒 일반 모드로 전환되었습니다.")
                st.rerun()
                
        st.markdown("---")
        st.caption("서비스 내부 보안 규정 준수 | DLP 가동 중")

    # Main body page routing navigation buttons
    nav_cols = st.columns([1, 1, 1, 1, 1.2])
    with nav_cols[0]:
        if st.button("🏠 홈 대시보드", use_container_width=True, type="primary" if st.session_state.active_menu == "Home" else "secondary"):
            st.session_state.active_menu = "Home"
            st.rerun()
    with nav_cols[1]:
        if st.button("🎬 비디오 스튜디오", use_container_width=True, type="primary" if st.session_state.active_menu == "Studio" else "secondary"):
            st.session_state.active_menu = "Studio"
            st.rerun()
    with nav_cols[2]:
        if st.button("📁 마이 보관함", use_container_width=True, type="primary" if st.session_state.active_menu == "Library" else "secondary"):
            st.session_state.active_menu = "Library"
            st.rerun()
    with nav_cols[3]:
        if st.button("👤 마이페이지", use_container_width=True, type="primary" if st.session_state.active_menu == "Profile" else "secondary"):
            st.session_state.active_menu = "Profile"
            st.rerun()
            
    if st.session_state.is_admin:
        with nav_cols[4]:
            if st.button("⚙️ 시스템 설정 (보안)", use_container_width=True, type="primary" if st.session_state.active_menu == "Settings" else "secondary"):
                st.session_state.active_menu = "Settings"
                st.rerun()
    else:
        with nav_cols[4]:
            st.button("⚙️ 잠겨있음 (어드민 전용)", use_container_width=True, disabled=True)

    st.markdown("---")

    # PAGE 1: HOME DASHBOARD
    if st.session_state.active_menu == "Home":
        st.markdown("### 🏠 홈 대시보드 (Dashboard)")
        st.markdown(f"**환영합니다, {st.session_state.user_role}님!** 비디오 팩토리 솔루션 대시보드에 오신 것을 환영합니다.")
        
        # Stat widgets
        c_stat1, c_stat2, c_stat3 = st.columns(3)
        with c_stat1:
            # Scan directory for generated mp4 files to show real count
            video_files_count = len([f for f in os.listdir(".") if f.endswith(".mp4") and os.path.isfile(f) and f != "test_shorts.mp4"])
            st.metric(label="총 제작한 비디오 수", value=f"{video_files_count} 개")
        with c_stat2:
            st.metric(label="서버 가동 상태", value="🟢 정상 작동 (Normal)")
        with c_stat3:
            cred_val = "무제한" if st.session_state.user_role == "System Admin" else ("482 / 500" if st.session_state.user_role == "VIP Partner" else "32 / 50")
            st.metric(label="남은 크레딧", value=cred_val)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### ⚡ 빠른 메뉴 바로가기")
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.markdown("""
            <div class='dashboard-card'>
                <h4>🎬 비디오 스튜디오 (Studio)</h4>
                <p>AI 다큐멘터리, 스토리텔링 등 5가지 기술 스킨을 활용해 영상 제작 기획 단계를 시작합니다.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("비디오 스튜디오로 가기", key="go_studio", use_container_width=True):
                st.session_state.active_menu = "Studio"
                st.rerun()
                
        with col_c2:
            st.markdown("""
            <div class='dashboard-card'>
                <h4>📁 마이 보관함 (Library)</h4>
                <p>현재까지 생성된 완성 동영상 파일을 실시간 스캔하여 재생하고 다운로드합니다.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("마이 보관함으로 가기", key="go_library", use_container_width=True):
                st.session_state.active_menu = "Library"
                st.rerun()
                
        with col_c3:
            st.markdown("""
            <div class='dashboard-card'>
                <h4>👤 마이페이지 & 회원 정보</h4>
                <p>가상 멤버십 등급(Standard / VIP)을 설정하고 크레딧 요금 및 보안 인증 가이드를 조회합니다.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("마이페이지로 가기", key="go_profile", use_container_width=True):
                st.session_state.active_menu = "Profile"
                st.rerun()

    # PAGE 2: STUDIO (VIDEO PRODUCTION)
    elif st.session_state.active_menu == "Studio":
        if st.session_state.step == "input":
            st.markdown("### 📝 1단계: 비디오 기획 및 스킨 설정")
            col1, col2 = st.columns([2, 1.2])
            
            with col1:
                # 1. Technical Production Skin
                video_skins = [
                    "Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)",
                    "Option 2: AI 비디오 직접 생성 (AI Video Generation - Luma/Kling)",
                    "Option 3: 스톡 비디오 매칭 (Stock Footage - Pexels API)",
                    "Option 4: AI 아바타 발표자 스타일 (AI Talking Avatar Presenter)",
                    "Option 5: 타이포그래피 & 자막 포커스 (Minimalist Typography)"
                ]
                selected_video_skin = st.selectbox(
                    "동영상 기술 제작방식(스킨) 선택",
                    video_skins,
                    index=video_skins.index(st.session_state.video_skin),
                    help="영상의 최종 프레임들을 합성하고 렌더링하는 핵심 기술 메커니즘을 지정합니다."
                )
                if selected_video_skin != st.session_state.video_skin:
                    st.session_state.video_skin = selected_video_skin
                    st.rerun()

                # 2. Content Genre Presets
                genre_presets = [
                    "🎬 역사 다큐멘터리 (Historical Documentary)",
                    "💡 동기부여 & 자기계발 (Motivation & Self-Development)",
                    "🔬 과학 & 일반 상식 (Science & Trivia)",
                    "📖 소설 & 판타지 스토리텔링 (Fiction & Storytelling)",
                    "👻 공포 & 미스터리 극장 (Horror & Mystery)"
                ]
                selected_genre = st.selectbox(
                    "콘텐츠 장르 & 테마 카테고리 선택",
                    genre_presets,
                    index=genre_presets.index(st.session_state.content_genre),
                    help="선택한 장르 카테고리는 대본 성우 말투, 어조, BGM 무드 등 기획과 내용 구성을 규정합니다."
                )
                if selected_genre != st.session_state.content_genre:
                    st.session_state.content_genre = selected_genre
                    if selected_genre == "🔬 과학 & 일반 상식 (Science & Trivia)":
                        st.session_state.visual_style = "3D 애니메이션 스타일 (Pixar-style 3D Render)"
                    elif selected_genre == "📖 소설 & 판타지 스토리텔링 (Fiction & Storytelling)":
                        st.session_state.visual_style = "역사화 유화 스타일 (Historical Oil Painting)"
                    else:
                        st.session_state.visual_style = "시네마틱 실사 영화 스틸컷 (Dramatic Cinematic Shot)"
                    st.rerun()

                topic_input = st.text_input(
                    "시네마틱 콘텐츠의 주제를 입력하세요:",
                    value=st.session_state.topic,
                    placeholder="예시: 나폴레옹의 워털루 전투 패배 원인 3가지"
                )
                
                st.markdown("#### 🎨 인물 및 화풍 일관성 설정")
                enable_consistency = st.checkbox("인물/화풍 일관성 규칙 활성화", value=True)
                
                char_desc_input = ""
                style_desc_input = ""
                
                if enable_consistency:
                    char_desc_input = st.text_area(
                        "주요 인물 외모 묘사 (Character Description)",
                        value=st.session_state.character_desc,
                        placeholder="예시: 이순신 장군: 40대 남성, 흉터가 있는 얼굴, 조선시대 갑옷 착용, 굳건한 표정",
                        help="인물의 외모 특징을 자세히 적을수록 모든 AI 이미지에서 캐릭터가 동일한 얼굴로 묘사됩니다."
                    )
                    
                    style_presets = [
                        "시네마틱 실사 영화 스틸컷 (Dramatic Cinematic Shot)",
                        "3D 애니메이션 스타일 (Pixar-style 3D Render)",
                        "역사화 유화 스타일 (Historical Oil Painting)",
                        "웹툰/만화 스타일 (Anime Webtoon)",
                        "직접 입력 (Custom Style)"
                    ]
                    try:
                        preset_idx = style_presets.index(st.session_state.visual_style)
                    except ValueError:
                        preset_idx = 0
                    style_selection = st.selectbox("비주얼 화풍/스타일 선택", style_presets, index=preset_idx)
                    
                    if style_selection == "직접 입력 (Custom Style)":
                        style_desc_input = st.text_input(
                            "커스텀 화풍 스타일 묘사",
                            value=st.session_state.custom_style,
                            placeholder="예시: Cyberpunk neon style, high contrast, cyberpunk city background"
                        )
                    else:
                        style_desc_input = style_selection
                
                # Advanced options inside Step 1
                with st.expander("🎥 렌더링 규격 및 채널 설정 (고급 옵션)", expanded=False):
                    fmt_opt = st.selectbox(
                        "비디오 포맷", 
                        ["쇼츠 (9:16 세로형)", "일반 영상 (16:9 가로형)"],
                        index=["쇼츠 (9:16 세로형)", "일반 영상 (16:9 가로형)"].index(st.session_state.format_option)
                    )
                    ql_opt = st.selectbox(
                        "렌더링 화질 선택 (서버 권장: 540p)", 
                        ["540p (Cloud 최적화 - 서버용)", "720p (Standard)", "1080p (High - 로컬 PC 권장)"],
                        index=["540p (Cloud 최적화 - 서버용)", "720p (Standard)", "1080p (High - 로컬 PC 권장)"].index(st.session_state.quality_option)
                    )
                    prv_opt = st.selectbox(
                        "유튜브 업로드 보안 설정", 
                        ["비공개 (Private)", "공개 (Public)", "일부공개 (Unlisted)"],
                        index=["비공개 (Private)", "공개 (Public)", "일부공개 (Unlisted)"].index(st.session_state.privacy_option)
                    )
                    
                    if (fmt_opt != st.session_state.format_option or 
                        ql_opt != st.session_state.quality_option or 
                        prv_opt != st.session_state.privacy_option):
                        
                        st.session_state.format_option = fmt_opt
                        st.session_state.quality_option = ql_opt
                        st.session_state.privacy_option = prv_opt
                        
                        st.session_state.is_shorts = (fmt_opt == "쇼츠 (9:16 세로형)")
                        st.session_state.privacy_status = "private" if "비공개" in prv_opt else ("public" if "공개" in prv_opt else "unlisted")
                        
                        if "540p" in ql_opt:
                            st.session_state.target_size = (540, 960) if st.session_state.is_shorts else (960, 540)
                        elif "720p" in ql_opt:
                            st.session_state.target_size = (720, 1280) if st.session_state.is_shorts else (1280, 720)
                        else: # 1080p
                            st.session_state.target_size = (1080, 1920) if st.session_state.is_shorts else (1920, 1080)
                        st.rerun()

                generate_script_btn = st.button("🚀 2단계: 대본 및 시나리오 기획안 생성", use_container_width=True)
                
                if generate_script_btn:
                    active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
                    if not topic_input:
                        st.error("주제를 입력해주세요!")
                    elif not active_gemini_key:
                        st.error("Gemini API Key 설정이 필요합니다. 관리자 콘솔 잠금을 해제하고 Settings 메뉴에서 입력하거나 서버 .env 설정을 확인하세요.")
                    else:
                        with st.spinner("📝 Gemini 2.5 Pro가 장르 테마와 스킨 기획을 분석해 대본을 제작하고 있습니다..."):
                            try:
                                os.environ["GEMINI_API_KEY"] = active_gemini_key
                                import core_generator
                                script_data = core_generator.generate_script_from_gemini(
                                    topic_input,
                                    is_shorts=st.session_state.is_shorts,
                                    character_desc=char_desc_input,
                                    visual_style=style_desc_input,
                                    content_skin=st.session_state.content_genre
                                )
                                st.session_state.script_data = script_data
                                st.session_state.topic = topic_input
                                st.session_state.character_desc = char_desc_input
                                st.session_state.visual_style = style_selection
                                st.session_state.custom_style = style_desc_input if style_selection == "직접 입력 (Custom Style)" else ""
                                st.session_state.step = "edit"
                                st.rerun()
                            except Exception as e:
                                st.error(f"대본 생성 실패: {e}")

            with col2:
                st.markdown("#### 💡 장르 & 스킨 팁")
                st.info(f"""
                - **선택된 제작방식 (스킨)**: `{st.session_state.video_skin}`
                - **선택된 장르 테마**: `{st.session_state.content_genre}`
                - 스킨(Skin)은 미디어 소스 렌더링에 사용할 기술적 수단(이미지 무빙, AI 비디오, Pexels API 스톡 매칭 등)을 결정합니다.
                """)

        elif st.session_state.step == "edit":
            st.markdown("### 📝 2단계: 대본 및 연출 디테일 수정")
            
            if st.session_state.script_data is None:
                st.warning("생성된 대본이 없습니다. 처음 단계로 돌아갑니다.")
                st.session_state.step = "input"
                st.rerun()
                
            script_data = st.session_state.script_data
            
            st.markdown("#### ⚙️ 전체 설정")
            col_t1, col_t2 = st.columns([2, 1])
            with col_t1:
                script_data["title"] = st.text_input("유튜브 동영상 제목", value=script_data.get("title", ""))
                script_data["description"] = st.text_area("동영상 설명 (Description)", value=script_data.get("description", ""))
            with col_t2:
                tags_str = st.text_input("태그 (쉼표로 구분)", value=", ".join(script_data.get("tags", [])))
                script_data["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
                
                bgm_moods = ["epic_orchestral", "dark_mystery", "sad_piano", "intense_suspense"]
                bgm_mood = script_data.get("overall_bgm_mood", "epic_orchestral")
                if bgm_mood not in bgm_moods:
                    bgm_moods.append(bgm_mood)
                script_data["overall_bgm_mood"] = st.selectbox("배경음악 무드", bgm_moods, index=bgm_moods.index(bgm_mood))

            st.markdown("---")
            st.markdown("#### 🎬 씬(Scene)별 상세 편집")
            
            scenes = script_data.get("scenes", [])
            for i, scene in enumerate(scenes):
                with st.container(border=True):
                    st.markdown(f"##### 🎥 Scene {i+1}")
                    col_ed1, col_ed2 = st.columns([2, 1.2])
                    
                    with col_ed1:
                        scene["narration"] = st.text_area(f"씬 {i+1} 나레이션 대사 (한국어)", value=scene.get("narration", ""), key=f"scene_narr_{i}")
                        scene["visual_prompt"] = st.text_area(f"씬 {i+1} 이미지 생성 프롬프트 (영어)", value=scene.get("visual_prompt", ""), key=f"scene_prompt_{i}")
                        
                    with col_ed2:
                        camera_info = scene.get("camera_movement", {})
                        camera_types = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]
                        cam_type = camera_info.get("type", "zoom_in")
                        if cam_type not in camera_types:
                            camera_types.append(cam_type)
                        
                        selected_cam_type = st.selectbox(f"카메라 연출", camera_types, index=camera_types.index(cam_type), key=f"scene_cam_type_{i}")
                        
                        camera_speeds = ["slow", "medium"]
                        cam_speed = camera_info.get("speed", "slow")
                        if cam_speed not in camera_speeds:
                            camera_speeds.append(cam_speed)
                        selected_cam_speed = st.selectbox(f"카메라 속도", camera_speeds, index=camera_speeds.index(cam_speed), key=f"scene_cam_speed_{i}")
                        scene["camera_movement"] = {"type": selected_cam_type, "speed": selected_cam_speed}
                        
                        sfx_list = ["none", "sword_clash", "thunder", "wind_howl", "horse_gallop", "fire_crackle"]
                        sfx_trigger = scene.get("sfx_trigger", "none")
                        if sfx_trigger not in sfx_list:
                            sfx_list.append(sfx_trigger)
                            
                        selected_sfx = st.selectbox(f"효과음(SFX)", sfx_list, index=sfx_list.index(sfx_trigger), key=f"scene_sfx_{i}")
                        
                        sfx_timings = ["start", "middle", "end"]
                        sfx_timing = scene.get("sfx_timing", "start")
                        if sfx_timing not in sfx_timings:
                            sfx_timings.append(sfx_timing)
                        selected_sfx_timing = st.selectbox(f"효과음 타이밍", sfx_timings, index=sfx_timings.index(sfx_timing), key=f"scene_sfx_timing_{i}")
                        scene["sfx_trigger"] = selected_sfx
                        scene["sfx_timing"] = selected_sfx_timing
                        
                        if st.button(f"🗑️ Scene {i+1} 삭제", key=f"del_scene_{i}"):
                            scenes.pop(i)
                            st.session_state.script_data["scenes"] = scenes
                            st.rerun()
                            
            col_act1, col_act2, col_act3 = st.columns([1, 1, 2])
            with col_act1:
                if st.button("➕ 씬 추가"):
                    new_scene = {
                        "narration": "새로운 장면 나레이션을 입력하세요.",
                        "visual_prompt": "A cinematic shot of a scene, detailed, photorealistic",
                        "camera_movement": {"type": "zoom_in", "speed": "slow"},
                        "sfx_trigger": "none",
                        "sfx_timing": "start"
                    }
                    scenes.append(new_scene)
                    st.session_state.script_data["scenes"] = scenes
                    st.rerun()
            with col_act2:
                if st.button("↩️ 대본 초기화 및 처음으로"):
                    st.session_state.script_data = None
                    st.session_state.step = "input"
                    st.rerun()
            with col_act3:
                if st.button("🚀 3단계: 최종 비디오 렌더링 시작!", use_container_width=True, type="primary"):
                    st.session_state.step = "render"
                    st.rerun()

        elif st.session_state.step == "render":
            st.markdown("### ⚙️ 3단계: 비디오 렌더링 및 파일 합성")
            if st.session_state.script_data is None:
                st.warning("렌더링할 대본 데이터가 없습니다.")
                st.session_state.step = "input"
                st.rerun()
                
            progress_area = st.empty()
            cb = get_progress_callback(progress_area)
            
            try:
                import core_generator
                
                active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
                active_eleven_key = st.session_state.api_eleven if st.session_state.api_eleven else elevenlabs_key
                active_fal_key = st.session_state.api_fal if st.session_state.api_fal else fal_key
                active_openai_key = st.session_state.api_openai if st.session_state.api_openai else openai_key
                active_pexels_key = st.session_state.api_pexels if st.session_state.api_pexels else pexels_key
                
                os.environ["GEMINI_API_KEY"] = active_gemini_key
                if active_eleven_key:
                    os.environ["ELEVENLABS_API_KEY"] = active_eleven_key
                if active_fal_key:
                    os.environ["FAL_API_KEY"] = active_fal_key
                    os.environ["FAL_KEY"] = active_fal_key
                if active_openai_key:
                    os.environ["OPENAI_API_KEY"] = active_openai_key
                if active_pexels_key:
                    os.environ["PEXELS_API_KEY"] = active_pexels_key

                # Run background cleanup of old dynamic files (older than 10 mins)
                cleanup_old_files()
                
                import uuid
                timestamp = int(time.time())
                unique_id = uuid.uuid4().hex[:8]
                
                # Make dynamic uniquely isolatable names for temp dir and outputs
                temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_assets_{timestamp}_{unique_id}")
                output_filename = f"final_output_{timestamp}_{unique_id}.mp4"
                
                video_path, script_data = core_generator.generate_full_video(
                    st.session_state.topic, 
                    is_shorts=st.session_state.is_shorts, 
                    output_filename=output_filename,
                    tts_provider=st.session_state.tts_provider,
                    tts_voice_id=st.session_state.tts_voice_id,
                    tts_api_key=active_eleven_key,
                    image_provider=st.session_state.image_provider,
                    fal_key=active_fal_key,
                    openai_key=active_openai_key,
                    pregenerated_script=st.session_state.script_data,
                    target_size=st.session_state.target_size,
                    content_skin=st.session_state.content_genre,
                    video_skin=st.session_state.video_skin,
                    pexels_key=active_pexels_key,
                    progress_callback=cb,
                    temp_dir=temp_dir
                )
                
                stable_video_path = f"output_render_{timestamp}_{unique_id}.mp4"
                shutil.copy(video_path, stable_video_path)
                st.session_state.final_video_path = stable_video_path
                
                # Clean up the initial raw render filename to keep directory clean
                try:
                    os.remove(output_filename)
                except Exception:
                    pass
                
                cb("RENDER")  # Update to final render (Thumbnails & Packaging)
                thumbnail_path = f"thumbnail_output_{timestamp}_{unique_id}.png"
                temp_thumb_bg_path = f"temp_thumb_bg_{timestamp}_{unique_id}.jpg"
                
                core_generator.generate_cinematic_image(
                    f"A dramatic and historical scene representing {st.session_state.topic}, digital art, masterpiece, realistic, cinematic lighting",
                    temp_thumb_bg_path,
                    is_shorts=False,
                    provider=st.session_state.image_provider,
                    fal_key=active_fal_key,
                    openai_key=active_openai_key
                )
                
                thumb_bg = Image.open(temp_thumb_bg_path)
                thumb_bg = thumb_bg.resize((1280, 720))
                draw = ImageDraw.Draw(thumb_bg)
                font = core_generator.get_system_font(font_size=80)
                
                clean_title = st.session_state.script_data.get("title", st.session_state.topic)
                lines = core_generator.wrap_text(clean_title, font, 1100, draw)
                
                current_y = 180
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font) if hasattr(draw, "textbbox") else draw.textsize(line, font=font)
                    line_w = bbox[2] - bbox[0] if hasattr(draw, "textbbox") else bbox[0]
                    line_h = bbox[3] - bbox[1] if hasattr(draw, "textbbox") else bbox[1]
                    x = (1280 - line_w) // 2
                    
                    stroke_w = 6
                    for dx in range(-stroke_w, stroke_w+1):
                        for dy in range(-stroke_w, stroke_w+1):
                            draw.text((x+dx, current_y+dy), line, font=font, fill=(0, 0, 0, 255))
                            
                    draw.text((x, current_y), line, font=font, fill=(255, 235, 59, 255))
                    current_y += line_h + 20
                    
                thumb_bg.save(thumbnail_path)
                st.session_state.thumbnail_path = thumbnail_path
                
                try:
                    os.remove(temp_thumb_bg_path)
                except Exception:
                    pass
                    
                cb("DONE")
                time.sleep(1.5)
                st.session_state.step = "result"
                st.rerun()
            except Exception as e:
                st.error(f"❌ 영상 제작 중 오류 발생: {e}")
                if st.button("↩️ 편집 단계로 돌아가기"):
                    st.session_state.step = "edit"
                    st.rerun()

        elif st.session_state.step == "result":
            st.markdown("### 🎉 4단계: 비디오 제작 및 업로드 결과")
            col_res1, col_res2 = st.columns([2, 1.2])
            
            with col_res1:
                if st.session_state.final_video_path:
                    st.markdown("### 🎬 완성된 영상 미리보기")
                    st.video(st.session_state.final_video_path)
                    
                    st.markdown("### 📝 최종 기획서 및 대본")
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
                            
            with col_res2:
                if st.session_state.thumbnail_path:
                    st.markdown("### 🖼️ 패키징된 썸네일")
                    st.image(st.session_state.thumbnail_path, use_column_width=True)
                    
                st.markdown("### 📢 YouTube 채널로 전송")
                st.info("유튜브 자동 업로드를 위해서는 `client_secrets.json` 파일이 루트 폴더에 준비되어야 합니다.")
                
                secrets_exist = os.path.exists("client_secrets.json")
                if not secrets_exist:
                    st.warning("⚠️ `client_secrets.json` 파일이 없습니다. OAuth 인증 설정을 확인하세요.")
                    
                upload_btn = st.button("📢 유튜브에 비디오 즉시 업로드", disabled=not secrets_exist, use_container_width=True)
                
                if upload_btn:
                    with st.spinner("📡 유튜브 API 연동 및 업로드 처리 중..."):
                        try:
                            import youtube_uploader
                            vid_id = youtube_uploader.upload_video(
                                video_path=st.session_state.final_video_path,
                                title=st.session_state.script_data.get("title", st.session_state.topic),
                                description=st.session_state.script_data.get("description", ""),
                                tags=st.session_state.script_data.get("tags", []),
                                category_id="22",
                                privacy_status=st.session_state.privacy_status
                            )
                            youtube_uploader.upload_thumbnail(vid_id, st.session_state.thumbnail_path)
                            st.success(f"🎉 유튜브 업로드 성공! 비디오 ID: {vid_id}")
                            st.markdown(f"🔗 [유튜브 영상 링크](https://youtu.be/{vid_id})")
                        except Exception as e:
                            st.error(f"유튜브 업로드 실패: {e}")
                            
                st.markdown("---")
                if st.button("↩️ 처음으로 (새 비디오 만들기)", use_container_width=True):
                    st.session_state.script_data = None
                    st.session_state.final_video_path = None
                    st.session_state.thumbnail_path = None
                    st.session_state.step = "input"
                    st.rerun()

    # PAGE 3: LIBRARY (RECENT RENDERED VIDEOS)
    elif st.session_state.active_menu == "Library":
        st.markdown("### 📁 마이 보관함 (Library)")
        st.markdown("이 장치에서 최근에 성공적으로 제작 및 렌더링된 동영상 리스트입니다.")
        
        video_files = [f for f in os.listdir(".") if f.endswith(".mp4") and os.path.isfile(f) and f != "test_shorts.mp4"]
        if not video_files:
            st.info("아직 생성된 비디오가 없습니다. Studio 메뉴에서 첫 비디오를 제작해 보세요!")
        else:
            video_files.sort(key=os.path.getmtime, reverse=True)
            for idx, video_file in enumerate(video_files):
                with st.container(border=True):
                    col_v1, col_v2 = st.columns([2, 1.2])
                    with col_v1:
                        st.markdown(f"##### 🎥 파일명: `{video_file}`")
                        st.video(video_file)
                    with col_v2:
                        f_size = os.path.getsize(video_file) / (1024 * 1024)
                        f_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(video_file)))
                        st.write(f"**파일 크기**: {f_size:.2f} MB")
                        st.write(f"**제작 일시**: {f_time}")
                        
                        with open(video_file, "rb") as f:
                            st.download_button(
                                label=f"💾 다운로드 ({video_file})",
                                data=f,
                                file_name=video_file,
                                mime="video/mp4",
                                key=f"dl_v3_{video_file}_{idx}"
                            )

    # PAGE 4: PROFILE & ROLE SELECTION SIMULATION
    elif st.session_state.active_menu == "Profile":
        st.markdown("### 👤 회원 정보 및 서비스 프로필")
        st.markdown("SaaS 서비스 멤버십 및 자원 사용량 시뮬레이션을 제어할 수 있습니다.")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("#### 💳 멤버십 등급 시뮬레이션")
            st.markdown("개발 과정 테스트를 위해 등급을 자유롭게 조정해볼 수 있습니다.")
            sim_role = st.radio(
                "가상 요금제 역할군 선택",
                ["Standard User (일반 회원)", "VIP Partner (기업 파트너)"],
                index=0 if st.session_state.user_role == "Standard User" else 1
            )
            if "Standard" in sim_role and st.session_state.user_role != "Standard User" and not st.session_state.is_admin:
                st.session_state.user_role = "Standard User"
                st.rerun()
            elif "VIP" in sim_role and st.session_state.user_role != "VIP Partner" and not st.session_state.is_admin:
                st.session_state.user_role = "VIP Partner"
                st.rerun()
                
            if st.session_state.is_admin:
                st.warning("⚠️ 현재 관리자 모드가 활성화되어 있습니다. 역할을 전환하려면 사이드바에서 로그아웃을 먼저 진행하십시오.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 🔐 보안 정책 및 가이드라인")
            st.warning("본 동영상 팩토리 솔루션은 기업의 내부 API 보안 가이드라인 및 데이터 누출 방지(DLP) 정책을 엄격히 준수합니다. 관리자 외에는 API key 수정 페이지가 노출되지 않으며, 공란일 경우 안전하게 백엔드 .env 바인딩 키를 사용해 작동됩니다.")
            
        with col_p2:
            st.markdown("#### 📊 크레딧 & 상세 정보")
            if st.session_state.user_role == "Standard User":
                st.info("✉️ **standard@aividfactory.com** \n\n 구독 상태: 무료 체험 사용 중")
                st.metric(label="남은 크레딧", value="32 / 50")
            elif st.session_state.user_role == "VIP Partner":
                st.success("✉️ **partner_vip@aividfactory.com** \n\n 구독 상태: Enterprise VIP (구독 기간: 2026-12-31)")
                st.metric(label="남은 크레딧", value="482 / 500")
            else:
                st.warning("✉️ **admin@aividfactory.com** \n\n 구독 상태: System Administrator")
                st.metric(label="남은 크레딧", value="무제한 (Unlimited)")

    # PAGE 5: SYSTEM SETTINGS (ADMIN SECURED)
    elif st.session_state.active_menu == "Settings" and st.session_state.is_admin:
        st.markdown("### ⚙️ 시스템 보안 설정 (System Admin Config)")
        st.markdown("이 페이지는 어드민 권한 획득 시에만 노출되는 보안 영역입니다. 입력된 API 키는 브라우저 상에 노출되지 않도록 마스킹 처리되어 보관됩니다.")
        
        with st.form("api_settings_form_v3"):
            has_gemini = "설정됨 (기본 서버 키 사용 가능)" if gemini_key else "미설정"
            has_eleven = "설정됨 (기본 서버 키 사용 가능)" if elevenlabs_key else "미설정"
            has_fal = "설정됨 (기본 서버 키 사용 가능)" if fal_key else "미설정"
            has_openai = "설정됨 (기본 서버 키 사용 가능)" if openai_key else "미설정"
            has_pexels = "설정됨 (기본 서버 키 사용 가능)" if pexels_key else "미설정"
            
            st.markdown("#### 1. API Credentials")
            
            gemini_input = st.text_input(
                "Gemini API Key", 
                value=st.session_state.api_gemini, 
                type="password",
                placeholder=f"기본 키 상태: {has_gemini}",
                help="비워두면 서버 기본값을 사용합니다."
            )
            eleven_input = st.text_input(
                "ElevenLabs API Key", 
                value=st.session_state.api_eleven, 
                type="password",
                placeholder=f"기본 키 상태: {has_eleven}",
                help="비워두면 서버 기본값을 사용합니다."
            )
            fal_input = st.text_input(
                "Fal.ai API Key (Flux.1 / SVD 용)", 
                value=st.session_state.api_fal, 
                type="password",
                placeholder=f"기본 키 상태: {has_fal}",
                help="비워두면 서버 기본값을 사용합니다."
            )
            openai_input = st.text_input(
                "OpenAI API Key (DALL-E 3 용)", 
                value=st.session_state.api_openai, 
                type="password",
                placeholder=f"기본 키 상태: {has_openai}",
                help="비워두면 서버 기본값을 사용합니다."
            )
            pexels_input = st.text_input(
                "Pexels API Key (스톡 비디오 용)", 
                value=st.session_state.api_pexels, 
                type="password",
                placeholder=f"기본 키 상태: {has_pexels}",
                help="비워두면 서버 기본값을 사용합니다."
            )
            
            st.markdown("#### 2. 글로벌 엔진 설정")
            tts_options = ["ElevenLabs (시네마틱 성우)", "Edge-TTS (무료 나레이션)"]
            current_tts_idx = 0 if st.session_state.tts_provider == "elevenlabs" else 1
            selected_tts_disp = st.selectbox("기본 TTS 엔진", tts_options, index=current_tts_idx)
            
            img_options = ["Flux.1 Dev (fal.ai/초고해상도)", "DALL-E 3 (OpenAI/고화질)", "Pollinations.ai (무료)"]
            if st.session_state.image_provider == "fal-ai":
                current_img_idx = 0
            elif st.session_state.image_provider == "dall-e-3":
                current_img_idx = 1
            else:
                current_img_idx = 2
            selected_img_disp = st.selectbox("기본 이미지 생성 모델", img_options, index=current_img_idx)

            st.markdown("##### 세부 목소리 설정")
            voice_selection_eleven = st.selectbox(
                "ElevenLabs 성우 보이스", 
                ["Adam (남성 - 중후함/신뢰)", "Rachel (여성 - 차분함/나레이션)", "Antoni (남성 - 깊음/예고편)", "Bella (여성 - 밝음/낭독)", "커스텀 보이스 ID"]
            )
            custom_voice_id = st.text_input("커스텀 ElevenLabs 보이스 ID", value="pNInz6obpgq5mWzIA5FD")
            voice_selection_edge = st.selectbox("Edge-TTS 나레이터", ["남성 (InJoon)", "여성 (SunHi)"])
            
            submit_settings = st.form_submit_button("💾 설정 저장")
            
            if submit_settings:
                st.session_state.api_gemini = gemini_input
                st.session_state.api_eleven = eleven_input
                st.session_state.api_fal = fal_input
                st.session_state.api_openai = openai_input
                st.session_state.api_pexels = pexels_input
                st.session_state.tts_provider = "elevenlabs" if "ElevenLabs" in selected_tts_disp else "edge"
                st.session_state.image_provider = "fal-ai" if "Flux.1" in selected_img_disp else ("dall-e-3" if "DALL-E" in selected_img_disp else "pollinations")
                
                if st.session_state.tts_provider == "elevenlabs":
                    if voice_selection_eleven == "커스텀 보이스 ID":
                        st.session_state.tts_voice_id = custom_voice_id
                    else:
                        voice_map = {
                            "Adam (남성 - 중후함/신뢰)": "pNInz6obpgq5mWzIA5FD",
                            "Rachel (여성 - 차분함/나레이션)": "21m00Tcm4TlvDq8ikWAM",
                            "Antoni (남성 - 깊음/예고편)": "ErXwobaYiN019PkySvjV",
                            "Bella (여성 - 밝음/낭독)": "EXAVITQu4vr4xnSDxMaL"
                        }
                        st.session_state.tts_voice_id = voice_map[voice_selection_eleven]
                else:
                    st.session_state.tts_voice_id = "ko-KR-InJoonNeural" if "남성" in voice_selection_edge else "ko-KR-SunHiNeural"
                    
                st.success("✅ 시스템 설정이 안전하게 저장되었습니다!")
                st.rerun()


# =========================================================================
# ==================== v2.0.0: 스킨 및 장르 다양성 도입 ====================
# =========================================================================
elif "v2.0.0" in selected_version:
    # Sidebar navigation radio (v2.0.0 legacy interface)
    with st.sidebar:
        st.markdown("### 🎬 AI Video Studio (v2.0.0)")
        st.markdown("---")
        menu_v2 = st.radio(
            "메뉴 내비게이션",
            ["Studio (비디오 제작)", "Library (마이 보관함)", "Settings (보안 설정)", "Profile (회원 정보)"],
            index=0,
            key="v2_sidebar_menu"
        )
        st.markdown("---")
        active_gemini = st.session_state.api_gemini or gemini_key
        if active_gemini:
            st.success("📡 시스템 엔진 연결됨")
        else:
            st.warning("⚠️ API 설정이 필요합니다")

    # Render pages based on selection
    if menu_v2 == "Studio (비디오 제작)":
        if st.session_state.step == "input":
            st.markdown("### 📝 1단계: 비디오 기획 및 스킨 설정 (v2.0.0)")
            col1, col2 = st.columns([2, 1.2])
            
            with col1:
                video_skins = [
                    "Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)",
                    "Option 2: AI 비디오 직접 생성 (AI Video Generation - Luma/Kling)",
                    "Option 3: 스톡 비디오 매칭 (Stock Footage - Pexels API)",
                    "Option 4: AI 아바타 발표자 스타일 (AI Talking Avatar Presenter)",
                    "Option 5: 타이포그래피 & 자막 포커스 (Minimalist Typography)"
                ]
                selected_video_skin = st.selectbox("동영상 기술 제작방식(스킨) 선택", video_skins, index=video_skins.index(st.session_state.video_skin), key="v2_skin")
                st.session_state.video_skin = selected_video_skin

                genre_presets = [
                    "🎬 역사 다큐멘터리 (Historical Documentary)",
                    "💡 동기부여 & 자기계발 (Motivation & Self-Development)",
                    "🔬 과학 & 일반 상식 (Science & Trivia)",
                    "📖 소설 & 판타지 스토리텔링 (Fiction & Storytelling)",
                    "👻 공포 & 미스터리 극장 (Horror & Mystery)"
                ]
                selected_genre = st.selectbox("콘텐츠 장르 & 테마 카테고리 선택", genre_presets, index=genre_presets.index(st.session_state.content_genre), key="v2_genre")
                st.session_state.content_genre = selected_genre

                topic_input = st.text_input("시네마틱 콘텐츠의 주제를 입력하세요:", value=st.session_state.topic, key="v2_topic")
                
                st.markdown("#### 🎨 인물 및 화풍 일관성 설정")
                char_desc_input = st.text_area("주요 인물 외모 묘사", value=st.session_state.character_desc, key="v2_char_desc")
                style_selection = st.selectbox("비주얼 화풍/스타일 선택", ["시네마틱 실사 영화 스틸컷 (Dramatic Cinematic Shot)", "3D 애니메이션 스타일 (Pixar-style 3D Render)", "역사화 유화 스타일 (Historical Oil Painting)", "웹툰/만화 스타일 (Anime Webtoon)", "직접 입력 (Custom Style)"], key="v2_style_sel")
                
                if style_selection == "직접 입력 (Custom Style)":
                    style_desc_input = st.text_input("커스텀 화풍 스타일 묘사", value=st.session_state.custom_style, key="v2_custom_style")
                else:
                    style_desc_input = style_selection
                
                # Render options inside sidebar for v2.0.0
                st.info("비디오 규격 및 해상도는 사이드바의 Settings 메뉴나 .env 기본 설정에 동기화됩니다.")
                
                generate_script_btn = st.button("🚀 2단계: 대본 생성 시작", use_container_width=True, key="v2_gen_btn")
                if generate_script_btn:
                    active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
                    if not topic_input:
                        st.error("주제를 입력해주세요!")
                    elif not active_gemini_key:
                        st.error("Gemini API Key가 비어있습니다. Settings 메뉴에서 설정해주세요.")
                    else:
                        with st.spinner("📝 대본 생성 중..."):
                            try:
                                os.environ["GEMINI_API_KEY"] = active_gemini_key
                                import core_generator
                                script_data = core_generator.generate_script_from_gemini(
                                    topic_input,
                                    is_shorts=st.session_state.is_shorts,
                                    character_desc=char_desc_input,
                                    visual_style=style_desc_input,
                                    content_skin=st.session_state.content_genre
                                )
                                st.session_state.script_data = script_data
                                st.session_state.topic = topic_input
                                st.session_state.character_desc = char_desc_input
                                st.session_state.visual_style = style_selection
                                st.session_state.step = "edit"
                                st.rerun()
                            except Exception as e:
                                st.error(f"대본 생성 실패: {e}")

            with col2:
                st.info("v2.0.0은 5가지 제작 스킨과 씬(Scene)별 인물 일관성 설정이 추가된 버전입니다.")

        elif st.session_state.step == "edit":
            st.markdown("### 📝 2단계: 대본 및 연출 디테일 수정 (v2.0.0)")
            script_data = st.session_state.script_data
            if script_data is None:
                st.session_state.step = "input"
                st.rerun()
                
            script_data["title"] = st.text_input("동영상 제목", value=script_data.get("title", ""), key="v2_title")
            script_data["description"] = st.text_area("설명", value=script_data.get("description", ""), key="v2_desc")
            
            scenes = script_data.get("scenes", [])
            for i, scene in enumerate(scenes):
                with st.container(border=True):
                    st.markdown(f"##### Scene {i+1}")
                    scene["narration"] = st.text_area("나레이션", value=scene.get("narration", ""), key=f"v2_narr_{i}")
                    scene["visual_prompt"] = st.text_area("이미지 프롬프트", value=scene.get("visual_prompt", ""), key=f"v2_prompt_{i}")
                    
            if st.button("🚀 렌더링 가동", type="primary", use_container_width=True, key="v2_render_start_btn"):
                st.session_state.step = "render"
                st.rerun()

        elif st.session_state.step == "render":
            st.markdown("### ⚙️ 3단계: 비디오 렌더링 중...")
            with st.status("렌더링 엔진 작동 중...") as status:
                try:
                    import core_generator
                    active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
                    active_eleven_key = st.session_state.api_eleven if st.session_state.api_eleven else elevenlabs_key
                    active_fal_key = st.session_state.api_fal if st.session_state.api_fal else fal_key
                    active_openai_key = st.session_state.api_openai if st.session_state.api_openai else openai_key
                    active_pexels_key = st.session_state.api_pexels if st.session_state.api_pexels else pexels_key
                    
                    os.environ["GEMINI_API_KEY"] = active_gemini_key
                    if active_eleven_key:
                        os.environ["ELEVENLABS_API_KEY"] = active_eleven_key
                    if active_fal_key:
                        os.environ["FAL_API_KEY"] = active_fal_key
                    if active_openai_key:
                        os.environ["OPENAI_API_KEY"] = active_openai_key
                    if active_pexels_key:
                        os.environ["PEXELS_API_KEY"] = active_pexels_key

                    cleanup_old_files()
                    import uuid
                    timestamp = int(time.time())
                    unique_id = uuid.uuid4().hex[:8]
                    
                    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_assets_{timestamp}_{unique_id}")
                    v2_raw_filename = f"v2_raw_{timestamp}_{unique_id}.mp4"
                    
                    video_path, script_data = core_generator.generate_full_video(
                        st.session_state.topic, 
                        is_shorts=st.session_state.is_shorts, 
                        output_filename=v2_raw_filename,
                        tts_provider=st.session_state.tts_provider,
                        tts_voice_id=st.session_state.tts_voice_id,
                        tts_api_key=active_eleven_key,
                        image_provider=st.session_state.image_provider,
                        fal_key=active_fal_key,
                        openai_key=active_openai_key,
                        pregenerated_script=st.session_state.script_data,
                        target_size=st.session_state.target_size,
                        content_skin=st.session_state.content_genre,
                        video_skin=st.session_state.video_skin,
                        pexels_key=active_pexels_key,
                        temp_dir=temp_dir
                    )
                    stable_video_path = f"v2_output_{timestamp}_{unique_id}.mp4"
                    shutil.copy(video_path, stable_video_path)
                    st.session_state.final_video_path = stable_video_path
                    
                    try:
                        os.remove(v2_raw_filename)
                    except Exception:
                        pass
                        
                    st.session_state.step = "result"
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")
                    if st.button("돌아가기"):
                        st.session_state.step = "edit"
                        st.rerun()

        elif st.session_state.step == "result":
            st.markdown("### 🎉 4단계: 비디오 제작 완료 (v2.0.0)")
            if st.session_state.final_video_path:
                st.video(st.session_state.final_video_path)
            if st.button("처음으로 돌아가기"):
                st.session_state.step = "input"
                st.rerun()

    elif menu_v2 == "Library (마이 보관함)":
        st.markdown("### 📁 마이 보관함 (Library - v2.0.0)")
        video_files = [f for f in os.listdir(".") if f.endswith(".mp4") and os.path.isfile(f) and f != "test_shorts.mp4"]
        for idx, video_file in enumerate(video_files):
            st.write(f"🎥 **{video_file}**")
            st.video(video_file)

    elif menu_v2 == "Settings (보안 설정)":
        st.markdown("### ⚙️ API 및 인프라 설정 (v2.0.0)")
        st.markdown("⚠️ **경고**: v2.0.0 버전에서는 보안 마스킹 처리가 미흡하여 API 키가 브라우저에 그대로 평문 노출될 수 있습니다.")
        
        st.session_state.api_gemini = st.text_input("Gemini API Key (Plain Text)", value=st.session_state.api_gemini, key="v2_key_gemini")
        st.session_state.api_eleven = st.text_input("ElevenLabs API Key (Plain Text)", value=st.session_state.api_eleven, key="v2_key_eleven")
        st.session_state.api_fal = st.text_input("Fal.ai API Key (Plain Text)", value=st.session_state.api_fal, key="v2_key_fal")
        st.session_state.api_openai = st.text_input("OpenAI API Key (Plain Text)", value=st.session_state.api_openai, key="v2_key_openai")
        st.session_state.api_pexels = st.text_input("Pexels API Key (Plain Text)", value=st.session_state.api_pexels, key="v2_key_pexels")
        
        st.session_state.format_option = st.selectbox("비디오 포맷", ["쇼츠 (9:16 세로형)", "일반 영상 (16:9 가로형)"], key="v2_format")
        st.session_state.is_shorts = (st.session_state.format_option == "쇼츠 (9:16 세로형)")

    elif menu_v2 == "Profile (회원 정보)":
        st.markdown("### 👤 회원 정보 (v2.0.0)")
        st.info("Standard VIP Plan 시뮬레이션 상태")
        st.metric("가상 크레딧", "482 / 500")


# =========================================================================
# ==================== v1.0.0: 초기 뼈대 및 설정 사이드바 ====================
# =========================================================================
else:
    # Sidebar config inputs (v1.0.0 style where ALL configs are cluttered in sidebar)
    with st.sidebar:
        st.markdown("### ⚙️ v1.0.0 Developer Console")
        st.markdown("---")
        
        # Plain Inputs for keys
        st.session_state.api_gemini = st.text_input("Gemini Key", value=st.session_state.api_gemini, key="v1_gemini")
        st.session_state.api_eleven = st.text_input("ElevenLabs Key", value=st.session_state.api_eleven, key="v1_eleven")
        st.session_state.api_fal = st.text_input("Fal.ai Key", value=st.session_state.api_fal, key="v1_fal")
        
        # Render configs directly in sidebar
        st.session_state.format_option = st.selectbox("Format", ["쇼츠 (9:16 세로형)", "일반 영상 (16:9 가로형)"], key="v1_fmt")
        st.session_state.is_shorts = (st.session_state.format_option == "쇼츠 (9:16 세로형)")
        st.session_state.quality_option = st.selectbox("Quality", ["540p (Cloud 최적화)", "720p (Standard)", "1080p (High)"], key="v1_qual")
        
        if "540p" in st.session_state.quality_option:
            st.session_state.target_size = (540, 960) if st.session_state.is_shorts else (960, 540)
        else:
            st.session_state.target_size = (720, 1280) if st.session_state.is_shorts else (1280, 720)

        # TTS Provider selection directly in sidebar
        st.session_state.tts_provider = st.selectbox("TTS Engine", ["edge", "elevenlabs"], key="v1_tts")
        st.session_state.image_provider = st.selectbox("Image Model", ["pollinations", "fal-ai"], key="v1_img")

    # Main body: ONLY Video Studio Wizard, no other pages
    st.markdown("### 🎬 AI Video Studio (v1.0.0 Core)")
    
    if st.session_state.step == "input":
        st.markdown("#### 1단계: 동영상 기획안 및 주제 입력")
        topic_v1 = st.text_input("콘텐츠 주제", value=st.session_state.topic, key="v1_topic_input")
        
        if st.button("기획 대본 생성", use_container_width=True, key="v1_sub_btn"):
            active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
            if not topic_v1:
                st.error("주제를 입력하세요.")
            elif not active_gemini_key:
                st.error("Gemini API Key가 누락되었습니다.")
            else:
                with st.spinner("대본 생성 중..."):
                    try:
                        os.environ["GEMINI_API_KEY"] = active_gemini_key
                        import core_generator
                        script_data = core_generator.generate_script_from_gemini(
                            topic_v1,
                            is_shorts=st.session_state.is_shorts,
                            character_desc="",
                            visual_style="시네마틱 실사 영화 스틸컷 (Dramatic Cinematic Shot)",
                            content_skin="🎬 역사 다큐멘터리 (Historical Documentary)"
                        )
                        st.session_state.script_data = script_data
                        st.session_state.topic = topic_v1
                        st.session_state.step = "edit"
                        st.rerun()
                    except Exception as e:
                        st.error(f"실패: {e}")
                        
    elif st.session_state.step == "edit":
        st.markdown("#### 2단계: 대본 검토 (v1.0.0)")
        script_data = st.session_state.script_data
        if script_data is None:
            st.session_state.step = "input"
            st.rerun()
            
        script_data["title"] = st.text_input("제목", value=script_data.get("title", ""), key="v1_title_val")
        
        scenes = script_data.get("scenes", [])
        for i, scene in enumerate(scenes):
            scene["narration"] = st.text_area(f"Scene {i+1} 나레이션", value=scene.get("narration", ""), key=f"v1_narr_{i}")
            
        if st.button("비디오 제작 시작", use_container_width=True, key="v1_render_btn"):
            st.session_state.step = "render"
            st.rerun()
            
    elif st.session_state.step == "render":
        st.markdown("#### 3단계: 비디오 합성 및 렌더링 중...")
        with st.spinner("비디오 렌더링 가동 중..."):
            try:
                import core_generator
                active_gemini_key = st.session_state.api_gemini if st.session_state.api_gemini else gemini_key
                active_eleven_key = st.session_state.api_eleven if st.session_state.api_eleven else elevenlabs_key
                active_fal_key = st.session_state.api_fal if st.session_state.api_fal else fal_key
                active_openai_key = st.session_state.api_openai if st.session_state.api_openai else openai_key
                active_pexels_key = st.session_state.api_pexels if st.session_state.api_pexels else pexels_key
                
                os.environ["GEMINI_API_KEY"] = active_gemini_key
                if active_eleven_key:
                    os.environ["ELEVENLABS_API_KEY"] = active_eleven_key
                if active_fal_key:
                    os.environ["FAL_API_KEY"] = active_fal_key
                if active_openai_key:
                    os.environ["OPENAI_API_KEY"] = active_openai_key
                if active_pexels_key:
                    os.environ["PEXELS_API_KEY"] = active_pexels_key

                cleanup_old_files()
                import uuid
                timestamp = int(time.time())
                unique_id = uuid.uuid4().hex[:8]
                
                temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_assets_{timestamp}_{unique_id}")
                v1_raw_filename = f"v1_raw_{timestamp}_{unique_id}.mp4"
                
                video_path, script_data = core_generator.generate_full_video(
                    st.session_state.topic, 
                    is_shorts=st.session_state.is_shorts, 
                    output_filename=v1_raw_filename,
                    tts_provider=st.session_state.tts_provider,
                    tts_voice_id=st.session_state.tts_voice_id,
                    tts_api_key=active_eleven_key,
                    image_provider=st.session_state.image_provider,
                    fal_key=active_fal_key,
                    openai_key=active_openai_key,
                    pregenerated_script=st.session_state.script_data,
                    target_size=st.session_state.target_size,
                    content_skin="🎬 역사 다큐멘터리 (Historical Documentary)",
                    video_skin="Option 1: 스틸컷 & Ken Burns 연출 (AI Image + Ken Burns)",
                    pexels_key=active_pexels_key,
                    temp_dir=temp_dir
                )
                stable_video_path = f"v1_output_{timestamp}_{unique_id}.mp4"
                shutil.copy(video_path, stable_video_path)
                st.session_state.final_video_path = stable_video_path
                
                try:
                    os.remove(v1_raw_filename)
                except Exception:
                    pass
                    
                st.session_state.step = "result"
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")
                if st.button("돌아가기"):
                    st.session_state.step = "edit"
                    st.rerun()
                    
    elif st.session_state.step == "result":
        st.markdown("#### 4단계: 최종 결과물")
        if st.session_state.final_video_path:
            st.video(st.session_state.final_video_path)
        if st.button("처음으로 돌아가기", key="v1_reset_btn"):
            st.session_state.step = "input"
            st.rerun()
