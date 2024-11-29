from blog_detector import BlogDetector
import time
import random
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

class BlogCrawler:
    def __init__(self):
        self.detector = BlogDetector()
        self.visited_sites = set()  # 记录已访问的站点
        self.max_retries = 2  # 最大重试次数
        self.comments = [
            "写得很好，学习了！",
            "感谢分享，文章很有帮助。",
            "期待更多类似的文章。",
            "写得非常详细，收藏了！",
            "内容很实用，感谢博主分享！",
            "学到了很多，谢谢！"
        ]

    def get_domain(self, url):
        """获取URL的域名"""
        return urlparse(url).netloc

    def find_external_links(self, soup, current_url):
        """查找外部链接"""
        external_links = set()
        current_domain = self.get_domain(current_url)
        
        for link in soup.find_all('a', href=True):
            try:
                url = urljoin(current_url, link['href'])
                # 解析URL
                parsed = urlparse(url)
                domain = parsed.netloc
                
                # 检查是否为有效域名且不是当前域名
                if (domain and 
                    domain != current_domain and 
                    domain not in self.visited_sites):
                    
                    # 构建干净的域名URL
                    clean_url = f"{parsed.scheme}://{parsed.netloc}"
                    
                    # 排除邮件链接和一些特殊服务
                    if not any(x in clean_url.lower() for x in [
                        'mail.', 'mailto:', 'javascript:', 
                        'share?', 'mailme', 'email=',
                        't.qq.com', 'weibo.com', 'twitter.com',
                        'facebook.com', 'linkedin.com'
                    ]):
                        external_links.add(clean_url)
                        print(f"找到外链: {clean_url}")
            
            except Exception as e:
                print(f"处理链接时出错: {str(e)}")
                continue
        
        return list(external_links)

    def process_site(self, url, depth=0):
        if depth > 10:  # 限制递归深度
            print(f"达到最大递归深度 {depth}，返回上层继续查找...")
            return
        
        try:
            current_domain = self.get_domain(url)
            if current_domain in self.visited_sites:
                print(f"域名 {current_domain} 已访问过，跳过...")
                return
            
            print(f"\n开始处理网站: {url}")
            self.visited_sites.add(current_domain)
            
            try:
                # 检测博客系统
                blog_type, soup = self.detector.detect_blog_system(url)
            except Exception as e:
                print(f"检测博客系统失败: {str(e)}，继续处理其他链接...")
                return
            
            if blog_type == "WordPress":
                # 尝试发表评论
                self._try_comment_on_site(url, soup)
                
                # 无论评论是否成功，都继续寻找新链接
                while True:  # 持续寻找直到找到有效链接或尝试完所有可能
                    try:
                        # 先尝试在当前页面找外链
                        external_links = self.find_external_links(soup, url)
                        if external_links:
                            print(f"\n找到 {len(external_links)} 个外部链接")
                            random.shuffle(external_links)
                            
                            for ext_url in external_links:
                                try:
                                    print(f"\n尝试访问外链: {ext_url}")
                                    self.process_site(ext_url, depth + 1)
                                except Exception as e:
                                    print(f"处理外链时出错: {str(e)}，继续下一个...")
                                    continue
                        
                        # 如果没有找到外链或处理外链失败，尝试站内页面
                        print("\n在站内继续寻找新页面...")
                        new_page_url = self._explore_new_page(url)
                        
                        if new_page_url:
                            print(f"访问新页面: {new_page_url}")
                            response = requests.get(new_page_url, headers=self.detector.headers, timeout=10)
                            new_soup = BeautifulSoup(response.text, 'html.parser')
                            soup = new_soup  # 更新soup以在下一次循环中使用
                            time.sleep(random.uniform(2, 4))
                        else:
                            print("未找到更多可访问的页面，结束当前站点处理")
                            break
                            
                    except Exception as e:
                        print(f"处理站点链接时出错: {str(e)}，尝试继续...")
                        time.sleep(random.uniform(2, 4))
                        continue
            else:
                print(f"网站 {url} 不是WordPress系统，继续寻找其他链接...")
                
        except Exception as e:
            print(f"处理站点 {url} 时发生错误: {str(e)}，继续处理其他链接...")

    def _try_comment_on_site(self, url, soup):
        """尝试在站点发表评论"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                article_url = self.detector.get_random_article_url(url, soup)
                if article_url:
                    print(f"\n尝试在文章 {article_url} 发表评论 (第 {retry_count + 1} 次尝试)")
                    comment = random.choice(self.comments)
                    time.sleep(random.uniform(3, 6))
                    
                    if self.detector.post_comment(article_url, comment):
                        print("评论发表成功！")
                        return True
                
                retry_count += 1
                print(f"评论失败，将尝试其他文章... ({retry_count}/{self.max_retries})")
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"评论过程出错: {str(e)}")
                retry_count += 1
                continue
        
        return False

    def _explore_new_page(self, base_url):
        """查找新的站内页面"""
        try:
            response = requests.get(base_url, headers=self.detector.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            internal_links = set()
            for link in soup.find_all('a', href=True):
                try:
                    internal_url = urljoin(base_url, link['href'])
                    if (internal_url.startswith(base_url) and 
                        not any(x in internal_url.lower() for x in [
                            '/wp-admin', '/wp-login', '/feed', 
                            '/wp-content', '/wp-includes', 'wp-json',
                            'replytocom=', '/attachment/', '/trackback/',
                            'share=', 'action=', '/comment-page-'
                        ])):
                        internal_links.add(internal_url)
                except:
                    continue
            
            if internal_links:
                return random.choice(list(internal_links))
            return None
            
        except Exception as e:
            print(f"查找新页面时出错: {str(e)}")
            return None

# 运行爬虫
crawler = BlogCrawler()
start_url = "https://www.aimiliy.top/"
crawler.process_site(start_url) 