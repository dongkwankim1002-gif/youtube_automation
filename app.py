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
        placeholder.markdown(html_content, unsafe_allow_html=True)
        
    return progress_callback



# --- 📂 VERSION SWITCHER AT THE VERY TOP ---
st.markdown("""
<div style='background: linear-gradient(135deg, #1e1e2e, #11111b); padding: 1.5rem; border-radius: 12px; border: 2px solid #ff4b4b; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(255, 75, 75, 0.15);'>
    <div style='display: flex; align-items: center; gap: 0.8rem;'>
        <span style='font-size: 2rem;'>📂</span>
        <div>
            <h3 style='margin:0; color:#ff4b4b; font-size:1.6rem; font-weight:800;'>개발 이력 모니터링 및 단계별 버전 스위처</h3>
            <p style='margin:0.2rem 0 0 0; color:#a0a0c0; font-size:0.98rem;'>
                초기 프로토타입 개발 단계(v1.0)부터 장르 도입 단계(v2.0), 최종 보안 강화 SaaS 완성 단계(v3.0)까지의 레이아웃 진화 과정을 실시간으로 확인할 수 있습니다.
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

selected_version = st.radio(
    "🔍 활성화할 애플리케이션 버전을 선택하세요 (버전 클릭 시 즉시 화면이 전환됩니다):",
    [
        "v3.0.0 (보안 & SaaS 통합 대시보드 - 현재 단계)",
        "v2.0.0 (컨텐츠 장르 및 제작 스킨 추가 - 이전 단계)",
        "v1.0.0 (초기 뼈대 및 설정 사이드바 - 최초 단계)"
    ],
    index=0,
    horizontal=True,
    help="선택한 단계의 UI와 보안 레벨로 화면이 즉시 재구성됩니다."
)

st.markdown("---")


# =========================================================================
# ==================== v3.0.0: 보안 & SaaS 통합 대시보드 ====================
# =========================================================================
if "v3.0.0" in selected_version:
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

                output_filename = "final_output.mp4"
                
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
                    progress_callback=cb
                )
                
                stable_video_path = "output_render.mp4"
                shutil.copy(video_path, stable_video_path)
                st.session_state.final_video_path = stable_video_path
                
                cb("RENDER")  # Update to final render (Thumbnails & Packaging)
                thumbnail_path = "thumbnail_output.png"
                
                core_generator.generate_cinematic_image(
                    f"A dramatic and historical scene representing {st.session_state.topic}, digital art, masterpiece, realistic, cinematic lighting",
                    "temp_thumb_bg.jpg",
                    is_shorts=False,
                    provider=st.session_state.image_provider,
                    fal_key=active_fal_key,
                    openai_key=active_openai_key
                )
                
                thumb_bg = Image.open("temp_thumb_bg.jpg")
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
                    os.remove("temp_thumb_bg.jpg")
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

                    video_path, script_data = core_generator.generate_full_video(
                        st.session_state.topic, 
                        is_shorts=st.session_state.is_shorts, 
                        output_filename="v2_output.mp4",
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
                        pexels_key=active_pexels_key
                    )
                    st.session_state.final_video_path = "v2_output.mp4"
                    shutil.copy(video_path, "v2_output.mp4")
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

                video_path, script_data = core_generator.generate_full_video(
                    st.session_state.topic, 
                    is_shorts=st.session_state.is_shorts, 
                    output_filename="v1_output.mp4",
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
                    pexels_key=active_pexels_key
                )
                st.session_state.final_video_path = "v1_output.mp4"
                shutil.copy(video_path, "v1_output.mp4")
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
