import subprocess
import os

def extract_frames(video_path):
    # 获取视频文件名和目录
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.join(os.path.dirname(video_path), video_name)

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 获取视频时长
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    duration = float(result.stdout.strip())

    # 提取每秒中间的帧
    for i in range(int(duration)):
        timestamp = i + 0.5  # 中间的帧
        output_image_path = os.path.join(output_dir, f'frame_{i+1:04d}.png')
        command = [
            'ffmpeg',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            output_image_path
        ]
        subprocess.run(command)

# 示例视频路径
video_path = './output_segments/segment_1.mp4'  # 替换为你的视频路径

# 调用函数提取帧
extract_frames(video_path)