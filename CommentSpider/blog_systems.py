from comment_spider import BlogCommentSpider
import random
import requests
from bs4 import BeautifulSoup

class WordPressSpider(BlogCommentSpider):
    def is_article_page(self, soup):
        return soup.find('article') is not None and soup.find('div', {'class': 'comment-respond'}) is not None
    
    def extract_links(self, soup):
        # 获取首页文章链接
        links = []
        articles = soup.find_all('article')
        for article in articles:
            try:
                # 先尝试查找带 entry-title 类的标题
                title_container = article.find('h2', {'class': 'entry-title'})
                if not title_container:
                    # 如果找不到，尝试其他可能的标题容器
                    title_container = article.find(['h1', 'h2', 'h3'], {'class': ['post-title', 'entry-title']})
                
                if title_container:
                    link = title_container.find('a')
                    if link and 'href' in link.attrs:
                        links.append(link['href'])
                        print(f"找到文章链接: {link['href']}")
            except Exception as e:
                print(f"提取文章链接时出错: {str(e)}")
                continue
        
        if not links:
            print("警告：未找到任何文章链接，尝试查找其他可能的链接...")
            # 备用方案：查找所有可能的文章链接
            all_links = soup.find_all('a')
            for link in all_links:
                if link.get('href') and '/archives/' in link.get('href'):
                    links.append(link['href'])
                    print(f"找到备用文章链接: {link['href']}")
        
        print(f"总共找到 {len(links)} 个文章链接")
        return links
    
    def post_comment(self, url, soup):
        try:
            # 获取评论表单数据
            comment_form = soup.find('form', {'id': 'commentform'})
            if not comment_form:
                print(f"在 {url} 未找到评论表单")
                return
                
            # 获取必要的表单字段
            comment_post_id = soup.find('input', {'name': 'comment_post_ID'})['value']
            comment_parent = '0'
            
            # 构建评论数据
            comment_data = {
                'comment': random.choice(self.comment_content_list),
                'author': '访客' + str(random.randint(100, 999)),  # 随机访客名
                'email': f'visitor{random.randint(100,999)}@example.com',  # 随机邮箱
                'url': '',
                'comment_post_ID': comment_post_id,
                'comment_parent': comment_parent,
                'submit': '发表评论'
            }
            
            # 获取评论提交地址
            action_url = comment_form.get('action', url)
            
            # 发送评论请求
            response = requests.post(
                action_url,
                data=comment_data,
                headers={
                    **self.headers,
                    'Referer': url,
                    'Origin': 'https://www.mxin.moe',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            if response.status_code == 200:
                print(f"在 {url} 发表评论成功")
            else:
                print(f"评论提交失败，状态码: {response.status_code}")
            
        except Exception as e:
            print(f"发表评论失败: {str(e)}")
    
    def should_follow_link(self, url):
        # 只跟踪同域名下的文章链接
        return (url.startswith(self.start_url) and 
                'wp-admin' not in url and 
                'wp-login' not in url and
                'feed' not in url)
        
    def extract_post_id(self, soup):
        # 从页面提取文章ID
        post_id = ''
        try:
            post_id = soup.find('input', {'name': 'comment_post_ID'})['value']
        except:
            pass
        return post_id 

class TypechoSpider(BlogCommentSpider):
    def is_article_page(self, soup):
        return soup.find('article') is not None or soup.find('div', {'class': 'post'}) is not None
        
    def post_comment(self, url, soup):
        # 实现Typecho特定的评论逻辑
        pass

class EmlogSpider(BlogCommentSpider):
    def is_article_page(self, soup):
        return soup.find('div', {'class': 'article'}) is not None
        
    def post_comment(self, url, soup):
        # 实现Emlog特定的评论逻辑
        pass