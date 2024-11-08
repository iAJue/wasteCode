import subprocess
import os

def concatenate_videos(output_filename, segment_directory):
    # 获取指定目录下所有视频片段文件
    segment_files = sorted([os.path.join(segment_directory, f) for f in os.listdir(segment_directory) if f.endswith('.mp4')])

    if not segment_files:
        print("No video files found in the directory.")
        return

    # 使用 ffmpeg concat 协议拼接视频
    command = ['ffmpeg']

    # 为每个视频片段添加 -i 参数
    for segment_file in segment_files:
        command.extend(['-i', segment_file])

    # 添加 concat 指令，明确指定视频编解码器
    command.extend([
        '-filter_complex', f"concat=n={len(segment_files)}:v=1:a=0",  # 拼接视频，不包括音频
        '-c:v', 'libx264',  # 使用H.264编解码器进行视频编码
        '-crf', '23',  # 设置CRF（恒定质量）参数，数值越低质量越高
        '-preset', 'fast',  # 使用较快的预设，保持良好的质量和编码速度平衡
        '-movflags', '+faststart',  # 优化用于网络传输的视频播放
        output_filename  # 输出文件名
    ])

    try:
        subprocess.run(command, check=True)
        print(f"Successfully concatenated videos into {output_filename}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")

# 使用示例：
segment_directory = 'output_temp'  # 视频片段所在的目录
output_video = 'final_output.mp4'

concatenate_videos(output_video, segment_directory)