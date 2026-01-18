import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json
import os
import argparse
from datetime import datetime

def get_authorized_session(base_url):
    """通过模拟动态挑战验证获取授权的 Session"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": base_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    })

    try:
        # 1. 访问首页获取挑战参数
        print(f"正在尝试绕过反爬验证...")
        response = session.get(base_url)
        html = response.text

        # 提取 challengeId 和 answer
        challenge_id_match = re.search(r'var challengeId = "(.*?)";', html)
        answer_match = re.search(r'var answer = (\d+);', html)

        if not challenge_id_match or not answer_match:
            # 如果没发现验证脚本，可能已经有 Cookie 或者没开启验证
            print("未检测到验证挑战，直接使用当前会话。")
            return session

        challenge_id = challenge_id_match.group(1)
        answer = int(answer_match.group(1))
        
        # 2. 提交挑战答案
        challenge_url = urljoin(base_url, '/dynamic_challenge')
        payload = {
            "challenge_id": challenge_id,
            "answer": answer,
            "browser_info": {
                "userAgent": session.headers["User-Agent"],
                "language": "zh-CN",
                "platform": "Win32",
                "cookieEnabled": True,
                "timezone": "Asia/Shanghai"
            }
        }
        
        challenge_resp = session.post(challenge_url, json=payload)
        if challenge_resp.status_code == 200:
            data = challenge_resp.json()
            if data.get('success'):
                # 设置授权 Cookie
                session.cookies.set('client_id', data['client_id'], domain=re.sub(r'^https?://', '', base_url).split('/')[0])
                print(f"✓ 反爬验证绕过成功")
                return session
            
        print("✗ 验证失败，尝试普通会话。")
        return session
    except Exception as e:
        print(f"✗ 绕过验证时发生错误: {e}")
        return session

def clean_text(text):
    """清理文本中的非法字符"""
    if not text:
        return text
    cleaned = ''
    for char in text:
        code = ord(char)
        if code >= 32 or code in [9, 10, 13]:
            cleaned += char
        else:
            cleaned += ' '
    cleaned = re.sub(r'[\u200B-\u200D\uFEFF]', '', cleaned)
    return cleaned

def extract_news_from_page(session, soup, base_url, target_date, news_data, page_num):
    """从当前页面提取指定日期的所有新闻数据"""
    list_ul = soup.find('ul', class_='list')
    if not list_ul:
        list_ul = soup.find('ul', class_=lambda x: x and 'list' in x)
    
    if not list_ul:
        print(f"  未找到列表元素")
        return False
    
    list_items = list_ul.find_all('li')
    print(f"  第 {page_num} 页：找到 {len(list_items)} 个列表项")
    
    found_count = 0
    for idx, li in enumerate(list_items, 1):
        # 首先检查列表页上的日期（通常是 MM-DD 格式）
        span_tag = li.find('span')
        list_date = span_tag.get_text().strip() if span_tag else ""
        
        # 如果列表日期不匹配且包含横杠（排除非日期文本），可能可以直接跳过，
        # 但有些置顶新闻可能日期不按顺序，所以还是得检查一下。
        # 这里我们先进入详情页确认。
        
        link = li.find('a')
        if link:
            href = link.get('href', '')
            full_url = urljoin(base_url, href) if not href.startswith('http') else href
            
            try:
                # 访问详情页
                resp = session.get(full_url, timeout=10)
                resp.encoding = resp.apparent_encoding
                item_soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 提取日期
                publish_time = ""
                art_tit_div = item_soup.find('div', class_='art-tit cont-tit')
                if art_tit_div:
                    date_spans = art_tit_div.find_all('span')
                    for span in date_spans:
                        span_text = span.get_text().strip()
                        if '发布日期' in span_text or '发布时间' in span_text:
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', span_text)
                            if date_match:
                                publish_time = date_match.group(1)
                                break
                
                if not publish_time and list_date:
                    # 如果详情页没找到，用列表页日期补全（假设今年）
                    if re.match(r'\d{2}-\d{2}', list_date):
                        publish_time = f"{datetime.now().year}-{list_date}"
                
                # 匹配日期：检查 publish_time 是否包含 target_date (MM-DD)
                if publish_time and target_date in publish_time:
                    # 提取标题和内容
                    article_title = ""
                    if art_tit_div:
                        h3_tag = art_tit_div.find('h3')
                        if h3_tag:
                            article_title = h3_tag.get_text().strip()
                    
                    if not article_title:
                        title_tag = item_soup.find('title')
                        article_title = title_tag.get_text().strip() if title_tag else "无标题"
                    
                    content_text = ""
                    content_div = item_soup.find('div', class_='v_news_content')
                    if content_div:
                        content_text = content_div.get_text(separator='\n', strip=True)
                        content_text = '\n'.join([line.strip() for line in content_text.split('\n') if line.strip()])

                    news_data.append({
                        'id': f"news_{len(news_data) + 1}",
                        'url': full_url,
                        'source': '教务处',
                        'publish_time': publish_time,
                        'crawl_time': datetime.now().strftime('%Y-%m-%d'),
                        'title': clean_text(article_title),
                        'content_clean': clean_text(content_text)
                    })
                    print(f"    ✓ 匹配并提取: {article_title[:40]}...")
                    found_count += 1
                else:
                    # print(f"    - 跳过 (日期不匹配: {publish_time or '未知'})")
                    pass
                    
            except Exception as e:
                print(f"    ✗ 处理失败 {full_url}: {e}")
                
    return True

def find_next_page_url(soup, current_url):
    """查找'下页'链接"""
    pagination_div = soup.find('div', class_=lambda x: x and 'pagination' in x)
    if not pagination_div:
        return None
    
    next_link = pagination_div.find('a', string=lambda x: x and '下页' in str(x))
    if not next_link:
        # 尝试查找 class 为 p_next 的 span 下的 a
        next_span = pagination_div.find('span', class_=lambda x: x and 'p_next' in x)
        if next_span:
            next_link = next_span.find('a')
            
    if next_link:
        href = next_link.get('href', '')
        if href and 'javascript' not in href:
            return urljoin(current_url, href)
    return None

def crawl_news(target_date, max_depth=10):
    """
    抓取指定日期的新闻
    
    Args:
        target_date: 目标日期 (MM-DD)
        max_depth: 最大抓取深度
    
    Returns:
        List[Dict]: 新闻列表
    """
    base_domain_url = 'https://dean.xjtu.edu.cn/'
    session = get_authorized_session(base_domain_url)
    
    urls = [
        'https://dean.xjtu.edu.cn/jxxx/jxdt.htm', 
        'https://dean.xjtu.edu.cn/jxxx/jxtz2.htm', 
    ]
    
    all_results = []
    
    for start_url in urls:
        print(f"\n开始处理栏目: {start_url}")
        current_url = start_url
        page_num = 1
        
        while current_url and page_num <= max_depth:
            print(f"  正在处理第 {page_num}/{max_depth} 页: {current_url}")
            try:
                rsp = session.get(current_url, timeout=10)
                rsp.encoding = rsp.apparent_encoding
                soup = BeautifulSoup(rsp.text, 'html.parser')
                
                # 提取并过滤
                extract_news_from_page(session, soup, current_url, target_date, all_results, page_num)
                
                # 查找下一页
                current_url = find_next_page_url(soup, current_url)
                page_num += 1
            except Exception as e:
                print(f"  ✗ 栏目处理中断: {e}")
                break
                
    return all_results

def main():
    parser = argparse.ArgumentParser(description='抓取教务处指定日期的公告')
    parser.add_argument('--date', type=str, help='目标日期 (MM-DD)，默认为今天')
    parser.add_argument('--depth', type=int, default=5, help='每类栏目最大抓取页数，默认为10')
    args = parser.parse_args()
    
    target_date = args.date if args.date else datetime.now().strftime('%m-%d')
    max_depth = args.depth
    
    print(f"目标日期: {target_date}, 最大深度: {max_depth}")
    
    all_results = crawl_news(target_date, max_depth)
    
    # 保存结果
    if all_results:
        output_file = f'news_results_{target_date}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n{'='*60}")
        print(f"完成！在 {target_date} 共找到 {len(all_results)} 条新闻。")
        print(f"结果已保存至: {output_file}")
        print(f"{'='*60}")
    else:
        print(f"\n未找到 {target_date} 的任何新闻。")

if __name__ == "__main__":
    main()
