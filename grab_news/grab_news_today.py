import requests 
from bs4 import BeautifulSoup
import re
import os
import json
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta


url = 'https://dean.xjtu.edu.cn/'
response = requests.get(url)

# 确保正确识别编码
response.encoding = response.apparent_encoding  # 自动检测编码
print(response.encoding)
# 或者如果知道是UTF-8，可以直接设置：
# response.encoding = 'utf-8'

# with open('response.html', 'w', encoding='utf-8') as f:
#     f.write(response.text)

# 解析HTML并查找所有匹配格式的内容
soup = BeautifulSoup(response.text, 'html.parser')

# 查找所有符合条件的链接
# 格式1: <a href="info/xxx/xxx.htm" target="_blank" title="..."><p><i>[分类]</i><em>标题</em></a><span>日期</span></p>
# 格式2: <a href="info/xxx/xxx.htm" target="_blank" title="..."><i>[分类]</i><em>标题</em></a><span>日期</span>
results = []

# 首先定位到 <div class="tz"> 元素
tz_div = soup.find('div', class_='tz')
if not tz_div:
    print("未找到 <div class='tz'> 元素")
    li_tags = []
else:
    print("成功定位到 <div class='tz'> 元素")
    # 在 tz_div 范围内查找所有的 <li> 标签
    li_tags = tz_div.find_all('li')
    print(f"在 tz div 中找到 {len(li_tags)} 个 <li> 标签")

# 获取昨天的日期，格式为 "MM-DD"
today = (datetime.now() - timedelta(days=1)).strftime('%m-%d')
print(f"昨天的日期: {today}")

for li in li_tags:
    # 提取 <li> 标签的完整HTML内容
    li_html = str(li)
    
    # 提取 href（从 <a> 标签）
    href = None
    link = li.find('a')
    if link:
        href = link.get('href', '')
    
    # 提取 title（从 <a> 标签的 title 属性）
    title = None
    if link:
        title = link.get('title', '')
    
    # 提取 span（日期）
    span_text = None
    span_tag = li.find('span')
    if span_tag:
        span_text = span_tag.get_text().strip()
    
    # 只添加今天的新闻
    if span_text == today:
        results.append({
            'html': li_html,
            'href': href,
            'title': title,
            'span': span_text
        })
        print(f"找到今天的新闻: {title} ({span_text})")

# 访问每个新闻链接，获取对应页面的HTML并提取信息
print(f"\n开始访问 {len(results)} 个新闻链接...\n")

base_url = 'https://dean.xjtu.edu.cn/'
crawl_time = datetime.now().strftime('%Y-%m-%d')
news_data = []

for i, item in enumerate(results, 1):
    if not item['href']:
        print(f"{i}. 跳过：无链接地址")
        continue
    
    # 构建完整的URL（处理相对路径）
    if item['href'].startswith('http'):
        full_url = item['href']
    else:
        full_url = urljoin(base_url, item['href'])
    
    print(f"{i}. 正在访问: {full_url}")
    print(f"   标题: {item['title']}")
    
    try:
        # 请求新闻页面
        news_response = requests.get(full_url, timeout=10)
        news_response.encoding = news_response.apparent_encoding
        
        # 解析新闻页面，提取题目、发布日期和主体内容
        news_soup = BeautifulSoup(news_response.text, 'html.parser')
        
        # 提取题目和发布日期（从 class="art-tit cont-tit"）
        article_title = item['title']  # 默认使用列表中的标题
        publish_date = None
        art_tit_div = news_soup.find('div', class_='art-tit cont-tit')
        if art_tit_div:
            # 提取题目（从 h3 标签，如果存在则使用，否则使用列表中的标题）
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
        
        # 如果页面中没有找到发布日期，尝试从span_text（MM-DD格式）转换为完整日期
        if not publish_date and item['span']:
            # 假设年份是当前年份
            current_year = datetime.now().year
            try:
                month, day = item['span'].split('-')
                publish_date = f"{current_year}-{month}-{day}"
            except:
                pass
        
        # 提取主体内容（从 class="v_news_content"）
        content_text = ""
        content_div = news_soup.find('div', class_='v_news_content')
        if content_div:
            # 方法1：处理段落标签，保留段落结构
            # 将p、div等块级元素转换为段落分隔
            for p_tag in content_div.find_all(['p', 'div']):
                # 在段落标签后添加换行标记
                if p_tag.get_text(strip=True):
                    p_tag.append('\n')
            
            # 提取文本，使用空格作为分隔符（避免HTML标签导致的换行）
            content_text = content_div.get_text(separator=' ', strip=True)
            
            # 清理文本：移除HTML格式导致的换行和多余空白
            # 将多个连续空格替换为单个空格
            content_text = re.sub(r' +', ' ', content_text)
            # 将换行前后的空格去掉
            content_text = re.sub(r' \n', '\n', content_text)
            content_text = re.sub(r'\n ', '\n', content_text)
            # 将多个连续换行替换为单个换行（段落分隔）
            content_text = re.sub(r'\n{2,}', '\n', content_text)
            # 移除行首行尾的空白
            content_text = content_text.strip()
            
            # 如果内容仍然有很多换行，可能是HTML结构导致的，进一步清理
            # 将单行中的换行替换为空格（保留段落之间的换行）
            lines = content_text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line:  # 只保留非空行
                    # 如果行内还有换行，替换为空格
                    line = re.sub(r'\s+', ' ', line)
                    cleaned_lines.append(line)
            content_text = '\n'.join(cleaned_lines)
        
        # 生成唯一ID
        unique_id = f"unique_id_{i}"
        
        # 构建符合 news_data.json 格式的数据
        news_item = {
            "id": unique_id,
            "url": full_url,
            "source": "教务处",
            "publish_time": publish_date if publish_date else "",
            "crawl_time": crawl_time,
            "title": article_title,
            "content_raw": "",
            "content_clean": content_text,
            "attachments": []
        }
        
        news_data.append(news_item)
        
        print(f"   ✓ 成功提取")
        if article_title:
            print(f"   题目: {article_title}")
        if publish_date:
            print(f"   发布日期: {publish_date}")
        if content_text:
            content_preview = content_text[:100].replace('\n', ' ')
            print(f"   内容预览: {content_preview}...")
        
    except requests.exceptions.RequestException as e:
        print(f"   ✗ 请求失败: {e}")
    except Exception as e:
        print(f"   ✗ 处理失败: {e}")
    
    print()

# 保存为JSON文件
if news_data:
    save_dir = '/root/NLP/news_days'
    os.makedirs(save_dir, exist_ok=True)
    filename = f"news_{today}.json"
    save_path = os.path.join(save_dir, filename)
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)
    print(f"\n完成！共处理 {len(news_data)} 条新闻，已保存到 {save_path}")
else:
    print(f"\n未找到昨天的新闻")

