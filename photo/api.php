<?php
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Origin: *"); 
header("Access-Control-Allow-Methods: GET, POST"); 
header("Access-Control-Allow-Headers: Content-Type"); 
$servername = "127.0.0.1";
$username = "photo_moejue_cn";
$password = "3zWdFaL7WZYzp26n";
$dbname = "photo_moejue_cn";

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die(json_encode(["error" => "连接数据库失败: " . $conn->connect_error]));
}

// 缓存相关设置
$cacheTime = 600; // 缓存时间5分钟（300秒）
$cacheDir = __DIR__ . '/cache/';
if (!is_dir($cacheDir)) {
    mkdir($cacheDir, 0755, true);
}

// 获取分页参数
$page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
$limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 10;
$offset = ($page - 1) * $limit;

// 获取请求 URL 作为缓存文件名
$requestUrl = $_SERVER['REQUEST_URI'];
$cacheFile = $cacheDir . md5($requestUrl) . '.json';

// 检查缓存文件是否存在且未过期
if (file_exists($cacheFile) && (time() - filemtime($cacheFile)) < $cacheTime) {
    echo file_get_contents($cacheFile);
    exit; // 直接返回缓存内容
}

if (isset($_GET['action'])) {
    $action = $_GET['action'];
    ob_start(); // 启用输出缓冲区
    switch ($action) {
        case "photos":
            getPhotos($conn, $offset, $limit);
            break;
        case "albums":
            getAlbums($conn);
            break;
        case "random":
            getRandomMedia($conn, $offset, $limit);
            break;
        default:
            echo json_encode(["error" => "无效的接口请求"]);
    }
    $output = ob_get_clean(); // 获取输出缓冲区内容

    // 将输出内容写入缓存文件
    file_put_contents($cacheFile, $output);
    echo $output; // 输出内容到客户端
} else {
    echo json_encode(["error" => "未指定接口操作"]);
}

$conn->close();

// 日期分组格式化函数
function formatDataByDate($data) {
    $groupedData = [];
    $today = strtotime('today');
    $yesterday = strtotime('yesterday');
    $dayBeforeYesterday = strtotime('-2 days');
    $currentYear = date("Y");

    foreach ($data as $item) {
        $itemDate = strtotime($item['created_at']);
        $itemYear = date("Y", $itemDate);
        
        // 根据日期确定显示的日期标签
        if ($itemDate >= $today) {
            $dateKey = "今天";
        } elseif ($itemDate >= $yesterday) {
            $dateKey = "昨天";
        } elseif ($itemDate >= $dayBeforeYesterday) {
            $dateKey = "前天";
        } else {
            // 判断年份是否为当前年份
            $dateFormat = ($itemYear === $currentYear) ? "m月d日" : "Y年m月d日";
            $dateKey = date($dateFormat, $itemDate);
        }
        
        // 初始化分组数据
        if (!isset($groupedData[$dateKey])) {
            $groupedData[$dateKey] = ['date' => $dateKey, 'items' => []];
        }

        // 添加项目数据
        $groupedData[$dateKey]['items'][] = [
            'src' => $item['data'],
            'alt' => $item['name'],
            'isVideo' => $item['type'] == 1,
            'duration' => $item['duration'] ?? null
        ];
    }

    return array_values($groupedData);
}


