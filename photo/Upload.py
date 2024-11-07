import os
import mysql.connector
import requests
from datetime import datetime
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv
load_dotenv()

# 配置数据库连接信息
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '123456789',
    'database': 'photo_moejue_cn'
}

# 定义目标文件夹路径和文件大小限制
older_name = "images"
video_folder_path = '/Users/ajue/Desktop/未命名文件夹/视频'
max_file_size = 15 * 1024 * 1024  # 18 MB in bytes
upload_url = os.getenv("UPLOAD_URL")
domain_prefix = 'https://moejuevideo.pages.dev'

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
    folder_id = create_folder_if_not_exists(cursor, older_name)
    db.commit()
    
    for root, _, files in os.walk(video_folder_path):
        for file in files:
            # 忽略隐藏文件
            if file.startswith('.'):
                continue

            file_path = os.path.join(root, file)
            print(f"正在处理文件: {file_path}")
            file_size = get_file_size(file_path)

            # 判断文件类型
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):  # 支持的图片格式
                # 上传图片
                file_url = upload_video(file_path)  # 图片直接上传
                if file_url:
                    insert_file_record(cursor, folder_id, file, file_size, 0, file_url, None)  # 图片时长为 None
                    db.commit()
                    os.remove(file_path)
                    print(f"图片 '{file}' 上传并记录成功，已删除本地文件")
                else:
                    print(f"图片 '{file}' 上传失败，保留本地文件")
            else:
                # 处理视频
                duration = get_video_duration(file_path)

                # 如果文件大小超过 18MB，进行分割
                video_parts = split_video(file_path, max_file_size)
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
    
    # 关闭数据库连接
    cursor.close()
    db.close()
    print("所有文件处理完毕")


if __name__ == "__main__":
    main()