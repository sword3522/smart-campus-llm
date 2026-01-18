import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json
import os
from datetime import datetime

def clean_text_for_excel(text):
    """清理文本中的非法字符，使其可以写入Excel"""
    if not text:
        return text
    
    # Excel不允许的字符：ASCII控制字符（除了换行符\n=10, 回车符\r=13, 制表符\t=9）
    # 移除其他控制字符（0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F）
    # 保留：\n (10), \r (13), \t (9)
    cleaned = ''
    for char in text:
        code = ord(char)
        # 允许的字符：可打印字符、换行符、回车符、制表符
        if code >= 32 or code in [9, 10, 13]:
            cleaned += char
        else:
            # 替换为空格
            cleaned += ' '
    
    # 移除其他可能导致问题的字符（如零宽字符）
    # 移除零宽空格、零宽非断空格等
    cleaned = re.sub(r'[\u200B-\u200D\uFEFF]', '', cleaned)
    
    return cleaned

def extract_news_from_page(soup, base_url, news_data, page_num):
    """从当前页面提取所有新闻数据"""
    # 找到列表部分：<ul class="wow fadeInUp list"> 或包含 list 类的 ul
    list_ul = soup.find('ul', class_='list')
    if not list_ul:
        # 尝试查找包含 'list' 类的 ul
        list_ul = soup.find('ul', class_=lambda x: x and 'list' in x)
    
    if not list_ul:
        print(f"  未找到列表元素")
        return False
    
    # 遍历每个列表项
    list_items = list_ul.find_all('li')
    print(f"  第 {page_num} 页：找到 {len(list_items)} 个列表项")
    
    for idx, li in enumerate(list_items, 1):
        # 找到 <a> 标签
        link = li.find('a')
        if link:
            href = link.get('href', '')
            
            # 构建完整URL
            if href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(base_url, href)
            
            print(f"    【项目 {idx}/{len(list_items)}】", end=' ')
            print(f"{full_url}")
            
            try:
                # 访问新闻页面
                news_response = requests.get(full_url, timeout=10)
                news_response.encoding = news_response.apparent_encoding
                
                # 解析新闻页面
                news_soup = BeautifulSoup(news_response.text, 'html.parser')
                
                # 提取题目（从 class="art-tit cont-tit" 中的 h3 标签）
                article_title = None
                publish_date = None
                art_tit_div = news_soup.find('div', class_='art-tit cont-tit')
                if art_tit_div:
                    # 提取题目（从 h3 标签）
                    h3_tag = art_tit_div.find('h3')
                    if h3_tag:
                        article_title = h3_tag.get_text().strip()
                    
                    # 提取发布日期（从包含"发布日期"的span标签）
                    date_spans = art_tit_div.find_all('span')
                    for span in date_spans:
                        span_text = span.get_text().strip()
                        if '发布日期' in span_text or '发布时间' in span_text:
                            # 提取日期部分，例如 "发布日期: 2025-11-19" -> "2025-11-19"
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', span_text)
                            if date_match:
                                publish_date = date_match.group(1)
                            else:
                                # 如果没有匹配到标准格式，尝试提取其他格式的日期
                                publish_date = span_text.replace('发布日期:', '').replace('发布时间:', '').strip()
                            break
                
                # 提取主体内容（从 class="v_news_content"）
                content_text = None
                content_div = news_soup.find('div', class_='v_news_content')
                if content_div:
                    # 提取文本，使用空格作为分隔符
                    content_text = content_div.get_text(separator=' ', strip=True)
                    
                    # 清理文本：移除HTML格式导致的换行和多余空白
                    content_text = re.sub(r' +', ' ', content_text)
                    content_text = re.sub(r' \n', '\n', content_text)
                    content_text = re.sub(r'\n ', '\n', content_text)
                    content_text = re.sub(r'\n{2,}', '\n', content_text)
                    content_text = content_text.strip()
                    
                    # 进一步清理：将单行中的换行替换为空格（保留段落之间的换行）
                    lines = content_text.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if line:
                            line = re.sub(r'\s+', ' ', line)
                            cleaned_lines.append(line)
                    content_text = '\n'.join(cleaned_lines)
                
                # 如果题目为空，尝试从页面标题获取
                if not article_title:
                    title_tag = news_soup.find('title')
                    if title_tag:
                        article_title = title_tag.get_text().strip()
                
                # 如果发布时间为空，使用列表中的日期
                if not publish_date:
                    span_tag = li.find('span')
                    if span_tag:
                        publish_date = span_tag.get_text().strip()
                
                # 清理文本中的非法字符
                article_title = clean_text_for_excel(article_title) if article_title else None
                publish_date = clean_text_for_excel(publish_date) if publish_date else None
                content_text = clean_text_for_excel(content_text) if content_text else None
                
                # 处理发布时间，精确到天
                publish_time = ""
                if publish_date:
                    # 尝试提取 YYYY-MM-DD 格式
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', publish_date)
                    if date_match:
                        publish_time = date_match.group(1)
                    else:
                        # 如果无法提取，使用原值
                        publish_time = publish_date.split()[0] if ' ' in publish_date else publish_date
                
                # 筛选：如果题目、时间或内容是"未找到"或为空，则不保存
                if article_title and article_title != '未找到' and \
                   publish_time and publish_time != '未找到' and \
                   content_text and content_text != '未找到':
                    # 存储数据（JSON格式）
                    # ID将在保存时统一分配，这里先使用临时ID
                    news_data.append({
                        'id': '',  # 临时ID，保存时会重新分配
                        'url': full_url,  # 新闻页面URL
                        'source': '教务处',  # 固定值
                        'publish_time': publish_time,  # 发布时间，精确到天
                        'crawl_time': datetime.now().strftime('%Y-%m-%d'),  # 抓取时间
                        'title': article_title,  # 标题
                        'content_raw': '',  # 空字符串
                        'content_clean': content_text,  # 清洗后的内容
                        'attachments': []  # 空数组
                    })
                    print(f"      ✓ 成功提取: {article_title[:50]}...")
                else:
                    print(f"      ✗ 数据不完整，跳过保存（题目: {article_title or '未找到'}, 时间: {publish_time or '未找到'}, 内容: {'有' if content_text and content_text != '未找到' else '未找到'}）")
                
            except requests.exceptions.RequestException as e:
                print(f"      ✗ 请求失败: {e}，跳过此条数据")
                # 不保存错误数据
            except Exception as e:
                print(f"      ✗ 处理失败: {e}，跳过此条数据")
                # 不保存错误数据
    
    return True

