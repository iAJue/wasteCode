import os
import mysql.connector
import requests
from datetime import datetime
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv
import ffmpeg
load_dotenv()

# 配置数据库连接信息
db_config = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_DATABASE")
}

# 定义目标文件夹路径和文件大小限制
older_name = "Wallpaper 18+"
video_folder_path = '/Users/ajue/Documents/wasteCode/photo/视频/'
max_file_size = 15 * 1024 * 1024  # 18 MB in bytes
upload_url = os.getenv("UPLOAD_URL")
domain_prefix = os.getenv("DOMAIN_PREFIX")
enable_compression = False
attribute = 2
password = '123456'


def compress_video(input_file, output_file, target_bitrate='1M', resolution=None):
    """
    使用 ffmpeg-python 压缩视频，确保保留音频流或重新编码音频。
    :param input_file: 输入视频文件路径
    :param output_file: 输出视频文件路径
    :param target_bitrate: 目标比特率（例如 '1M', '500k'）
    :param resolution: 目标分辨率（例如 '1280x720'），默认为 None 保持原分辨率
    """
    try:
        # 输入文件
        stream = ffmpeg.input(input_file)

        # 调整分辨率（如果指定）
        if resolution:
            width, height = map(int, resolution.split('x'))
            stream = ffmpeg.filter(stream, 'scale', width, height)

        # 输出文件
        stream = ffmpeg.output(
            stream,
            output_file,
            video_bitrate=target_bitrate,  # 视频比特率
            audio_bitrate='128k',         # 音频比特率
            preset='medium',              # 压缩速度
            movflags='faststart',         # 提前移动元数据
            vcodec='libx264',             # 视频编码器
            acodec='aac',                 # 音频编码器
            strict='experimental'         # 兼容性选项
        )

        # 执行压缩
        ffmpeg.run(stream, overwrite_output=True)
        print(f"视频已成功压缩并保留音频，保存到 {output_file}")
        return output_file

    except ffmpeg.Error as e:
        error_message = e.stderr.decode() if e.stderr else str(e)
        print(f"视频压缩失败: {error_message}")
        return None

    except Exception as e:
        print(f"视频压缩过程中发生未知错误: {e}")
        return None
    
def get_file_size(file_path):
    """获取文件大小（字节为单位）"""
    size = os.path.getsize(file_path)
    print(f"文件 '{file_path}' 大小: {size / (1024 * 1024):.2f} MB")
    return size

