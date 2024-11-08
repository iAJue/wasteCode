from gtts import gTTS
import os

def text_to_speech(text, output_filename):
    # 创建 gTTS 对象
    tts = gTTS(text=text, lang='zh-cn', slow=False)
    
    # 保存语音到文件
    tts.save(output_filename)
    print(f"Speech saved to {output_filename}")

# 使用示例：
script_text = """
这里输入你要转换成语音的文稿内容。确保文本内容为中文（zh-cn）。
"""

output_audio = 'output_audio.mp3'
text_to_speech(script_text, output_audio)