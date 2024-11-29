import requests
from bs4 import BeautifulSoup
import random
from urllib.parse import urljoin, urlparse
import re
import time

class BlogDetector:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def detect_blog_system(self, url):
        try:
            print(f"正在检测网站: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检测方法1：查找页面源码中是否包含WordPress相关关键词
            page_source = response.text.lower()
            if 'wordpress' in page_source:
                print("√ 检测到 WordPress 特征（源码关键词）")
                return "WordPress", soup
                
            # 检测方法2：检查是否存在wp-includes目录
            if 'wp-includes' in page_source or 'wp-content' in page_source:
                print("√ 检测到 WordPress 特征（目录结构）")
                return "WordPress", soup
                
            # 检测方法3：检查meta标签
            generator_meta = soup.find('meta', {'name': 'generator'})
            if generator_meta and 'wordpress' in generator_meta.get('content', '').lower():
                print("√ 检测到 WordPress 特征（meta标签）")
                return "WordPress", soup
            
            print("× 未检测到 WordPress 特征")
            return "Unknown", soup
            
        except Exception as e:
            print(f"检测过程中发生错误: {str(e)}")
            return "Error", None

    def get_random_article_url(self, base_url, soup):
        try:
            # 获取页面上所有链接
            all_links = set()  # 使用set避免重复
            links = soup.find_all('a', href=True)
            
            for link in links:
                url = urljoin(base_url, link['href'])
                # 只保留同域名的链接
                if url.startswith(base_url):
                    all_links.add(url)
            
            # 转换为列表并随机排序
            all_links = list(all_links)
            random.shuffle(all_links)
            
            print(f"\n找到 {len(all_links)} 个站内链接")
            
            # 遍历链接并检查是否为文章页面
            for url in all_links:
                try:
                    # 排除明显的非文章链接
                    if any(pattern in url.lower() for pattern in [
                        '/wp-admin', '/wp-login', '/feed', 
                        '/wp-content', '/wp-includes', 'wp-json',
                        '/category/', '/tag/', '/author/',
                        'replytocom=', '/attachment/', '/trackback/',
                        'share=', 'action=', '/comment-page-'
                    ]):
                        continue
                    
                    print(f"\n检查链接: {url}")
                    response = requests.get(url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        article_soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 检查是否为文章页面（多重判断）
                        is_article = False
                        
                        # 方法1：检查评论相关元素
                        if (article_soup.find('form', {'id': 'commentform'}) or 
                            article_soup.find('div', {'class': ['comment-respond', 'comments-area', 'comments']}) or
                            article_soup.find('div', id=lambda x: x and 'comments' in x.lower())):
                            is_article = True
                        
                        # 方法2：检查文章结构
                        if not is_article:
                            article_element = article_soup.find(['article', 'div'], {
                                'class': lambda x: x and any(c in str(x).lower() for c in [
                                    'post', 'article', 'entry', 'blog-post', 'content'
                                ])
                            })
                            if article_element:
                                # 检查是否有标题
                                title = article_soup.find(['h1', 'h2'], {
                                    'class': lambda x: x and any(c in str(x).lower() for c in [
                                        'title', 'post-title', 'entry-title',
                                        'article-title', 'heading'
                                    ])
                                })
                                if title:
                                    is_article = True
                        
                        # 方法3：检查URL结构
                        if not is_article:
                            url_patterns = [
                                r'/\d{4}/\d{2}/\d{2}/',  # 日期格式
                                r'/archives/\d+',         # archives格式
                                r'/p/\d+',               # p格式
                                r'/\?p=\d+',             # ?p=格式
                                r'/post/\d+',            # post格式
                                r'/article/\d+'          # article格式
                            ]
                            if any(re.search(pattern, url) for pattern in url_patterns):
                                # 额外检查页面内容
                                if (article_soup.find(['article', 'div'], {'class': ['post', 'article', 'content']}) and
                                    article_soup.find(['h1', 'h2', 'h3'])):
                                    is_article = True
                        
                        # 方法4：检查页面结构特征
                        if not is_article:
                            # 检查是否有典型的文章元数据
                            meta_elements = article_soup.find_all(['span', 'div', 'p'], {
                                'class': lambda x: x and any(c in str(x).lower() for c in [
                                    'meta', 'date', 'author', 'time', 'post-info',
                                    'entry-meta', 'article-meta'
                                ])
                            })
                            if meta_elements and article_soup.find(['h1', 'h2']):
                                is_article = True
                        
                        if is_article:
                            print(f"✓ 找到有效文章页面: {url}")
                            return url
                    
                    time.sleep(random.uniform(1, 2))  # 短暂延迟
                    
                except Exception as e:
                    print(f"检查链接 {url} 时出错: {str(e)}")
                    continue
            
            print("未找到有效的文章页面")
            return None
            
        except Exception as e:
            print(f"获取文章链接时发生错误: {str(e)}")
            return None
    
    def _is_valid_article_url(self, base_url, url):
        """判断URL是否为有效的文章链接"""
        try:
            # 确保链接属于同一域名
            if not url.startswith(base_url):
                return False
            
            # 排除无关链接
            exclude_patterns = [
                '/wp-admin', '/wp-login', '/feed', '/page/', 
                '/category/', '/tag/', '/author/', '/wp-content/',
                '/wp-includes/', 'wp-json', '/comments', '/feed/',
                'replytocom=', '/attachment/', '/trackback/',
                'share=', 'action=', '/page/', '/comment-page-'
            ]
            
            if any(pattern in url.lower() for pattern in exclude_patterns):
                return False
            
            # 检查是否符合文章URL模式
            valid_patterns = [
                # 常见文章路径
                '/archives/', '/posts/', '/post/', '/article/', 
                '/blog/', '/p=', '/?p=', '/index.php/',
                # 年月格式
                r'/\d{4}/\d{2}/',
                # 数字ID模式
                r'/\d+\.html?$',
                r'/\d+/?$',
                # 自定义固定链接格式
                r'/[a-zA-Z0-9_-]+\.html?$',
                r'/[a-zA-Z0-9_-]+/?$'
            ]
            
            # 检查是否匹配任一模式
            for pattern in valid_patterns:
                if pattern.startswith('/') and pattern.endswith('/'):
                    # 正则表达式模式
                    if re.search(pattern[1:-1], url):
                        return True
                else:
                    # 普通字符串模式
                    if pattern in url:
                        return True
            
            return False
            
        except Exception as e:
            print(f"URL验证错误: {str(e)}")
            return False

    def post_comment(self, article_url, comment_text):
        try:
            # 获取文章页面
            response = requests.get(article_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 构建评论数据
            comment_data = {
                'comment': comment_text,
                'author': f'访客{random.randint(100,999)}',
                'email': f'visitor{random.randint(100,999)}@example.com',
                'url': '',
                'submit': '发表评论'
            }
            
            # 尝试获取文章ID
            try:
                # 从隐藏字段获取
                id_field = soup.find('input', {'name': ['comment_post_ID', 'postId', 'article-id']})
                if id_field:
                    comment_data['comment_post_ID'] = id_field['value']
                else:
                    # 从URL提取
                    match = re.search(r'[?&]p=(\d+)|/(\d+)\.html?|/archives/(\d+)', article_url)
                    if match:
                        comment_data['comment_post_ID'] = next(g for g in match.groups() if g is not None)
            except:
                pass  # 如果获取不到ID，就不添加这个字段
            
            # 构建评论提交地址
            action_url = urljoin(article_url, 'wp-comments-post.php')
            
            # 发送评论
            response = requests.post(
                action_url,
                data=comment_data,
                headers={
                    **self.headers,
                    'Referer': article_url,
                    'Origin': f"{urlparse(article_url).scheme}://{urlparse(article_url).netloc}",
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                timeout=10
            )
            
            # 简单判断是否成功
            if response.status_code == 200:
                print(f"评论请求发送成功")
                return True
            else:
                print(f"评论请求失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"发表评论时发生错误: {str(e)}")
            return False 