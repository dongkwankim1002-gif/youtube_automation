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
quality_option = st.sidebar.selectbox(
    "렌더링 화질 선택 (서버 배포용 권장: 540p)", 
    ["540p (Cloud 최적화 - 서버용)", "720p (Standard)", "1080p (High - 로컬 PC 권장)"],
    index=0
)
privacy_option = st.sidebar.selectbox("유튜브 업로드 보안 설정", ["비공개 (Private)", "공개 (Public)", "일부공개 (Unlisted)"])

is_shorts = (format_option == "쇼츠 (9:16 세로형)")
privacy_status = "private" if "비공개" in privacy_option else ("public" if "공개" in privacy_option else "unlisted")

# Determine target_size
if "540p" in quality_option:
    target_size = (540, 960) if is_shorts else (960, 540)
elif "720p" in quality_option:
    target_size = (720, 1280) if is_shorts else (1280, 720)
else: # 1080p
    target_size = (1080, 1920) if is_shorts else (1920, 1080)

# State Management for outputs and wizard steps
if "step" not in st.session_state:
    st.session_state.step = "input"
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

# Main Interface UI
st.markdown("<h1 class='main-title'>🎬 High-End Cinematic AI Video Factory</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>최고 품질의 성우 나레이션, 초고화질 AI 이미지, 역동적 카메라 연출이 결합된 시네마틱 동영상 자동화 생산기</p>", unsafe_allow_html=True)

# ----------------- PHASE 1: INPUT STEP -----------------
if st.session_state.step == "input":
    st.markdown("### 📝 1단계: 비디오 기획 및 스타일 설정")
    col1, col2 = st.columns([2, 1.2])
    
    with col1:
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
            
            # Find index of previous style in presets
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
        
        generate_script_btn = st.button("🚀 2단계: 대본 및 시나리오 기획안 생성", use_container_width=True)
        
        if generate_script_btn:
            if not topic_input:
                st.error("주제를 입력해주세요!")
            elif not os.environ.get("GEMINI_API_KEY"):
                st.error("Gemini API Key를 사이드바나 .env 파일에 입력해주세요!")
            else:
                with st.spinner("📝 Gemini 2.5 Pro가 시나리오와 대본을 기획하고 있습니다..."):
                    try:
                        import core_generator
                        script_data = core_generator.generate_script_from_gemini(
                            topic_input,
                            is_shorts=is_shorts,
                            character_desc=char_desc_input,
                            visual_style=style_desc_input
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
        st.markdown("#### 💡 팁 & 활용 가이드")
        st.info("""
        - **인물 일관성**: 특정 인물의 외모 특징(나이, 의상, 표정, 안경 여부 등)을 고정해주면 AI 이미지 모델(Flux.1/DALL-E 3)이 씬마다 최대한 동일한 인물로 렌더링합니다.
        - **화풍 일관성**: '시네마틱 실사'를 고르면 어두운 분위기의 역사 다큐멘터리 영화 스틸컷처럼, '3D 애니메이션'을 고르면 디즈니/픽사 스타일로 통일된 비주얼을 제공합니다.
        """)

# ----------------- PHASE 2: EDIT STEP -----------------
elif st.session_state.step == "edit":
    st.markdown("### 📝 2단계: 대본 및 연출 디테일 수정")
    
    if st.session_state.script_data is None:
        st.warning("생성된 대본이 없습니다. 처음 단계로 돌아갑니다.")
        st.session_state.step = "input"
        st.rerun()
        
    script_data = st.session_state.script_data
    
    # Global script settings
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
    
    # We display each scene inside a container
    for i, scene in enumerate(scenes):
        with st.container(border=True):
            st.markdown(f"##### 🎥 Scene {i+1}")
            
            c_ed1, c_ed2 = st.columns([2, 1.2])
            
            with c_ed1:
                scene["narration"] = st.text_area(
                    f"씬 {i+1} 나레이션 대사 (한국어)",
                    value=scene.get("narration", ""),
                    key=f"scene_narr_{i}"
                )
                scene["visual_prompt"] = st.text_area(
                    f"씬 {i+1} 이미지 생성 프롬프트 (영어)",
                    value=scene.get("visual_prompt", ""),
                    key=f"scene_prompt_{i}",
                    help="AI 이미지 생성기에 전달될 영문 프롬프트입니다. 인물 및 화풍 일관성을 유지할 수 있는 구체적인 묘사가 들어갑니다."
                )
                
            with c_ed2:
                # Camera movement selection
                camera_info = scene.get("camera_movement", {})
                camera_types = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]
                cam_type = camera_info.get("type", "zoom_in")
                if cam_type not in camera_types:
                    camera_types.append(cam_type)
                
                selected_cam_type = st.selectbox(
                    f"카메라 연출",
                    camera_types,
                    index=camera_types.index(cam_type),
                    key=f"scene_cam_type_{i}"
                )
                
                camera_speeds = ["slow", "medium"]
                cam_speed = camera_info.get("speed", "slow")
                if cam_speed not in camera_speeds:
                    camera_speeds.append(cam_speed)
                    
                selected_cam_speed = st.selectbox(
                    f"카메라 속도",
                    camera_speeds,
                    index=camera_speeds.index(cam_speed),
                    key=f"scene_cam_speed_{i}"
                )
                scene["camera_movement"] = {"type": selected_cam_type, "speed": selected_cam_speed}
                
                # SFX selection
                sfx_list = ["none", "sword_clash", "thunder", "wind_howl", "horse_gallop", "fire_crackle"]
                sfx_trigger = scene.get("sfx_trigger", "none")
                if sfx_trigger not in sfx_list:
                    sfx_list.append(sfx_trigger)
                    
                selected_sfx = st.selectbox(
                    f"효과음(SFX)",
                    sfx_list,
                    index=sfx_list.index(sfx_trigger),
                    key=f"scene_sfx_{i}"
                )
                
                sfx_timings = ["start", "middle", "end"]
                sfx_timing = scene.get("sfx_timing", "start")
                if sfx_timing not in sfx_timings:
                    sfx_timings.append(sfx_timing)
                    
                selected_sfx_timing = st.selectbox(
                    f"효과음 타이밍",
                    sfx_timings,
                    index=sfx_timings.index(sfx_timing),
                    key=f"scene_sfx_timing_{i}"
                )
                scene["sfx_trigger"] = selected_sfx
                scene["sfx_timing"] = selected_sfx_timing
                
                # Delete Scene Button
                if st.button(f"🗑️ Scene {i+1} 삭제", key=f"del_scene_{i}"):
                    scenes.pop(i)
                    st.session_state.script_data["scenes"] = scenes
                    st.rerun()
                    
    # Actions for scenes
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
        start_rendering = st.button("🚀 3단계: 최종 비디오 렌더링 시작!", use_container_width=True, type="primary")
        if start_rendering:
            st.session_state.step = "render"
            st.rerun()

