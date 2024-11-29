from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import random
import time
from urllib.parse import urljoin

class BlogCommentSpider:
    def __init__(self, start_url, comment_content_list):
        self.start_url = start_url
        self.visited_urls = set()
        self.comment_content_list = comment_content_list
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def start_crawling(self):
        self.crawl_page(self.start_url)
        
    def crawl_page(self, url):
        if url in self.visited_urls:
            return
            
        try:
            print(f"\n开始爬取页面: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()  # 检查响应状态
            
            if response.status_code == 200:
                print(f"页面获取成功，开始解析...")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 添加评论
                if self.is_article_page(soup):
                    print("检测到文章页面，准备发表评论...")
                    self.post_comment(url, soup)
                else:
                    print("当前页面不是文章页面，继续寻找文章链接...")
                
                # 获取更多链接继续爬取
                print("开始提取页面中的链接...")
                links = self.extract_links(soup)
                self.visited_urls.add(url)
                
                # 随机延迟，避免被封
                delay = random.uniform(3, 7)
                print(f"等待 {delay:.2f} 秒后继续...")
                time.sleep(delay)
                
                for link in links:
                    absolute_url = urljoin(url, link)
                    if self.should_follow_link(absolute_url):
                        self.crawl_page(absolute_url)
                
            else:
                print(f"页面响应异常，状态码: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {str(e)}")
        except Exception as e:
            print(f"爬取页面 {url} 时发生错误: {str(e)}") 