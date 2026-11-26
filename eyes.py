"""
EYES — video analyzer for Claude
Extracts key frames from a video so Claude can "see" them

Usage:
  py eyes.py <path_to_video> [number_of_frames]

Result:
  - A folder with frames (PNG)
  - A text report about the video (duration, resolution, FPS)
"""

import sys
import os
import cv2
import json
from pathlib import Path
from datetime import timedelta


def extract_key_frames(video_path, num_frames=8, output_dir=None):
    """Extract key frames from a video"""

    video_path = Path(video_path)
    if not video_path.exists():
        print(f"ОШИБКА: Файл не найден: {video_path}")
        return None

    # Folder for frames
    if output_dir is None:
        output_dir = video_path.parent / f"{video_path.stem}_frames"
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Open the video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"ОШИБКА: Не удалось открыть видео: {video_path}")
        return None

    # Video metadata
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps if fps > 0 else 0
    duration = str(timedelta(seconds=int(duration_sec)))

    info = {
        "file": str(video_path),
        "file_size_mb": round(video_path.stat().st_size / (1024*1024), 1),
        "resolution": f"{width}x{height}",
        "fps": round(fps, 1),
        "total_frames": total_frames,
        "duration": duration,
        "duration_seconds": round(duration_sec, 1),
        "extracted_frames": num_frames,
        "frames": []
    }

    print(f"Видео: {video_path.name}")
    print(f"  Разрешение: {width}x{height}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Длительность: {duration}")
    print(f"  Всего кадров: {total_frames}")
    print(f"  Извлекаю {num_frames} ключевых кадров...")
    print()

    # Distribute frames evenly across the video
    if num_frames >= total_frames:
        frame_indices = list(range(total_frames))
    else:
        # Skip the very beginning and end (usually black)
        start = int(total_frames * 0.02)
        end = int(total_frames * 0.98)
        step = (end - start) / (num_frames - 1) if num_frames > 1 else 0
        frame_indices = [int(start + i * step) for i in range(num_frames)]

    # Extract frames
    for i, frame_idx in enumerate(frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()

        if not ret:
            continue

        # Time of this frame
        time_sec = frame_idx / fps if fps > 0 else 0
        time_str = str(timedelta(seconds=int(time_sec)))

        # Save the frame
        frame_name = f"frame_{i+1:02d}_{time_str.replace(':', '-')}.png"
        frame_path = output_dir / frame_name

        # Shrink to a reasonable size for viewing
        max_dim = 1280
        h, w = frame.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            frame = cv2.resize(frame, (int(w*scale), int(h*scale)))

        # cv2.imwrite does not work with Cyrillic — use numpy+Pillow
        import numpy as np
        from PIL import Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Image.fromarray(rgb_frame).save(str(frame_path))

        frame_info = {
            "index": i + 1,
            "file": frame_name,
            "path": str(frame_path),
            "time": time_str,
            "time_seconds": round(time_sec, 1),
            "original_frame": frame_idx
        }
        info["frames"].append(frame_info)

        print(f"  Кадр {i+1}/{num_frames}: {time_str} -> {frame_name}")

    cap.release()

    # Save the report
    report_path = output_dir / "video_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    # Text report for Claude
    txt_report_path = output_dir / "video_report.txt"
    with open(txt_report_path, 'w', encoding='utf-8') as f:
        f.write(f"=== ВИДЕО-АНАЛИЗ: {video_path.name} ===\n\n")
        f.write(f"Файл: {video_path}\n")
        f.write(f"Размер: {info['file_size_mb']} МБ\n")
        f.write(f"Разрешение: {info['resolution']}\n")
        f.write(f"FPS: {info['fps']}\n")
        f.write(f"Длительность: {info['duration']}\n\n")
        f.write(f"Извлечено кадров: {len(info['frames'])}\n")
        f.write(f"Папка кадров: {output_dir}\n\n")
        f.write("Кадры:\n")
        for fr in info["frames"]:
            f.write(f"  [{fr['index']}] {fr['time']} -> {fr['path']}\n")
        f.write(f"\nДля просмотра: Claude может прочитать каждый PNG файл\n")

    print(f"\nГотово! Кадры в папке: {output_dir}")
    print(f"Отчёт: {report_path}")

    return info


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: py eyes.py <видео_файл> [кол-во_кадров]")
        print("Пример: py eyes.py video.mp4 10")
        sys.exit(1)

    video_file = sys.argv[1]
    num = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    extract_key_frames(video_file, num)
