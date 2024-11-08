from flask import Flask, render_template
from PIL import Image, ImageDraw, ImageOps
import io
import base64

app = Flask(__name__)

def crop_puzzle_piece(image, mask_path):
    """
    从输入图像中裁剪出拼图形状，并应用遮罩。

    参数:
        image (PIL.Image.Image): 输入的PIL图像对象。
        mask_path (str): 拼图遮罩图像的路径。

    返回:
        PIL.Image.Image: 裁剪并应用拼图遮罩后的图像。
    """
    mask = Image.open(mask_path).convert("L")  # 载入拼图遮罩并转换为灰度图
    mask = ImageOps.fit(mask, image.size, centering=(0.5, 0.5))  # 调整遮罩大小以适应输入图像
    image = image.convert("RGBA")  # 确保输入图像具有透明度通道
    image.putalpha(mask)  # 应用拼图遮罩
    return image

def image_to_base64(img, format='PNG'):
    """
    将PIL图像转换为Base64编码的字符串。

    参数:
        img (PIL.Image.Image): 输入的PIL图像对象。
        format (str): 图像保存的格式，如 'PNG' 或 'JPEG'。

    返回:
        str: Base64编码的图像字符串。
    """
    buffered = io.BytesIO()
    img.save(buffered, format=format)  # 将图像保存到内存中的缓冲区
    return base64.b64encode(buffered.getvalue()).decode()  # 编码为Base64字符串

@app.route('/')
def index():
    """
    Flask路由处理函数，处理主页请求。
    1. 打开背景图像。
    2. 裁剪拼图形状并添加边框和遮罩。
    3. 将裁剪后的图像粘贴到背景图上。
    4. 将最终图像转换为Base64编码并传递给HTML模板。
    """
    background_path = 'static/background.jpg'  # 背景图像的路径
    puzzle_mask_path = 'static/image.png'  # 拼图形状遮罩的路径
    with Image.open(background_path) as img:
        # 将背景图像转换为RGBA模式，以支持透明度
        background = img.convert('RGBA')
        
        # 裁剪拼图形状
        puzzle_piece = crop_puzzle_piece(img, puzzle_mask_path)
        
        # 计算拼图形状的位置并粘贴到背景图上
        puzzle_position = ((background.width - puzzle_piece.width) // 2, (background.height - puzzle_piece.height) // 2)
        background.paste(puzzle_piece, puzzle_position, puzzle_piece)  # 使用拼图形状的alpha通道作为遮罩
        
        # 将最终的背景图转换为JPEG格式（去除透明度）
        final_image = background.convert('RGB')
        buffered = io.BytesIO()
        final_image.save(buffered, format="JPEG")  # 保存到内存中的缓冲区
        img_str = base64.b64encode(buffered.getvalue()).decode()  # 编码为Base64字符串
    
    # 渲染HTML模板，并将Base64编码的图像传递给模板
    return render_template('index.html', modified_image=img_str)

if __name__ == '__main__':
    app.run(debug=True)