<?php
header('Content-Type: application/json');

// 错误处理设置
ini_set('display_errors', 0);
error_reporting(E_ALL);

// 统一响应格式
function jsonResponse($success, $message = '', $data = []) {
    $response = [
        'success' => $success,
        'message' => $message,
        'data' => $data
    ];
    exit(json_encode($response));
}

try {
    if ($_SERVER['REQUEST_METHOD'] != 'POST') {
        throw new Exception("仅支持POST请求");
    }

    // 验证认证密码
    if (!isset($_POST['auth_password']) || $_POST['auth_password'] != '451235fasfwre') {
        throw new Exception("认证失败");
    }

    // 验证必要参数
    $requiredParams = [
        'db_host', 'db_user', 'db_password', 'db_database',
        'older_name', 'upload_url', 'domain_prefix', 'attribute'
    ];
    
    foreach ($requiredParams as $param) {
        if (!isset($_POST[$param])) {
            throw new Exception("缺少必要参数: $param");
        }
    }

    // 数据库连接参数
    $host = $_POST['db_host'];
    $user = $_POST['db_user'];
    $password = $_POST['db_password'];
    $database = $_POST['db_database'];
    $folder_name = $_POST['older_name'];
    $upload_url = $_POST['upload_url'];
    $domain_prefix = rtrim($_POST['domain_prefix'], '/');
    $attribute = intval($_POST['attribute']);
    $folder_password = $_POST['password'] ?? null;

    // 创建数据库连接
    $conn = new mysqli($host, $user, $password, $database);
    if ($conn->connect_error) {
        throw new Exception("数据库连接失败: " . $conn->connect_error);
    }

    // 处理文件上传
    if (empty($_FILES['file']['tmp_name'])) {
        throw new Exception("未收到上传文件");
    }

    // 上传到目标服务器
    $file_tmp = $_FILES['file']['tmp_name'];
    $file_name = basename($_FILES['file']['name']);
    $file_size = $_FILES['file']['size'];
    $file_type = $_FILES['file']['type'];
    
    $ch = curl_init();
    $cfile = new CURLFile($file_tmp, $file_type, $file_name);
    $data = ['file' => $cfile];

    curl_setopt_array($ch, [
        CURLOPT_URL => $upload_url,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $data,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_SSL_VERIFYPEER => 0
    ]);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    if (curl_errno($ch)) {
        throw new Exception("文件传输失败: " . curl_error($ch));
    }

    // 解析响应内容
    $responseData = json_decode($response, true);
    if (!$responseData || !isset($responseData['src'])) {
        throw new Exception("无效的响应格式");
    }

    // 获取完整URL
    $relative_path = ltrim($responseData['src'], '/');
    $full_url = $domain_prefix . '/' . $relative_path;

    // 创建文件夹记录
    $folder_id = create_folder_if_not_exists($conn, $folder_name, $attribute, $folder_password);

    // 插入文件记录
    $created_at = date('Y-m-d H:i:s');
    $stmt = $conn->prepare("INSERT INTO files (folder_id, name, size, type, url, created_at) VALUES (?, ?, ?, ?, ?, ?)");
    $stmt->bind_param("isssss", $folder_id, $file_name, $file_size, $file_type, $full_url, $created_at);

    if (!$stmt->execute()) {
        throw new Exception("数据库插入失败: " . $stmt->error);
    }

    // 返回成功响应
    jsonResponse(true, '上传成功', [
        'filename' => $file_name,
        'url' => $full_url,
        'size' => $file_size,
        'created_at' => $created_at
    ]);

} catch (Exception $e) {
    http_response_code(500);
    jsonResponse(false, $e->getMessage());
}

/**
 * 创建文件夹记录
 */
function create_folder_if_not_exists($conn, $name, $attribute, $password) {
    $stmt = $conn->prepare("SELECT id FROM folders WHERE name = ?");
    $stmt->bind_param("s", $name);
    $stmt->execute();
    
    $result = $stmt->get_result();
    if ($result->num_rows > 0) {
        return $result->fetch_assoc()['id'];
    }

    $stmt = $conn->prepare("INSERT INTO folders (name, attribute, password, created_at) VALUES (?, ?, ?, ?)");
    $created_at = date('Y-m-d H:i:s');
    $stmt->bind_param("siss", $name, $attribute, $password, $created_at);
    
    if (!$stmt->execute()) {
        throw new Exception("文件夹创建失败: " . $stmt->error);
    }
    
    return $stmt->insert_id;
}
?>