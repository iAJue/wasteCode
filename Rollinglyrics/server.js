const express = require('express');
const path = require('path');

const app = express();
const PORT = 3001;

// 设置静态文件目录
app.use(express.static(path.join(__dirname, 'public')));

// 处理根目录请求，返回 1.html 文件
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});