def split_video(file_path, target_size):
    """根据目标大小分割视频并返回分割后的文件路径"""
    file_size = get_file_size(file_path)
    if file_size <= target_size:
        print(f"文件 '{file_path}' 不需要分割。")
        return [file_path]

    # 计算分割份数
    num_parts = (file_size // target_size) + 1
    duration = get_video_duration(file_path)
    part_duration = duration / num_parts
    print(f"文件 '{file_path}' 将被分割成 {num_parts} 段，每段时长: {part_duration:.2f} 秒")

    parts = []
    for i in range(num_parts):
        start_time = i * part_duration
        end_time = min((i + 1) * part_duration, duration)
        output_path = f"{file_path}_part_{i + 1}.mp4"
        print(f"正在创建分割文件: {output_path} ({start_time:.2f} 秒 到 {end_time:.2f} 秒)")
        ffmpeg_extract_subclip(file_path, start_time, end_time, targetname=output_path)
        parts.append(output_path)
    return parts

def get_video_duration(file_path):
    """获取视频时长（秒）"""
    with VideoFileClip(file_path) as video:
        duration = video.duration
    print(f"文件 '{file_path}' 总时长: {duration:.2f} 秒")
    return duration

def upload_video(file_path):
    """上传视频并返回带有前缀的 URL，替换 # 为 %23"""
    print(f"正在上传视频文件: {file_path}")
    try:
        with open(file_path, 'rb') as video_file:
            files = {'file': video_file}
            response = requests.post(upload_url, files=files)
            response_data = response.json()
            
            # 检查返回的数据结构
            if isinstance(response_data, list) and len(response_data) > 0 and 'src' in response_data[0]:
                video_url = response_data[0]['src'].replace('#', '%23')
                full_url = f"{domain_prefix}{video_url}"
                print(f"文件 '{file_path}' 上传成功, 获取到 URL: {full_url}")
                return full_url
            else:
                print(f"文件 '{file_path}' 上传失败，没有获得有效的 URL。")
    except Exception as e:
        print(f"文件 '{file_path}' 上传过程中发生错误: {e}")
    return None

def connect_database():
    """连接 MySQL 数据库"""
    print("连接数据库...")
    return mysql.connector.connect(**db_config)

def create_folder_if_not_exists(cursor, folder_name, attribute=0, password=None):
    """检查文件夹是否存在，存在则返回其 ID，否则创建新文件夹"""
    print(f"检查是否已存在文件夹 '{folder_name}'")
    cursor.execute("SELECT id FROM folders WHERE name = %s", (folder_name,))
    result = cursor.fetchone()

    if result:
        folder_id = result[0]
        print(f"文件夹 '{folder_name}' 已存在，ID: {folder_id}")
    else:
        print(f"文件夹 '{folder_name}' 不存在，正在创建...")
        cursor.execute(
            "INSERT INTO folders (name, attribute, password, created_at) "
            "VALUES (%s, %s, %s, %s)",
            (folder_name, attribute, password, datetime.now())
        )
        folder_id = cursor.lastrowid
        print(f"文件夹 '{folder_name}' 创建成功，ID: {folder_id}")
    
    return folder_id

def insert_file_record(cursor, folder_id, file_name, file_size, file_type, file_data, duration):
    """在数据库中插入文件记录，包括视频时长"""
    if file_type == 1:
        print(f"插入文件记录 '{file_name}' (大小: {file_size / (1024 * 1024):.2f} MB, 时长: {duration:.2f} 秒) 到文件夹 ID: {folder_id}")
    cursor.execute(
        "INSERT INTO files (folder_id, name, size, type, data, duration, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (folder_id, file_name, file_size, file_type, file_data, duration, datetime.now())
    )

def main():
    db = connect_database()
    cursor = db.cursor()

    # 检查或创建文件夹记录
    folder_id = create_folder_if_not_exists(cursor, older_name, attribute, password)
    db.commit()
    
    for root, _, files in os.walk(video_folder_path):
        for file in files:
            if file.startswith('.'):
                continue

            file_path = os.path.join(root, file)
            print(f"正在处理文件: {file_path}")
            file_size = get_file_size(file_path)

            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                file_url = upload_video(file_path)
                if file_url:
                    insert_file_record(cursor, folder_id, file, file_size, 0, file_url, None)
                    db.commit()
                    os.remove(file_path)
                    print(f"图片 '{file}' 上传并记录成功，已删除本地文件")
                else:
                    print(f"图片 '{file}' 上传失败，保留本地文件")
            else:
                duration = get_video_duration(file_path)

                # 如果启用压缩，则先压缩视频
                if enable_compression:
                    compressed_path = f"{file_path}_compressed.mp4"
                    print(f"压缩视频: {file_path} -> {compressed_path}")
                    compressed_file = compress_video(file_path, compressed_path, target_bitrate='800k', resolution='1280x720')
                    
                    if compressed_file and os.path.exists(compressed_file):
                        print(f"压缩成功，处理压缩后的视频: {compressed_file}")
                        target_file = compressed_file
                    else:
                        print(f"压缩失败，将使用原始视频: {file_path}")
                        target_file = file_path
                else:
                    print(f"跳过压缩，直接处理原始视频: {file_path}")
                    target_file = file_path

                # 分割和上传逻辑
                video_parts = split_video(target_file, max_file_size)
                file_urls = []
                upload_success = True

                for part_path in video_parts:
                    file_url = upload_video(part_path)
                    if file_url:
                        file_urls.append(file_url)
                        os.remove(part_path)
                        print(f"已删除分割文件: {part_path}")
                    else:
                        print(f"文件 '{part_path}' 上传失败，将删除所有已分割文件，保留源文件 '{file_path}'")
                        upload_success = False
                        for cleanup_path in video_parts:
                            if os.path.exists(cleanup_path):
                                os.remove(cleanup_path)
                                print(f"删除失败上传的分割文件: {cleanup_path}")
                        break

                if upload_success:
                    file_data = "\n".join(file_urls) if len(video_parts) > 1 else file_urls[0]
                    insert_file_record(cursor, folder_id, file, file_size, 1, file_data, duration)
                    db.commit()

                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"已删除原始文件: {file_path}")
                    else:
                        print(f"原始文件 '{file_path}' 不存在，无法删除")
                else:
                    print(f"文件 '{file}' 上传失败，保留本地原始文件")
    
    cursor.close()
    db.close()
    print("所有文件处理完毕")


if __name__ == "__main__":
    main()