def find_next_page_url(soup, current_url):
    """查找"下页"链接"""
    # 查找分页div（支持多个class名）
    pagination_div = soup.find('div', class_=lambda x: x and 'pagination' in x)
    if not pagination_div:
        return None
    
    # 查找"下页"链接：<span class="p_next p_fun"><a href="...">下页</a></span>
    # 或者查找包含"下页"文本的链接
    next_span = pagination_div.find('span', class_=lambda x: x and 'p_next' in x)
    if next_span:
        # 检查是否有链接（不是 p_next_d，而是 p_next p_fun）
        classes = next_span.get('class', [])
        if 'p_fun' in classes and 'p_next_d' not in classes:
            next_link = next_span.find('a')
            if next_link:
                href = next_link.get('href', '')
                if href:
                    # 构建完整URL
                    if href.startswith('http'):
                        return href
                    else:
                        return urljoin(current_url, href)
    
    # 备用方案：直接查找包含"下页"文本的链接
    next_link = pagination_div.find('a', string=lambda x: x and '下页' in str(x))
    if next_link:
        href = next_link.get('href', '')
        if href:
            if href.startswith('http'):
                return href
            else:
                return urljoin(current_url, href)
    
    return None

def save_to_json(news_data, json_filename, url_index):
    """保存数据到JSON文件（支持追加模式）"""
    try:
        if not news_data:
            return
        
        # 过滤掉无效数据（title、publish_time或content_clean为"未找到"或为空的）
        valid_data = []
        for item in news_data:
            title = item.get('title', '')
            publish_time = item.get('publish_time', '')
            content = item.get('content_clean', '')
            if title and title != '未找到' and \
               publish_time and publish_time != '未找到' and \
               content and content != '未找到':
                valid_data.append(item)
        
        if not valid_data:
            print(f"  没有有效数据需要保存")
            return
        
        # 如果文件已存在，读取现有数据并合并
        if os.path.exists(json_filename):
            try:
                with open(json_filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                # 过滤现有数据中的无效数据
                existing_valid = []
                for item in existing_data:
                    title = item.get('title', '')
                    publish_time = item.get('publish_time', '')
                    content = item.get('content_clean', '')
                    if title and title != '未找到' and \
                       publish_time and publish_time != '未找到' and \
                       content and content != '未找到':
                        existing_valid.append(item)
                
                # 合并数据（基于URL去重，避免重复）
                existing_urls = {item.get('url', '') for item in existing_valid}
                new_data = [item for item in valid_data if item.get('url', '') not in existing_urls]
                
                if new_data:
                    # 重新分配ID
                    max_id = 0
                    for item in existing_valid:
                        item_id = item.get('id', '')
                        if item_id and item_id.startswith('unique_id_'):
                            try:
                                id_num = int(item_id.replace('unique_id_', ''))
                                max_id = max(max_id, id_num)
                            except:
                                pass
                    
                    # 为新数据分配ID
                    for idx, item in enumerate(new_data):
                        item['id'] = f"unique_id_{max_id + idx + 1}"
                    
                    # 合并新旧数据
                    all_data = existing_valid + new_data
                else:
                    # 没有新数据，使用现有有效数据
                    all_data = existing_valid
                    # 确保现有数据也有ID
                    for idx, item in enumerate(all_data):
                        if not item.get('id') or item.get('id') == '':
                            item['id'] = f"unique_id_{idx + 1}"
            except Exception as e:
                print(f"  警告：读取现有文件失败，将覆盖文件: {e}")
                all_data = valid_data
        else:
            # 文件不存在，创建新文件
            all_data = valid_data
            # 为新数据分配ID
            for idx, item in enumerate(all_data):
                item['id'] = f"unique_id_{idx + 1}"
        
        # 先保存到临时文件，成功后再替换原文件
        temp_filename = json_filename + '.tmp'
        json_str = json.dumps(all_data, ensure_ascii=False, indent=2)
        with open(temp_filename, 'w', encoding='utf-8') as f:
            f.write(json_str)
        
        # 替换原文件
        if os.path.exists(json_filename):
            os.replace(temp_filename, json_filename)
        else:
            os.rename(temp_filename, json_filename)
        
        print(f"  ✓ 已保存 {len(all_data)} 条数据到 {json_filename}")
        
    except Exception as e:
        print(f"  ✗ 保存文件失败: {e}")
        # 如果保存失败，尝试保存到备份文件
        try:
            backup_filename = json_filename.replace('.json', f'_backup_{url_index}.json')
            json_str = json.dumps(news_data, ensure_ascii=False, indent=2)
            with open(backup_filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"  ✓ 已保存到备份文件: {backup_filename}")
        except Exception as e2:
            print(f"  ✗ 备份保存也失败: {e2}")

# 教学动态， 教学通知， 培养方案
urls = ['https://dean.xjtu.edu.cn/jxxx/jxdt.htm', 'https://dean.xjtu.edu.cn/jxxx/jxtz2.htm', 'https://dean.xjtu.edu.cn/jxxx/pyfa.htm']
# urls = ['https://dean.xjtu.edu.cn/jxxx/jxtz2.htm']

for i, url in enumerate(urls):
    print(f"\n{'='*80}")
    print(f"开始处理: {url}")
    print(f"{'='*80}\n")
    
    # 存储所有新闻数据
    news_data = []
    current_url = url
    page_num = 1
    
    while current_url:
        print(f"\n正在处理第 {page_num} 页: {current_url}")
        
        try:
            # 获取当前页面
            rsp = requests.get(current_url, timeout=10)
            rsp.encoding = rsp.apparent_encoding
            
            # 解析HTML
            soup = BeautifulSoup(rsp.text, 'html.parser')
            
            # 提取当前页的所有新闻
            page_start_count = len(news_data)  # 记录处理前的数据量
            if extract_news_from_page(soup, current_url, news_data, page_num):
                # 每处理完一页就保存一次（实时保存）
                if len(news_data) > page_start_count:
                    save_to_json(news_data, f'news_data.json', i)
                
                # 查找"下页"链接
                next_url = find_next_page_url(soup, current_url)
                if next_url:
                    print(f"  找到下页链接: {next_url}")
                    current_url = next_url
                    page_num += 1
                else:
                    print(f"  已到达最后一页")
                    current_url = None
            else:
                print(f"  提取失败，停止处理")
                # 即使提取失败，也保存已有数据
                if news_data:
                    save_to_json(news_data, f'news_data.json', i)
                break
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ 请求失败: {e}")
            # 即使请求失败，也保存已有数据
            if news_data:
                save_to_json(news_data, f'news_data.json', i)
            break
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            # 即使处理失败，也保存已有数据
            if news_data:
                save_to_json(news_data, f'news_data.json', i)
            break
    
    # 最终保存（确保所有数据都已保存）
    if news_data:
        save_to_json(news_data, f'news_data.json', i)
        print(f"\n{'='*80}")
        print(f"✓ 最终保存：共 {len(news_data)} 条新闻数据")
        print(f"  共处理了 {page_num} 页")
        print(f"{'='*80}")
    else:
        print(f"\n✗ 没有提取到任何数据")