# ----------------- PHASE 3: RENDER STEP -----------------
elif st.session_state.step == "render":
    st.markdown("### ⚙️ 3단계: 비디오 렌더링 및 파일 합성")
    
    if st.session_state.script_data is None:
        st.warning("렌더링할 대본 데이터가 없습니다.")
        st.session_state.step = "input"
        st.rerun()
        
    status_box = st.empty()
    
    with st.status("🎬 시네마틱 비디오 제작 공장 가동 중...", expanded=True) as status:
        try:
            import core_generator
            import shutil
            
            # Use settings from sidebar
            output_filename = "final_output.mp4"
            
            status.write("⚙️ 1단계: 성우 나레이션 및 AI 이미지 생성, 효과음 믹싱 중...")
            status.write("💾 2단계: MoviePy 비디오 렌더링 시작 (Ken Burns 카메라 무빙 및 BGM Ducking 적용)...")
            
            video_path, script_data = core_generator.generate_full_video(
                st.session_state.topic, 
                is_shorts=is_shorts, 
                output_filename=output_filename,
                tts_provider=tts_provider,
                tts_voice_id=tts_voice_id,
                tts_api_key=api_eleven if api_eleven else elevenlabs_key,
                image_provider=image_provider,
                fal_key=fal_api_key if fal_api_key else fal_key,
                openai_key=openai_api_key if openai_api_key else openai_key,
                pregenerated_script=st.session_state.script_data,
                target_size=target_size
            )
            
            # Copy final output to keep a stable file name
            stable_video_path = "output_render.mp4"
            shutil.copy(video_path, stable_video_path)
            st.session_state.final_video_path = stable_video_path
            
            # Generate custom thumbnail
            status.write("🖼️ 3단계: Pillow를 사용하여 텍스트 외곽선이 강조된 맞춤 썸네일 합성 중...")
            thumbnail_path = "thumbnail_output.png"
            
            core_generator.generate_cinematic_image(
                f"A dramatic and historical scene representing {st.session_state.topic}, digital art, masterpiece, realistic, cinematic lighting",
                "temp_thumb_bg.jpg",
                is_shorts=False,  # Thumbnails are 16:9
                provider=image_provider,
                fal_key=fal_api_key if fal_api_key else fal_key,
                openai_key=openai_api_key if openai_api_key else openai_key
            )
            
            # Draw stylized text on background
            from PIL import Image, ImageDraw, ImageFont
            thumb_bg = Image.open("temp_thumb_bg.jpg")
            thumb_bg = thumb_bg.resize((1280, 720)) # Standard YouTube thumbnail size
            draw = ImageDraw.Draw(thumb_bg)
            
            # Load Korean Bold Font
            font = core_generator.get_system_font(font_size=80)
            
            clean_title = st.session_state.script_data.get("title", st.session_state.topic)
            lines = core_generator.wrap_text(clean_title, font, 1100, draw)
            
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
            
            try:
                os.remove("temp_thumb_bg.jpg")
            except Exception:
                pass
                
            status.update(label="🎉 비디오 렌더링 완료!", state="complete", expanded=False)
            st.session_state.step = "result"
            st.rerun()
            
        except Exception as e:
            status.update(label="❌ 영상 제작 중 오류 발생", state="error")
            st.error(f"오류 상세: {e}")
            if st.button("↩️ 편집 단계로 돌아가기"):
                st.session_state.step = "edit"
                st.rerun()

# ----------------- PHASE 4: RESULT STEP -----------------
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
                        privacy_status=privacy_status
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
