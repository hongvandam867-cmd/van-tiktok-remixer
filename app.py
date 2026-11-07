import os
import sys
import glob
import time
import random
import base64
import tempfile
import datetime
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import extra_streamlit_components as stx

# Import local modules
from video_processor import probe_video, process_video, merge_multiple_videos, get_ffmpeg_binary
from voice_engine import generate_voiceover, apply_voiceover_to_video, VOICE_OPTIONS, SCRIPT_TEMPLATES
from presets import PRESETS

# Cross-platform scratch directory
def get_scratch_dir() -> str:
    local_scratch = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "scratch")
    if os.path.exists(local_scratch):
        return local_scratch
    d = os.path.join(tempfile.gettempdir(), "van_tiktok_scratch")
    os.makedirs(d, exist_ok=True)
    return d

# Avatar path & helper
AVATAR_PATH = os.path.join(os.path.dirname(__file__), "assets", "van_avatar.jpg")

def get_avatar_base64() -> str:
    if os.path.exists(AVATAR_PATH):
        with open(AVATAR_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

APP_PASSWORD = "vanxinhyeu187"

# Page configuration
st.set_page_config(
    page_title="Tool của Vân xinh gái 💖 | TikTok Remixer",
    page_icon="💖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authentication check with multi-layer persistence (Query Param + Browser Cookie + LocalStorage)
cookie_manager = stx.CookieManager(key="van_auth_manager")
saved_cookie = cookie_manager.get(cookie="van_auth_token")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# If user explicitly logged out, keep logged out until they log in again
if st.session_state.get("just_logged_out", False):
    st.session_state["authenticated"] = False
else:
    # 1. Check URL query params (?token=vanxinhyeu187)
    if st.query_params.get("token") == APP_PASSWORD:
        st.session_state["authenticated"] = True
    # 2. Check Browser Cookie
    elif saved_cookie == APP_PASSWORD:
        st.session_state["authenticated"] = True
        st.query_params["token"] = APP_PASSWORD

if not st.session_state["authenticated"]:
    # 3. Check LocalStorage via JavaScript redirect if not recently logged out
    if not st.session_state.get("just_logged_out", False):
        st.html(f"""
        <script>
        try {{
            const saved = localStorage.getItem('van_auth_token');
            if (saved === '{APP_PASSWORD}') {{
                const url = new URL(window.location.href);
                if (url.searchParams.get('token') !== '{APP_PASSWORD}') {{
                    url.searchParams.set('token', '{APP_PASSWORD}');
                    window.location.href = url.href;
                }}
            }}
        }} catch(e) {{}}
        </script>
        """, unsafe_allow_javascript=True)

    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        iframe[height="0"] { display: none !important; }
        .stButton>button {
            background: linear-gradient(90deg, #FF69B4, #FF1493) !important;
            color: white !important;
            font-weight: 700 !important;
            border-radius: 12px !important;
            padding: 0.6rem 2rem !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    avatar_b64 = get_avatar_base64()
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.4, 1])
    with col_l2:
        img_tag = f'<img src="data:image/jpeg;base64,{avatar_b64}" style="width: 175px; height: 175px; object-fit: cover; border-radius: 50%; border: 4px solid #FF69B4; box-shadow: 0 0 30px rgba(255, 105, 180, 0.7), 0 0 50px rgba(255, 20, 147, 0.4); margin-bottom: 1.2rem;" />' if avatar_b64 else ''
        st.markdown(f"""
        <div style="text-align: center; margin-top: 2rem;">
            {img_tag}
            <h2 style="font-weight: 800; font-size: 1.7rem; background: linear-gradient(90deg, #FF69B4, #FF1493, #00F2FE); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.4rem;">
                Chào mừng bạn đến tool làm video của Vân xinh gái ✨
            </h2>
            <p style="color: #bbb; font-size: 0.95rem; margin-bottom: 1.5rem;">
                🔒 Vui lòng nhập mật khẩu để sử dụng tool
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            entered_pw = st.text_input("Mật khẩu:", type="password", placeholder="Nhập mật khẩu truy cập...", label_visibility="collapsed")
            col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
            with col_b2:
                login_btn = st.form_submit_button("💖 Đăng nhập", use_container_width=True)
            
            if login_btn:
                if entered_pw == APP_PASSWORD:
                    st.session_state["authenticated"] = True
                    if "just_logged_out" in st.session_state:
                        del st.session_state["just_logged_out"]
                    st.query_params["token"] = APP_PASSWORD
                    try:
                        cookie_manager.set(
                            cookie="van_auth_token",
                            val=APP_PASSWORD,
                            expires_at=datetime.datetime.now() + datetime.timedelta(days=180),
                            key="login_cookie_save"
                        )
                    except Exception:
                        pass
                    st.html(f"""
                    <script>
                    try {{
                        localStorage.setItem('van_auth_token', '{APP_PASSWORD}');
                    }} catch(e) {{}}
                    </script>
                    """, unsafe_allow_javascript=True)
                    st.success("✅ Đăng nhập thành công! Đã lưu phiên đăng nhập.")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("❌ Mật khẩu chưa đúng, hãy thử lại nha!")
                    
    st.stop()

# Ensure token & persistent storage are maintained during active session
if st.query_params.get("token") != APP_PASSWORD:
    st.query_params["token"] = APP_PASSWORD

st.html(f"""
<script>
try {{
    localStorage.setItem('van_auth_token', '{APP_PASSWORD}');
}} catch(e) {{}}
</script>
""", unsafe_allow_javascript=True)

# Custom Styling
st.markdown("""
<style>
    .welcome-box {
        display: inline-block;
        background: linear-gradient(135deg, rgba(255, 105, 180, 0.2), rgba(255, 20, 147, 0.3));
        border: 1px solid rgba(255, 105, 180, 0.6);
        padding: 8px 24px;
        border-radius: 30px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(255, 20, 147, 0.25);
    }
    .welcome-text {
        font-size: 1.25rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF69B4, #FF1493, #00F2FE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 0.8px;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF0050, #00F2FE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #888888;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1e1e24;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid #FF0050;
    }
    .stButton>button {
        background: linear-gradient(90deg, #FF0050, #FE2C55);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        transition: transform 0.1s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Title banner
st.markdown("""
<div class="welcome-box">
    <span>💖</span> <span class="welcome-text">Chào mừng bạn đến tool làm video của Vân xinh gái</span> <span>✨</span>
</div>
<div class="main-title">🎬 TikTok Video Remixer & Multi-Source Studio</div>
<div class="sub-title">Tự động xào nấu, ghép nối nhiều suộc video & lách bản quyền TikTok / Shorts / Reels 100% tự động</div>
""", unsafe_allow_html=True)

# Check FFmpeg readiness
try:
    ffmpeg_path = get_ffmpeg_binary()
    ffmpeg_ready = True
except Exception as e:
    ffmpeg_ready = False
    st.error(f"⚠️ Chưa tìm thấy FFmpeg: {str(e)}. Hãy đợi vài giây để hệ thống hoàn tất.")

# Sidebar settings
with st.sidebar:
    avatar_b64 = get_avatar_base64()
    if avatar_b64:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 0.8rem; padding-bottom: 0.8rem; border-bottom: 1px solid rgba(255, 105, 180, 0.25);">
            <img src="data:image/jpeg;base64,{avatar_b64}" style="width: 58px; height: 58px; object-fit: cover; border-radius: 50%; border: 2px solid #FF69B4; box-shadow: 0 0 10px rgba(255, 105, 180, 0.5);" />
            <div>
                <div style="font-weight: 800; color: #FF69B4; font-size: 1.05rem;">Vân xinh gái 💖</div>
                <div style="font-size: 0.8rem; color: #aaa;">Đang sử dụng tool</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    col_out1, col_out2 = st.columns([1, 1])
    with col_out2:
        if st.button("🔒 Đăng xuất", use_container_width=True, help="Đăng xuất và hủy lưu mật khẩu trên thiết bị này"):
            st.session_state["authenticated"] = False
            st.session_state["just_logged_out"] = True
            try:
                st.query_params.clear()
            except Exception:
                pass
            try:
                cookie_manager.delete(cookie="van_auth_token", key="logout_cookie_del")
            except Exception:
                pass
            st.html("""
            <script>
            try {
                localStorage.removeItem('van_auth_token');
                const url = new URL(window.location.href);
                url.searchParams.delete('token');
                window.history.replaceState({}, '', url.pathname);
            } catch(e) {}
            </script>
            """, unsafe_allow_javascript=True)
            time.sleep(0.4)
            st.rerun()
            
    st.header("⚙️ Cấu hình lách bản quyền")
    st.info("💡 Các thông số bên dưới sẽ được áp dụng khi render video để phá vỡ toàn bộ mã băm (MD5, Audio wave, Pixel grid) của TikTok.")
    
    preset_key = st.selectbox(
        "🎯 Chọn Preset cấu hình:",
        options=list(PRESETS.keys()),
        format_func=lambda x: PRESETS[x]["name"],
        index=0
    )
    
    selected_preset = PRESETS[preset_key]
    st.caption(selected_preset["description"])
    
    st.divider()
    st.subheader("⚡ Tăng tốc độ Render")
    engine_choice = st.selectbox(
        "Bộ xử lý tăng tốc:",
        options=["ultrafast", "gpu_amf", "veryfast"],
        format_func=lambda x: {
            "ultrafast": "⚡ Đa luồng 12 nhân CPU (Siêu tốc 2-3s - Khuyên dùng)",
            "gpu_amf": "🎮 Card đồ họa GPU AMD",
            "veryfast": "Tiêu chuẩn (Veryfast)"
        }[x],
        index=0,
        help="Chế độ 'Đa luồng 12 nhân' render song song nhiều suộc video cùng lúc, xuất video hoàn chỉnh chỉ trong 2-3 giây."
    )
    
    st.divider()
    st.subheader("🛠️ Tinh chỉnh thông số")
    
    speed = st.slider("Tốc độ video (Speed)", min_value=0.95, max_value=1.15, value=float(selected_preset["speed"]), step=0.01,
                      help="Thay đổi tốc độ 1.03 - 1.05x sẽ phá vỡ nhịp keyframe cũ mà người xem hầu như không nhận ra.")
    
    zoom = st.slider("Độ phóng to (Zoom)", min_value=1.00, max_value=1.15, value=float(selected_preset["zoom"]), step=0.01,
                     help="Phóng to 3-6% giúp cắt bỏ viền, logo ẩn ở mép và đổi tọa độ pixel.")
    
    flip_h = st.checkbox("Lật gương ngang (Horizontal Flip)", value=selected_preset["flip_h"],
                         help="Lật khung hình từ trái sang phải. Rất hiệu quả né quét AI, nhưng lưu ý nếu video có chữ sẽ bị ngược.")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        contrast = st.slider("Độ tương phản", min_value=0.90, max_value=1.20, value=float(selected_preset["contrast"]), step=0.01)
        brightness = st.slider("Độ sáng", min_value=-0.10, max_value=0.10, value=float(selected_preset["brightness"]), step=0.01)
    with col_c2:
        saturation = st.slider("Độ bão hòa", min_value=0.90, max_value=1.30, value=float(selected_preset["saturation"]), step=0.01)
        noise_intensity = st.slider("Độ nhiễu hạt (Noise)", min_value=0, max_value=10, value=int(selected_preset["noise_intensity"]),
                                    help="Mặc định 0 để render siêu tốc bằng GPU. Nếu tăng > 0, CPU sẽ tính toán nhiễu từng pixel.")
        
    add_vignette = st.checkbox("Hiệu ứng viền tối (Vignette)", value=selected_preset["add_vignette"])
    
    st.divider()
    st.subheader("✂️ Cắt đầu & Đuôi mỗi clip")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        cut_head = st.number_input("Cắt đầu (giây)", min_value=0.0, max_value=5.0, value=float(selected_preset["cut_head"]), step=0.1)
    with col_t2:
        cut_tail = st.number_input("Cắt đuôi (giây)", min_value=0.0, max_value=5.0, value=float(selected_preset["cut_tail"]), step=0.1)
        
    st.divider()
    st.subheader("🎵 Cao độ âm thanh (Pitch Shift)")
    pitch_shift = st.slider("Đổi cao độ (Pitch)", min_value=0.95, max_value=1.08, value=float(selected_preset["pitch_shift"]), step=0.01,
                            help="Đổi cao độ nhẹ giúp né bộ quét âm thanh Shazam/TikTok mà giọng nói không bị biến dạng kỳ quặc.")


# Main tabs
tab_merge, tab_voice, tab_single, tab_batch, tab_guide = st.tabs([
    "🎞️ Ghép nhiều suộc (Multi-Source)", 
    "🎙️ Tạo Text & Voice AI (Voiceover Studio)",
    "⚡ Xử lý đơn lẻ (1 video)", 
    "📁 Xử lý hàng loạt (Batch)", 
    "💡 Cẩm nang né bản quyền TikTok"
])

# ----------------- TAB 1: MULTI-SOURCE MERGER -----------------
with tab_merge:
    st.write("### 🎞️ Ghép nhiều suộc video có sẵn thành 1 video hoàn chỉnh")
    st.markdown("Chọn nhiều video nguồn (clips), hệ thống sẽ **tự động cắt ghép, đồng bộ tỷ lệ chuẩn 9:16 (1080x1920), áp dụng bộ lọc lách bản quyền** và xuất ra 1 video duy nhất.")
    
    col_m_src1, col_m_src2 = st.columns([1.2, 1])
    
    with col_m_src1:
        has_local_download = os.path.exists(r"D:\Download")
        source_choices = ["Chọn từ thư mục (D:\\Download)", "Tải lên nhiều video từ máy tính / điện thoại"] if has_local_download else ["Tải lên nhiều video từ máy tính / điện thoại", "Chọn từ thư mục"]
        merge_source_mode = st.radio(
            "Nguồn chọn suộc video:", 
            source_choices, 
            horizontal=True
        )
        
        selected_merge_paths = []
        
        if merge_source_mode == "Chọn từ thư mục (D:\\Download)":
            merge_dir = st.text_input("Thư mục chứa các video suộc:", value=r"D:\Download")
            if os.path.exists(merge_dir):
                m_exts = ("*.mp4", "*.mov", "*.mkv", "*.webm")
                available_files = []
                for ext in m_exts:
                    available_files.extend(glob.glob(os.path.join(merge_dir, ext)))
                    
                if available_files:
                    pick_all = st.checkbox("Chọn tất cả video trong thư mục", value=False)
                    if pick_all:
                        selected_merge_paths = available_files
                        st.info(f"Đã chọn toàn bộ {len(selected_merge_paths)} video.")
                    else:
                        chosen_names = st.multiselect(
                            f"Chọn các suộc muốn ghép ({len(available_files)} video tìm thấy):",
                            options=[os.path.basename(f) for f in available_files],
                            default=[os.path.basename(available_files[0]), os.path.basename(available_files[1])] if len(available_files) >= 2 else []
                        )
                        selected_merge_paths = [os.path.join(merge_dir, name) for name in chosen_names]
                else:
                    st.warning("Không có file video nào trong thư mục này.")
            else:
                st.error("Thư mục không tồn tại!")
        else:
            uploaded_sources = st.file_uploader(
                "Kéo thả hoặc tải lên nhiều file video:", 
                type=["mp4", "mov", "mkv"], 
                accept_multiple_files=True
            )
            if uploaded_sources:
                temp_upload_dir = os.path.join(get_scratch_dir(), "merge_uploads")
                os.makedirs(temp_upload_dir, exist_ok=True)
                for up_idx, up_file in enumerate(uploaded_sources):
                    ext = os.path.splitext(up_file.name)[1].lower() or ".mp4"
                    # Safe ASCII filename to guarantee 100% FFmpeg stability on all OS
                    clean_id = getattr(up_file, 'file_id', str(up_idx))
                    safe_name = f"up_{clean_id}_{int(time.time())}_{up_idx}{ext}"
                    f_path = os.path.join(temp_upload_dir, safe_name)
                    with open(f_path, "wb") as f:
                        f.write(up_file.getbuffer())
                    selected_merge_paths.append(f_path)
                st.success(f"Đã tải lên {len(selected_merge_paths)} video suộc.")

    with col_m_src2:
        st.write("##### ✂️ Chiến lược cắt & ghép")
        
        slice_mode = st.radio(
            "Độ dài mỗi suộc khi ghép:",
            ["Cắt mỗi suộc một đoạn ngắn (Khuyên dùng cho Shorts/TikTok)", "Giữ nguyên độ dài từng suộc"]
        )
        
        clip_sec = None
        if slice_mode == "Cắt mỗi suộc một đoạn ngắn (Khuyên dùng cho Shorts/TikTok)":
            clip_sec = st.slider("Thời lượng lấy từ mỗi suộc (giây):", min_value=1.0, max_value=20.0, value=5.0, step=0.5,
                                 help="Ví dụ lấy 5 giây từ mỗi suộc: 6 suộc sẽ tạo ra video hoàn chỉnh 30 giây cực cuốn hút.")
            
        max_total_sec = st.slider("Tổng thời lượng tối đa video thành phẩm (giây):", min_value=10, max_value=180, value=60, step=5,
                                  help="TikTok Shorts tối ưu nhất ở khoảng 30 - 60 giây.")
        
        shuffle_clips = st.checkbox("🎲 Xáo trộn ngẫu nhiên thứ tự các suộc", value=False,
                                    help="Mỗi lần ghép sẽ cho ra thứ tự video ngẫu nhiên khác nhau.")
        
        smart_cut_toggle = st.checkbox(
            "🗣️ Cắt thông minh theo câu thoại (Smart Voice Cut)",
            value=True,
            help="Tự động phân tích sóng âm thanh của từng video gốc, tìm chính xác điểm hết câu / dứt lời của người nói để cắt, KHÔNG BAO GIỜ bị cắt ngang giữa chừng hay nuốt chữ!"
        )
        smooth_fade_toggle = st.checkbox(
            "✨ Khớp nối âm mượt mà (Anti-Popping Crossfade)",
            value=True,
            help="Tự động vuốt mượt âm thanh 0.06s đầu và cuối mỗi đoạn, chuyển cảnh êm ái như dựng phim chuyên nghiệp."
        )

    st.divider()
    
    col_m_audio, col_m_banner = st.columns([1, 1])
    with col_m_audio:
        st.write("##### 🎵 Âm thanh thành phẩm")
        audio_choice = st.radio(
            "Cấu hình âm thanh:",
            ["Giữ tiếng gốc của từng suộc", "Tắt hoàn toàn tiếng gốc (Chỉ dùng nhạc nền BGM)", "Giữ tiếng gốc + Lồng thêm nhạc nền BGM nhẹ (15%)"]
        )
        
        merge_bgm_file = st.file_uploader("Nhạc nền BGM lồng xuyên suốt video (.mp3, .wav):", type=["mp3", "wav", "m4a"], key="merge_bgm")
        merge_bgm_path = None
        if merge_bgm_file:
            temp_bgm_dir = os.path.join(get_scratch_dir(), "merge_bgm")
            os.makedirs(temp_bgm_dir, exist_ok=True)
            merge_bgm_path = os.path.join(temp_bgm_dir, merge_bgm_file.name)
            with open(merge_bgm_path, "wb") as f:
                f.write(merge_bgm_file.getbuffer())

    with col_m_banner:
        st.write("##### 🏷️ Tiêu đề Hook / Banner đỉnh video")
        merge_banner_text = st.text_input(
            "Tiêu đề nổi bật (Ví dụ: TOP MẸO ĐỈNH CAO | XEM NGAY):", 
            placeholder="Để trống nếu không cần chèn chữ",
            key="merge_banner"
        )
        default_merge_out = r"D:\Download\TikTok_Merged_Videos" if os.path.exists(r"D:\Download") else os.path.join(get_scratch_dir(), "TikTok_Merged_Videos")
        merge_out_dir = st.text_input("Thư mục lưu video thành phẩm:", value=default_merge_out)

    st.divider()

    if selected_merge_paths:
        st.write(f"📋 **Danh sách {len(selected_merge_paths)} suộc đã chọn:**")
        with st.expander("👁️ Xem chi tiết các suộc đã chọn", expanded=True):
            for i, p in enumerate(selected_merge_paths, 1):
                st.caption(f"{i}. `{os.path.basename(p)}` ({round(os.path.getsize(p)/(1024*1024), 2)} MB)")

        start_merge_btn = st.button("🚀 BẮT ĐẦU GHÉP & XÀO NẤU THÀNH 1 VIDEO HOÀN CHỈNH", use_container_width=True)
        
        if start_merge_btn:
            if not ffmpeg_ready:
                st.error("FFmpeg chưa sẵn sàng!")
            else:
                os.makedirs(merge_out_dir, exist_ok=True)
                final_out_file = os.path.join(merge_out_dir, f"merged_{int(time.time())}_{len(selected_merge_paths)}clips.mp4")
                
                merge_progress = st.progress(0, text="Bắt đầu quá trình ghép nối các suộc video...")
                merge_status = st.empty()
                start_merge_time = time.time()
                
                def on_merge_prog(pct, msg):
                    merge_progress.progress(pct, text=msg)
                    merge_status.info(f"⏳ {msg}")
                    
                keep_orig = (audio_choice != "Tắt hoàn toàn tiếng gốc (Chỉ dùng nhạc nền BGM)")
                
                try:
                    res_path = merge_multiple_videos(
                        video_paths=selected_merge_paths,
                        output_path=final_out_file,
                        clip_duration=clip_sec,
                        max_total_duration=float(max_total_sec),
                        shuffle=shuffle_clips,
                        cut_head=cut_head,
                        cut_tail=cut_tail,
                        speed=speed,
                        zoom=zoom,
                        flip_h=flip_h,
                        contrast=contrast,
                        brightness=brightness,
                        saturation=saturation,
                        add_noise=(noise_intensity > 0),
                        noise_intensity=noise_intensity,
                        pitch_shift=pitch_shift,
                        keep_original_audio=keep_orig,
                        bgm_path=merge_bgm_path,
                        bgm_volume=0.20 if audio_choice == "Giữ tiếng gốc + Lồng thêm nhạc nền BGM nhẹ (15%)" else 0.8,
                        banner_text=merge_banner_text,
                        smart_voice_cut=smart_cut_toggle,
                        smooth_audio_fade=smooth_fade_toggle,
                        engine_mode=engine_choice,
                        on_progress=on_merge_prog
                    )
                    
                    merge_duration_total = round(time.time() - start_merge_time, 1)
                    merge_progress.progress(1.0, text=f"Hoàn thành trong {merge_duration_total}s!")
                    merge_status.success(f"🎉 Ghép thành công {len(selected_merge_paths)} suộc thành 1 video duy nhất trong {merge_duration_total}s!")
                    st.balloons()
                    
                    col_res1, col_res2 = st.columns([1.5, 1])
                    with col_res1:
                        st.write("##### 📺 Video thành phẩm:")
                        st.video(res_path)
                    with col_res2:
                        res_info = probe_video(res_path)
                        st.write("##### 📊 Thông số video:")
                        st.metric("Tổng thời lượng", f"{res_info['duration']:.1f} s")
                        st.metric("Độ phân giải chuẩn", f"{res_info['width']} x {res_info['height']} (9:16)")
                        st.metric("Dung lượng file", f"{res_info['size_mb']} MB")
                        st.info(f"📁 Đã lưu tại: `{res_path}`")
                        
                        with open(res_path, "rb") as mf:
                            st.download_button(
                                label="⬇️ Tải video thành phẩm về máy",
                                data=mf,
                                file_name=os.path.basename(res_path),
                                mime="video/mp4"
                            )
                        st.info("💡 **Gợi ý tiếp theo:** Chuyển ngay sang tab **🎙️ Tạo Text & Voice AI** bên trên để lồng tiếng thuyết minh và phụ đề tự động cho video này!")
                except Exception as ex:
                    merge_status.error(f"❌ Xảy ra lỗi khi ghép video: {str(ex)}")
    else:
        st.info("👆 Vui lòng chọn ít nhất 2 suộc video ở trên để bắt đầu ghép.")

# ----------------- TAB 2: AI VOICEOVER & SUBTITLES -----------------
with tab_voice:
    st.write("### 🎙️ Tự tạo Kịch bản, Giọng đọc AI & Phụ đề cho Video thành phẩm")
    st.markdown("Chọn video thành phẩm vừa tạo (hoặc video có sẵn), hệ thống sẽ **tự động sinh kịch bản thuyết minh, chuyển thành giọng đọc AI tự nhiên (Hoài My / Nam Minh) và chèn phụ đề chữ chạy** lên video.")
    
    col_v_in1, col_v_in2 = st.columns([1.2, 1])
    with col_v_in1:
        voice_video_src = st.radio(
            "Nguồn video cần lồng tiếng:",
            ["Từ thư mục video thành phẩm", "Tải video lên từ máy tính", "Đường dẫn thư mục máy tính"],
            horizontal=True,
            key="v_src_mode"
        )
        
        target_video_for_voice = None
        if voice_video_src == "Từ thư mục video thành phẩm":
            check_dirs = [
                r"D:\Download\TikTok_Merged_Videos",
                r"D:\Download\TikTok_Remixed",
                r"D:\Download\TikTok_Remixed_Batch",
                r"D:\Download"
            ]
            merged_dir = next((d for d in check_dirs if os.path.exists(d)), r"D:\Download")
            found_vids = glob.glob(os.path.join(merged_dir, "*.mp4")) + glob.glob(os.path.join(merged_dir, "*.mov"))
            found_vids.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            if found_vids:
                chosen_v = st.selectbox(
                    f"Chọn video thành phẩm ({len(found_vids)} video tìm thấy):",
                    options=found_vids,
                    format_func=lambda x: f"{os.path.basename(x)} ({round(os.path.getsize(x)/(1024*1024), 1)} MB)",
                    key="voice_target_select"
                )
                target_video_for_voice = chosen_v
            else:
                st.warning("Chưa có video thành phẩm nào trong thư mục này.")
        elif voice_video_src == "Tải video lên từ máy tính":
            uploaded_v = st.file_uploader("Chọn video cần lồng tiếng:", type=["mp4", "mov"], key="up_for_voice")
            if uploaded_v:
                t_dir = os.path.join(get_scratch_dir(), "voice_uploads")
                os.makedirs(t_dir, exist_ok=True)
                target_video_for_voice = os.path.join(t_dir, uploaded_v.name)
                with open(target_video_for_voice, "wb") as f:
                    f.write(uploaded_v.getbuffer())
        else:
            custom_path = st.text_input("Đường dẫn file video:", value=r"D:\Download", key="custom_v_path")
            if os.path.isfile(custom_path):
                target_video_for_voice = custom_path

    with col_v_in2:
        if target_video_for_voice and os.path.exists(target_video_for_voice):
            v_info = probe_video(target_video_for_voice)
            st.metric("Thời lượng video", f"{v_info['duration']:.1f} giây")
            st.video(target_video_for_voice)
        else:
            st.info("👆 Hãy chọn một video ở bên trái để xem trước.")

    st.divider()

    # SCRIPT GENERATOR SECTION
    st.subheader("📝 1. Kịch bản thuyết minh (Script)")
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        template_choice = st.selectbox(
            "Chọn mẫu kịch bản TikTok gợi ý:",
            options=list(SCRIPT_TEMPLATES.keys()),
            format_func=lambda x: SCRIPT_TEMPLATES[x]["title"]
        )
        if st.button("📋 Sử dụng mẫu kịch bản này"):
            st.session_state["script_text"] = SCRIPT_TEMPLATES[template_choice]["text"]
            
    with col_s2:
        default_script = st.session_state.get("script_text", SCRIPT_TEMPLATES["skincare"]["text"])
        user_script = st.text_area(
            "Nội dung giọng đọc AI (Bạn có thể tự do gõ, sửa, dán theo ý thích):",
            value=default_script,
            height=120,
            key="user_script_input"
        )
        word_count = len(user_script.split())
        est_seconds = round(word_count / 3.0, 1)
        st.caption(f"📊 Độ dài: **{word_count} từ** | Dự kiến thời gian đọc: **~{est_seconds} giây**")

    st.divider()

    # VOICE SELECTION & PREVIEW
    st.subheader("🎙️ 2. Cài đặt Giọng đọc AI & Nghe thử")
    col_voice1, col_voice2, col_voice3 = st.columns([1.5, 1, 1])
    with col_voice1:
        voice_actor = st.selectbox(
            "Chọn Giọng đọc AI:",
            options=list(VOICE_OPTIONS.keys()),
            format_func=lambda x: VOICE_OPTIONS[x]
        )
    with col_voice2:
        voice_rate = st.selectbox(
            "Tốc độ đọc:",
            options=["+0%", "+10%", "+20%", "-10%"],
            format_func=lambda x: {
                "+0%": "Bình thường (1.0x)",
                "+10%": "Nhanh hơn (+10% - Chuẩn TikTok)",
                "+20%": "Rất nhanh (+20%)",
                "-10%": "Chậm hơn (-10%)"
            }[x],
            index=1
        )
    with col_voice3:
        st.write("")
        st.write("")
        preview_voice_btn = st.button("🔊 Nghe thử giọng đọc trước", use_container_width=True)

    if preview_voice_btn:
        if not user_script or not user_script.strip():
            st.warning("Vui lòng nhập kịch bản trước khi nghe thử!")
        else:
            with st.spinner("Đang tạo giọng đọc AI nghe thử..."):
                preview_audio_file = os.path.join(get_scratch_dir(), "preview_voice.mp3")
                try:
                    generate_voiceover(
                        text=user_script,
                        output_audio_path=preview_audio_file,
                        voice=voice_actor,
                        rate=voice_rate
                    )
                    st.success("✅ Đã tạo xong giọng đọc thử!")
                    st.audio(preview_audio_file)
                except Exception as ex_v:
                    st.error(f"Lỗi: {str(ex_v)}")

    st.divider()

    # SUBTITLES & AUDIO MIXING
    st.subheader("🎨 3. Phụ đề & Hòa âm nhạc nền")
    col_sub1, col_sub2 = st.columns([1, 1])
    with col_sub1:
        enable_subtitles = st.checkbox("Chèn phụ đề chữ nổi bật trên video (TikTok Subtitles)", value=True,
                                       help="Chữ vàng viền đen to rõ, hiển thị ở 1/3 dưới màn hình chuẩn phong cách TikTok Shorts.")
    with col_sub2:
        voice_bgm = st.file_uploader("Nhạc nền BGM lồng nhẹ dưới giọng đọc (Tùy chọn):", type=["mp3", "wav"], key="voice_bgm_up")
        v_bgm_path = None
        if voice_bgm:
            temp_bgm_d = os.path.join(get_scratch_dir(), "voice_bgm")
            os.makedirs(temp_bgm_d, exist_ok=True)
            v_bgm_path = os.path.join(temp_bgm_d, voice_bgm.name)
            with open(v_bgm_path, "wb") as bf:
                bf.write(voice_bgm.getbuffer())

    # RENDER BUTTON
    st.divider()
    render_voiceover_btn = st.button("🚀 BẮT ĐẦU LỒNG GIỌNG ĐỌC AI & PHỤ ĐỀ VÀO VIDEO", use_container_width=True)
    
    if render_voiceover_btn:
        if not target_video_for_voice or not os.path.exists(target_video_for_voice):
            st.error("Vui lòng chọn video thành phẩm hợp lệ!")
        elif not user_script or not user_script.strip():
            st.error("Vui lòng nhập nội dung kịch bản thuyết minh!")
        else:
            v_progress = st.progress(0, text="Đang tạo file giọng đọc AI...")
            start_v_time = time.time()
            
            scratch_root = get_scratch_dir()
            tts_speech_file = os.path.join(scratch_root, f"speech_{int(time.time())}.mp3")
            out_final_voice_video = os.path.join(
                os.path.dirname(target_video_for_voice),
                f"voiced_{int(time.time())}_{os.path.basename(target_video_for_voice)}"
            )
            
            try:
                generate_voiceover(
                    text=user_script,
                    output_audio_path=tts_speech_file,
                    voice=voice_actor,
                    rate=voice_rate
                )
                v_progress.progress(0.4, text="Đang hòa âm & chèn phụ đề vào video bằng GPU...")
                
                final_v_path = apply_voiceover_to_video(
                    video_path=target_video_for_voice,
                    voice_audio_path=tts_speech_file,
                    output_path=out_final_voice_video,
                    subtitle_text=user_script if enable_subtitles else None,
                    bgm_path=v_bgm_path,
                    bgm_volume=0.15,
                    voice_volume=1.0,
                    engine_mode=engine_choice
                )
                
                v_total_sec = round(time.time() - start_v_time, 1)
                v_progress.progress(1.0, text=f"Hoàn thành siêu tốc trong {v_total_sec}s!")
                st.success(f"🎉 Đã lồng giọng đọc AI và phụ đề thành công vào video trong {v_total_sec} giây!")
                st.balloons()
                
                col_fin1, col_fin2 = st.columns([1.5, 1])
                with col_fin1:
                    st.write("##### 📺 Video thành phẩm có Thuyết minh & Phụ đề:")
                    st.video(final_v_path)
                with col_fin2:
                    fin_info = probe_video(final_v_path)
                    st.write("##### 📊 Chi tiết video:")
                    st.metric("Thời lượng", f"{fin_info['duration']:.1f} s")
                    st.metric("Dung lượng", f"{fin_info['size_mb']} MB")
                    st.info(f"📁 Đã lưu tại: `{final_v_path}`")
                    
                    with open(final_v_path, "rb") as ff:
                        st.download_button(
                            label="⬇️ Tải video thuyết minh về máy",
                            data=ff,
                            file_name=os.path.basename(final_v_path),
                            mime="video/mp4"
                        )
            except Exception as err_v:
                st.error(f"❌ Xảy ra lỗi khi lồng tiếng: {str(err_v)}")

# ----------------- TAB 3: SINGLE VIDEO -----------------
with tab_single:
    st.write("### 🎬 Biên tập và Xem trước từng Video")
    
    col_input1, col_input2 = st.columns([1, 1])
    
    input_mode = col_input1.radio("Cách chọn video:", ["Chọn từ thư mục máy tính (D:\\Download)", "Tải file lên (Upload)"], horizontal=True, key="single_mode")
    
    selected_video_path = None
    
    if input_mode == "Chọn từ thư mục máy tính (D:\\Download)":
        scan_folder = col_input1.text_input("Đường dẫn thư mục chứa video:", value=r"D:\Download", key="single_folder")
        if os.path.exists(scan_folder):
            video_extensions = ("*.mp4", "*.mov", "*.mkv", "*.webm")
            found_files = []
            for ext in video_extensions:
                found_files.extend(glob.glob(os.path.join(scan_folder, ext)))
                
            if found_files:
                selected_video_name = col_input1.selectbox(
                    f"Chọn video từ {len(found_files)} video tìm thấy:",
                    options=[os.path.basename(f) for f in found_files],
                    key="single_select"
                )
                selected_video_path = os.path.join(scan_folder, selected_video_name)
            else:
                col_input1.warning("Không tìm thấy video nào (.mp4, .mov, .mkv) trong thư mục này.")
        else:
            col_input1.error("Thư mục không tồn tại!")
    else:
        uploaded_file = col_input1.file_uploader("Kéo thả hoặc tải lên video MP4/MOV:", type=["mp4", "mov", "mkv"], key="single_up")
        if uploaded_file is not None:
            temp_dir = os.path.join(get_scratch_dir(), "temp_uploads")
            os.makedirs(temp_dir, exist_ok=True)
            temp_save_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            selected_video_path = temp_save_path

    # BGM selection
    bgm_file = col_input2.file_uploader("Thêm nhạc nền BGM (Tùy chọn - .mp3, .wav, .m4a):", type=["mp3", "wav", "m4a"], key="single_bgm")
    bgm_path = None
    if bgm_file:
        temp_bgm_dir = os.path.join(get_scratch_dir(), "temp_bgm")
        os.makedirs(temp_bgm_dir, exist_ok=True)
        bgm_path = os.path.join(temp_bgm_dir, bgm_file.name)
        with open(bgm_path, "wb") as f:
            f.write(bgm_file.getbuffer())
        col_input2.success(f"Đã nạp nhạc nền: {bgm_file.name}")

    single_banner_text = col_input2.text_input("Tiêu đề nổi bật đỉnh video:", placeholder="Ví dụ: XEM ĐẾN CUỐI NHA...", key="single_banner")

    st.divider()

    if selected_video_path and os.path.exists(selected_video_path):
        try:
            info = probe_video(selected_video_path)
            
            # Display video metadata
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            col_m1.metric("Thời lượng", f"{info['duration']:.1f} s")
            col_m2.metric("Độ phân giải", f"{info['width']} x {info['height']}")
            col_m3.metric("Tốc độ khung hình", f"{info['fps']} fps")
            col_m4.metric("Dung lượng", f"{info['size_mb']} MB")
            col_m5.metric("Âm thanh", "Có âm thanh" if info['has_audio'] else "Không có")
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.write("**Video gốc:**")
                st.video(selected_video_path)
                
            with col_v2:
                st.write("**Video sau khi xào nấu:**")
                render_btn = st.button("🚀 Bắt đầu xào nấu video này", use_container_width=True, key="single_btn")
                
                output_dir = os.path.join(os.path.dirname(selected_video_path), "TikTok_Remixed")
                os.makedirs(output_dir, exist_ok=True)
                output_filename = f"remixed_{int(time.time())}_{os.path.basename(selected_video_path)}"
                output_file_path = os.path.join(output_dir, output_filename)
                
                if render_btn:
                    if not ffmpeg_ready:
                        st.error("FFmpeg chưa sẵn sàng!")
                    else:
                        progress_bar = st.progress(0, text="Đang xử lý video với FFmpeg...")
                        try:
                            start_render_time = time.time()
                            
                            def update_progress(val, text):
                                progress_bar.progress(val, text=text)
                                
                            out_path = process_video(
                                input_path=selected_video_path,
                                output_path=output_file_path,
                                speed=speed,
                                zoom=zoom,
                                flip_h=flip_h,
                                contrast=contrast,
                                brightness=brightness,
                                saturation=saturation,
                                add_noise=(noise_intensity > 0),
                                noise_intensity=noise_intensity,
                                add_vignette=add_vignette,
                                pitch_shift=pitch_shift,
                                bgm_path=bgm_path,
                                bgm_volume=0.15,
                                original_audio_vol=1.0,
                                remove_audio=False,
                                cut_head=cut_head,
                                cut_tail=cut_tail,
                                target_aspect="9:16",
                                banner_text=single_banner_text,
                                engine_mode=engine_choice,
                                on_progress=update_progress
                            )
                            
                            elapsed = round(time.time() - start_render_time, 2)
                            progress_bar.progress(1.0, text=f"Xong trong {elapsed} giây!")
                            st.success(f"✅ Đã xử lý xong video trong {elapsed}s!")
                            st.video(out_path)
                            st.info(f"📁 Video đã lưu tại: `{out_path}`")
                            
                            with open(out_path, "rb") as vf:
                                st.download_button(
                                    label="⬇️ Tải video remixed về máy",
                                    data=vf,
                                    file_name=output_filename,
                                    mime="video/mp4"
                                )
                        except Exception as err:
                            st.error(f"❌ Xảy ra lỗi khi xử lý: {str(err)}")
                            
        except Exception as e:
            st.error(f"Lỗi đọc thông tin video: {str(e)}")

# ----------------- TAB 3: BATCH PROCESSING -----------------
with tab_batch:
    st.write("### 📁 Xử lý tự động hàng loạt toàn bộ thư mục video")
    st.write("Tự động quét toàn bộ thư mục video, áp dụng công thức xào nấu né bản quyền và xuất ra thư mục mới.")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        batch_input_dir = st.text_input("Thư mục chứa video gốc cần xào:", value=r"D:\Download", key="batch_in")
    with col_b2:
        default_out = os.path.join(batch_input_dir, "TikTok_Remixed_Batch") if batch_input_dir else ""
        batch_output_dir = st.text_input("Thư mục lưu video thành phẩm:", value=default_out, key="batch_out")
        
    randomize_parameters = st.checkbox(
        "🎲 Ngẫu nhiên hóa nhẹ từng video (Micro-Randomization)",
        value=True,
        help="Mỗi video sẽ có thông số zoom (1.04-1.07), tốc độ (1.02-1.05), độ tương phản hơi khác nhau 1 chút để không video nào có cấu trúc giống hệt video nào!"
    )

    if os.path.exists(batch_input_dir):
        exts = ("*.mp4", "*.mov", "*.mkv")
        batch_files = []
        for e in exts:
            batch_files.extend(glob.glob(os.path.join(batch_input_dir, e)))
            
        st.write(f"📊 Tìm thấy **{len(batch_files)}** video trong thư mục:")
        
        with st.expander("👁️ Xem danh sách video đã tìm thấy", expanded=False):
            for i, f in enumerate(batch_files[:50], 1):
                st.write(f"{i}. `{os.path.basename(f)}` ({round(os.path.getsize(f)/(1024*1024), 1)} MB)")
            if len(batch_files) > 50:
                st.caption(f"... và còn {len(batch_files)-50} video khác.")

        start_batch_btn = st.button("🚀 BẮT ĐẦU XÀO NẤU HÀNG LOẠT", use_container_width=True, key="batch_btn")
        
        if start_batch_btn:
            if not batch_files:
                st.warning("Không có video nào để xử lý!")
            else:
                os.makedirs(batch_output_dir, exist_ok=True)
                total_count = len(batch_files)
                batch_progress = st.progress(0, text=f"Đang chuẩn bị xử lý {total_count} video...")
                
                status_box = st.empty()
                success_count = 0
                start_total_time = time.time()
                
                for idx, file_path in enumerate(batch_files):
                    fname = os.path.basename(file_path)
                    status_box.info(f"⏳ Đang xử lý video ({idx+1}/{total_count}): **{fname}**")
                    
                    cur_speed = speed + (random.uniform(-0.015, 0.015) if randomize_parameters else 0.0)
                    cur_zoom = zoom + (random.uniform(-0.01, 0.02) if randomize_parameters else 0.0)
                    cur_contrast = contrast + (random.uniform(-0.02, 0.02) if randomize_parameters else 0.0)
                    cur_pitch = pitch_shift + (random.uniform(-0.01, 0.01) if randomize_parameters else 0.0)
                    
                    out_filename = f"remix_{idx+1:03d}_{fname}"
                    out_path = os.path.join(batch_output_dir, out_filename)
                    
                    try:
                        process_video(
                            input_path=file_path,
                            output_path=out_path,
                            speed=cur_speed,
                            zoom=cur_zoom,
                            flip_h=flip_h,
                            contrast=cur_contrast,
                            brightness=brightness,
                            saturation=saturation,
                            add_noise=(noise_intensity > 0),
                            noise_intensity=noise_intensity,
                            add_vignette=add_vignette,
                            pitch_shift=cur_pitch,
                            remove_audio=False,
                            cut_head=cut_head,
                            cut_tail=cut_tail,
                            target_aspect="9:16",
                            engine_mode=engine_choice
                        )
                        success_count += 1
                    except Exception as err:
                        st.error(f"Lỗi video {fname}: {str(err)}")
                        
                    batch_progress.progress((idx + 1) / total_count, text=f"Đã xử lý {idx+1}/{total_count} video...")
                    
                total_duration = round(time.time() - start_total_time, 1)
                status_box.success(f"🎉 Hoàn thành xuất sắc! Đã xào nấu thành công {success_count}/{total_count} video trong {total_duration}s.")
                st.balloons()
                st.info(f"📁 Toàn bộ video đã được lưu vào thư mục: `{batch_output_dir}`")
    else:
        st.error("Thư mục nguồn không tồn tại. Vui lòng kiểm tra lại đường dẫn!")

# ----------------- TAB 4: GUIDE -----------------
with tab_guide:
    st.write("### 💡 Cẩm nang cơ chế quét bản quyền TikTok & Chiến thuật né 2026")
    
    st.markdown("""
    #### 1. Tại sao kỹ thuật ghép nhiều suộc (Mashup/Compilation) lại né bản quyền tốt nhất?
    - **Phá vỡ Keyframe Timeline:** Khi bạn ghép nhiều đoạn cắt 3 - 6 giây từ các video khác nhau, AI của TikTok không thể tìm thấy bất kỳ chuỗi keyframe dài nào khớp với video gốc ban đầu.
    - **Thuật toán TikTok đánh giá đây là 'Nội dung sáng tạo tổng hợp' (Fair Use / Transformative Content):** Video tổng hợp có giá trị thông tin cao hơn rất nhiều so với reup nguyên 1 clip.
    - **Tỷ lệ giữ chân người xem (Retention rate) cực cao:** Chuyển cảnh nhanh mỗi 3-5 giây khiến người xem không bị nhàm chán, xem hết video và thả tim nhiều hơn.

    #### 2. Các tầng bảo vệ tự động của Tool:
    - **MD5 / Binary Hash:** Tái mã hóa bitexact, làm sạch 100% metadata.
    - **Visual Fingerprint:** Zoom, Crop 9:16 chuẩn TikTok (1080x1920), phủ Noise vi hạt và chỉnh tone màu.
    - **Audio Hash:** Đổi Pitch Shift cao độ hoặc lồng 1 bản nhạc BGM xu hướng xuyên suốt.
    - **Logo / Watermark OCR:** Tự động cắt bỏ 0.5s đầu và đuôi của từng clip để lọc sạch logo TikTok/CapCut.
    """)
