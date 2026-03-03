import os
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import json

def read_config():
    with open('config.json', 'r') as f:
        config = json.load(f)
    return config


class GoogleScholarResearch(object):
    def __init__(self, query, page_num = 999):
        self.query = query
        self.page_num = page_num
        config = read_config()
        self.user_date_dir = config['google']['user_date_dir']
        self.save_dir = config['save_dir']

        self.driver = self.setup_driver(self.user_date_dir)
        self.wait = WebDriverWait(self.driver, 10, poll_frequency=0.5)

    def setup_driver(self, user_date_dir):
        options = Options()
        options.add_experimental_option('detach', True) # 脚本运行结束后浏览器窗口保持打开。

        options.add_argument(f"--user-data-dir={user_date_dir}") # 独立用户目录
        # 稳健性 降低Selenium被网站识别的概率
        options.add_experimental_option("excludeSwitches", ["enable-automation"]) # 排除开关"enable-automation"
        options.add_experimental_option('useAutomationExtension', False) # 禁用Chrome自动化扩展 核心自动化功能通常不受影响
        
        driver_path = ChromeDriverManager().install() # 使用webdriver_manager自动下载和管理ChromeDriver
        service = Service(executable_path=driver_path)

        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10) # 设置隐式等待时间，单位为秒
        driver.set_window_rect(800, 0, 600, 800)
        return driver
    def search(self):
        self.driver.get("https://scholar.google.com")
        ele_input = self.driver.find_element(By.ID, "gs_hdr_tsi")
        ele_input.clear()
        ele_input.send_keys(self.query)
        for _ in range(2):
            try:
                time.sleep(1)
                ele_click = self.driver.find_element(By.ID, "gs_hdr_tsb")
                ele_click.click()
            except:
                break
    
    def save_paper_to_csv(self, paper_items):
        # 保存到CSV（可追加写入）
        save_path = f"{self.save_dir}\\{self.query}.csv"

        # 判断文件是否存在，如果存在则追加，不存在则新建
        if os.path.exists(save_path):
            # 追加模式，不写表头
            df = pd.DataFrame(paper_items)
            df.to_csv(save_path, mode='a', index=False, header=False, encoding='utf-8-sig')
        else:
            # 首次创建文件，包含表头
            df = pd.DataFrame(paper_items)
            df.to_csv(save_path, index=False, encoding='utf-8-sig')

        print(f"已保存 {len(df)} 条记录到 papers.csv")
    
    def stop_and_quit(self,pause):
        if pause:
            input("Press Enter to close the browser...")
        self.driver.close()
        # 退出浏览器并释放驱动
        self.driver.quit()

    def clean_title(self,title):
        """
        移除标题开头的中括号部分，例如 [HTML]、[PDF] 等。
        例如："[HTML][HTML]Motion capture..." -> "Motion capture..."
        """
        if not title:
            return ""
        # 使用正则表达式移除开头所有由中括号包围的内容（包括可能的多组括号）
        cleaned = re.sub(r'^(\s*\[[^\]]*\]\s*)+', '', title)
        return cleaned.strip()
    
    def split_author_info(self, author_info_str):
        """
        将作者信息字符串分割为作者列表和出版信息。
        格式通常为: "作者1, 作者2... - 期刊/会议, 年份 - 出版社/网站"
        """
        if not author_info_str:
            return [], ""

        # 清理字符串两端的引号和空格
        info = author_info_str.strip(' "\'')
        
        # 按 " - " 分割，第一个部分通常是作者，剩余部分是出版信息
        parts = info.split(' - ', 1)
        
        if len(parts) == 2:
            authors_part = parts[0].strip()
            publication_part = parts[1].strip()
        else:
            # 如果没有找到 " - "，整个字符串视为作者
            authors_part = info
            publication_part = ""
        
        # 将作者部分按逗号分割成列表，并清理每个作者名字
        authors = [author.strip() for author in authors_part.split(',')]
        
        return authors, publication_part

    def classify_publication(self, pub_info):
        """
        根据出版信息判断论文发表在期刊还是会议。
        返回: "期刊", "会议", 或 "其他/未知"
        """
        pub_info_lower = pub_info.lower()
        
        # 期刊关键词
        journal_keywords = [
            'journal', 'transactions', 'letters', 'magazine', 
            'review', 'annals', 'archive', 'science',
            'nature', 'cell', 'sensors', 'springer', 'elsevier',
            'taylor', 'francis', 'wiley', 'mdpi', 'plos', 'peerj'
        ]
        
        # 会议关键词
        conference_keywords = [
            'proceedings', 'conference', 'symposium', 'workshop',
            'icra', 'cvpr', 'iccv', 'eccv', 'neurips', 'icml',
            'acl', 'sig', 'ieee', 'acm', 'international conference',
            'annual meeting', 'proc.', 'conf.'
        ]
        
        # 统计关键词出现次数
        journal_score = sum(1 for keyword in journal_keywords if keyword in pub_info_lower)
        conference_score = sum(1 for keyword in conference_keywords if keyword in pub_info_lower)
        
        # 根据得分判断类型
        if journal_score > conference_score:
            return "期刊"
        elif conference_score > journal_score:
            return "会议"
        else:
            return "其他/未知"
    def paper_process(self, papers_div):
        paper_items = []
        for paper in papers_div:
            title = paper.select_one("h3.gs_rt").get_text(strip=True) if paper.select_one("h3.gs_rt") else ""
            title = self.clean_title(title)
            author_info_str = paper.select_one("div.gs_a").get_text() if paper.select_one("div.gs_a") else ""
            authors, publication_part = self.split_author_info(author_info_str)
            pub_type = self.classify_publication(publication_part)
            item = {
                "标题": title,
                "作者信息": authors,
                "出版信息": publication_part,
                "出版物类型": pub_type,
                "摘要": paper.select_one("div.gs_rs").get_text(strip=True) if paper.select_one("div.gs_rs") else "",
                "PDF链接": paper.select_one("a[href$='.pdf']").get("href") if paper.select_one("a[href$='.pdf']") else None,
                "论文链接": paper.select_one("h3.gs_rt a").get("href") if paper.select_one("h3.gs_rt a") else None
            }
            paper_items.append(item)

        return paper_items
    def run(self):
        self.search()

        for page in range(self.page_num):
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#gs_res_ccl_mid > div:nth-child(1)")))
            except:
                print(f"No found any paper, finish.")
                break

            full_html = self.driver.page_source

            soup = BeautifulSoup(full_html, 'html.parser')
            papers_div = soup.select("#gs_res_ccl_mid > div")

            paper_items = self.paper_process(papers_div)

            self.save_paper_to_csv(paper_items)

            try:
                next_page = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#gs_nm > button.gs_btnPR.gs_in_ib.gs_btn_lrge.gs_btn_half.gs_btn_lsu"))
                )
                next_page.click()
                print("="*10, f"Next page({page+1}/{self.page_num})", "="*10)
                time.sleep(5)
            except:
                print(f"No found next page button, finish.")
                break
        
        self.stop_and_quit(pause=False)


if __name__ == "__main__":
    key = 'motion capture'
    gs = GoogleScholarResearch(key)
    gs.run()