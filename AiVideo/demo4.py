
from tensorflow.keras.applications import InceptionV3
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.inception_v3 import preprocess_input, decode_predictions
import numpy as np

# 加载预训练的InceptionV3模型
model = InceptionV3(weights='imagenet')

# 读取并预处理图像
img_path = '/Users/ajue/Documents/AiVideo/output_segments/segment_1/frame_0020.png'
img = image.load_img(img_path, target_size=(299, 299))
img_array = image.img_to_array(img)
img_array = np.expand_dims(img_array, axis=0)
img_array = preprocess_input(img_array)

# 进行预测
predictions = model.predict(img_array)
decoded_predictions = decode_predictions(predictions, top=3)[0]

# 生成描述文本
description = "The image contains "
for i, (imagenet_id, label, score) in enumerate(decoded_predictions):
    description += f"{label} with a {score*100:.2f}% probability"
    if i < len(decoded_predictions) - 1:
        description += ", "

# 打印生成的描
print(description)