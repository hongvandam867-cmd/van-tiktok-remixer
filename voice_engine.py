import os
import sys
import shutil
import subprocess
import tempfile
import time
from typing import Optional, List, Dict

def get_edge_tts_bin() -> list:
    """Returns executable command for edge-tts (cross-platform)."""
    win_path = r"C:\Users\Admin\.gemini\antigravity\scratch\tools\python\Scripts\edge-tts.exe"
    if os.path.exists(win_path):
        return [win_path]
    system_bin = shutil.which("edge-tts")
    if system_bin:
        return [system_bin]
    return [sys.executable, "-m", "edge_tts"]

def get_ffmpeg_bin() -> str:
    """Returns executable path for ffmpeg (cross-platform)."""
    win_path = r"C:\Users\Admin\.gemini\antigravity\scratch\tools\ffmpeg\ffmpeg.exe"
    if os.path.exists(win_path):
        return win_path
    system_bin = shutil.which("ffmpeg")
    if system_bin:
        return system_bin
    return "ffmpeg"

VOICE_OPTIONS = {
    "vi-VN-HoaiMyNeural": "👩 Nữ - Hoài My (Giọng Review TikTok / Bán hàng / Năng động)",
    "vi-VN-NamMinhNeural": "👨 Nam - Nam Minh (Giọng Kể chuyện / Tin tức / Trầm ấm)"
}

SCRIPT_TEMPLATES = {
    "skincare": {
        "title": "🧴 Review Mỹ phẩm / Skincare",
        "text": "Đừng lướt qua nếu da bạn đang bị mụn và nhạy cảm! Đây là dòng kem dưỡng cứu cánh cho làn da đang cực hot trên TikTok, giúp làm dịu da tức thì và cấp ẩm chuyên sâu. Hãy thử ngay để cảm nhận sự thay đổi rõ rệt nhé!"
    },
    "tips": {
        "title": "💡 Mẹo hay / Bí quyết cuộc sống",
        "text": "Bí quyết cực hay mà 90% mọi người đều chưa biết! Xem ngay để không bỏ lỡ những tuyệt chiêu đỉnh cao này nha. Đừng quên thả tim và lưu video lại khi cần áp dụng!"
    },
    "mystery": {
        "title": "🔥 Kể chuyện tò mò / Hook giữ chân",
        "text": "Bạn có tin vào điều này không? Thứ mà bạn sắp thấy ngay sau đây sẽ khiến bạn phải bất ngờ đến ngỡ ngàng. Hãy xem thật kỹ đến giây cuối cùng để biết sự thật nhé!"
    },
    "sale": {
        "title": "🏷️ Giảm giá sốc / Khuyến mãi",
        "text": "Deal hời duy nhất hôm nay dành cho các tín đồ săn sale! Sản phẩm chính hãng giá cực sốc chưa từng có. Nhanh tay chốt đơn ngay trước khi hết hàng nha mọi người ơi!"
    }
}

def generate_voiceover(
    text: str,
    output_audio_path: str,
    voice: str = "vi-VN-HoaiMyNeural",
    rate: str = "+0%"
) -> str:
    """
    Generates natural Vietnamese speech from text using Edge-TTS.
    """
    if not text or not text.strip():
        raise ValueError("Văn bản kịch bản trống!")
        
    scratch_dir = tempfile.gettempdir()
    temp_txt = os.path.join(scratch_dir, f"tts_{int(time.time())}.txt")
    with open(temp_txt, "w", encoding="utf-8-sig") as f:
        f.write(text.strip())
        
    cmd = list(get_edge_tts_bin()) + [
        "--file", temp_txt,
        "--voice", voice,
        "--write-media", output_audio_path
    ]
    if rate and rate != "+0%":
        cmd.extend(["--rate", rate])
        
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0 or not os.path.exists(output_audio_path):
            raise RuntimeError(f"Lỗi tạo giọng đọc: {res.stderr}")
        return output_audio_path
    finally:
        if os.path.exists(temp_txt):
            os.remove(temp_txt)

def apply_voiceover_to_video(
    video_path: str,
    voice_audio_path: str,
    output_path: str,
    subtitle_text: Optional[str] = None,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.15,
    voice_volume: float = 1.0,
    engine_mode: str = "ultrafast"
) -> str:
    """
    Overlays AI voiceover, optional background music, and TikTok-style subtitles onto the video.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Không tìm thấy video: {video_path}")
    if not os.path.exists(voice_audio_path):
        raise FileNotFoundError(f"Không tìm thấy file giọng đọc: {voice_audio_path}")
        
    ffmpeg_bin = get_ffmpeg_bin()
    cmd = [ffmpeg_bin, "-y", "-i", video_path, "-i", voice_audio_path]
    
    has_bgm = bgm_path and os.path.exists(bgm_path)
    if has_bgm:
        cmd.extend(["-stream_loop", "-1", "-i", bgm_path])
        
    # Audio mixing (Audio ducking)
    if has_bgm:
        filter_complex_audio = (
            f"[1:a]volume={voice_volume:.2f}[v_ai];"
            f"[2:a]volume={bgm_volume:.2f}[bgm];"
            f"[v_ai][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    else:
        filter_complex_audio = f"[1:a]volume={voice_volume:.2f}[aout]"
        
    # Video filters (Subtitles / Captions)
    vf_list = []
    if subtitle_text and subtitle_text.strip():
        # Clean text for drawtext
        clean_sub = subtitle_text.strip().replace(":", "\\:").replace("'", "\\'").replace('"', '')
        # Wrap into 2 lines if long
        words = clean_sub.split()
        if len(words) > 8:
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
            formatted_text = f"{line1}\n{line2}"
        else:
            formatted_text = clean_sub
            
        formatted_text = formatted_text.replace("\n", "\n")
        
        # TikTok style: Font size 48, yellow text, dark transparent outline box near bottom (y=h-480)
        vf_list.append(
            f"drawtext=font='Arial':text='{formatted_text}':fontcolor=yellow:fontsize=46:"
            f"box=1:boxcolor=black@0.65:boxborderw=18:line_spacing=12:x=(w-text_w)/2:y=h-460"
        )
        
    # If video filter is applied, re-encode video with GPU AMF or ultrafast
    if vf_list:
        cmd.extend(["-vf", ",".join(vf_list)])
        if engine_mode == "gpu_amf":
            cmd.extend(["-c:v", "h264_amf", "-quality", "speed"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-threads", "0"])
    else:
        # No video change: copy video stream directly (instant < 0.5s!)
        cmd.extend(["-c:v", "copy"])
        
    # Audio filter
    cmd.extend([
        "-filter_complex", filter_complex_audio,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-map_metadata", "-1",
        "-movflags", "+faststart",
        output_path
    ])
    
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if res.returncode != 0:
        raise RuntimeError(f"Lỗi khi lồng tiếng vào video: {res.stderr}")
        
    return output_path