// 照片接口
function getPhotos($conn, $offset, $limit) {
    // 获取可选参数 folder_id、password 和 search
    $folder_id = isset($_GET['folder_id']) ? (int)$_GET['folder_id'] : null;
    $password = isset($_GET['password']) ? $_GET['password'] : null;
    $search = isset($_GET['search']) ? $_GET['search'] : null;


    // 验证文件夹密码（如果指定了 folder_id 且该文件夹需要密码）
    if ($folder_id) {
        $query = "SELECT password FROM folders WHERE id = ?";
        $stmt = $conn->prepare($query);
        $stmt->bind_param("i", $folder_id);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($row = $result->fetch_assoc()) {
            // 如果文件夹设置了密码且密码不匹配，返回错误
            if ($row['password'] && $row['password'] !== $password) {
                echo json_encode(["error" => "文件夹密码错误"]);
                return;
            }
        } else {
            echo json_encode(["error" => "文件夹不存在"]);
            return;
        }
    }

    // 构建 SQL 查询
    $query = "SELECT * FROM files";
    $conditions = [];
    $params = [];
    $types = "";

    // 处理 folder_id 条件
    if ($folder_id) {
        $conditions[] = "folder_id = ?";
        $params[] = $folder_id;
        $types .= "i";
    } else {
        if ($search) {
            $conditions[] = "folder_id IN (SELECT id FROM folders WHERE attribute = 0)";
        }else {
            $conditions[] = "type = 0 AND folder_id IN (SELECT id FROM folders WHERE attribute = 0)";
        }
    }

    // 处理 search 条件
    if ($search) {
        $conditions[] = "(name LIKE ? OR data LIKE ?)";
        $params[] = "%$search%";
        $params[] = "%$search%";
        $types .= "ss";
    }

    // 将条件组合到查询中
    if ($conditions) {
        $query .= " WHERE " . implode(" AND ", $conditions);
    }
    $query .= " ORDER BY created_at DESC LIMIT ?, ?";

    // 设置分页参数
    $params[] = $offset;
    $params[] = $limit;
    $types .= "ii";

    // 准备并执行查询
    $stmt = $conn->prepare($query);
    $stmt->bind_param($types, ...$params);
    $stmt->execute();
    $result = $stmt->get_result();

    // 获取查询结果并格式化数据
    $photos = [];
    while ($row = $result->fetch_assoc()) {
        $photos[] = $row;
    }
    echo json_encode(formatDataByDate($photos));
}

// 相册接口
function getAlbums($conn) {
    $query = "
        SELECT 
            f.id AS folder_id, 
            f.name AS folder_name, 
            f.created_at, f.attribute,
            f.password,
            COUNT(files.id) AS photo_count, 
            (SELECT files.data 
             FROM files 
             WHERE files.folder_id = f.id 
             ORDER BY files.created_at DESC 
             LIMIT 1) AS latest_image 
        FROM 
            folders f 
        LEFT JOIN 
            files ON files.folder_id = f.id 
        GROUP BY 
            f.id 
        ORDER BY 
            f.created_at DESC";
    
    $result = $conn->query($query);

    $albums = [];
    while ($row = $result->fetch_assoc()) {
        $albums[] = [
            "folder_id" => $row["folder_id"],
            "folder_name" => $row["folder_name"],
            "created_at" => $row["created_at"],
            "photo_count" => $row["photo_count"],
            "latest_image" => $row["latest_image"],
            'attribute' => $row['attribute'],
            "ispassword" => !!$row['password']
        ];
    }

    echo json_encode($albums);
}

// 随机接口(该方法效率较低,尽可能不要频繁执行,并确保有缓存存在)
function getRandomMedia($conn, $page, $limit) {
    // 每种类型分配的记录数，尽量平分
    $typeLimit = ceil($limit / 2);

    // 分别查询图片和视频
    $query = "
        (
            SELECT f.*
            FROM files f
            JOIN folders fo ON f.folder_id = fo.id
            WHERE fo.attribute = 0 AND f.type = 0
            ORDER BY RAND()
            LIMIT ?
        )
        UNION ALL
        (
            SELECT f.*
            FROM files f
            JOIN folders fo ON f.folder_id = fo.id
            WHERE fo.attribute = 0 AND f.type = 1
            ORDER BY RAND()
            LIMIT ?
        )
        ORDER BY RAND()
        LIMIT ?";
    
    $stmt = $conn->prepare($query);
    $stmt->bind_param("iii", $typeLimit, $typeLimit, $limit);
    $stmt->execute();
    $result = $stmt->get_result();

    $media = [];
    while ($row = $result->fetch_assoc()) {
        $media[] = $row;
    }
    echo json_encode($media);
}
?>