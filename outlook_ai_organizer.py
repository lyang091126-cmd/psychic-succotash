import win32com.client
import pandas as pd
import datetime
import os
import json
import re
import openpyxl
import sys
sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# 配置区域 (Configuration)
# ==========================================
# 请通过环境变量 GEMINI_API_KEY 设置密钥（不要写死在代码里）。如果没有，请去 Google AI Studio 申请一个。
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
DAYS_TO_EXTRACT = 30 # 提取最近 30 天的邮件
EXPORT_FILENAME = "智能邮件整理报告.xlsx"

# 是否开启真实的 AI 分析。如果设为 False，将只提取邮件但不调用 AI，方便快速测试数据。
ENABLE_AI_ANALYSIS = True 

# ==========================================

if ENABLE_AI_ANALYSIS:
    try:
        from google import genai
        from google.genai import types
        # 初始化 Gemini 客户端
        client = genai.Client(api_key=GEMINI_API_KEY)
    except ImportError:
        print("未安装 google-genai 库。请运行: pip install google-genai")
        ENABLE_AI_ANALYSIS = False


def extract_emails_from_outlook(days=30):
    """
    从本地 Outlook 提取指定天数内的邮件。
    遍历所有登录的账号 (Stores)。
    """
    print(f"[*] 正在连接本地 Outlook，准备提取最近 {days} 天的邮件...")
    try:
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    except Exception as e:
        print(f"连接 Outlook 失败，请检查 Outlook 是否已打开且正常运行: {e}")
        return []
    
    # 计算日期界限，并将格式转为 Outlook 可识别的字符串 (MM/DD/YYYY HH:MM)
    date_limit = datetime.datetime.now() - datetime.timedelta(days=days)
    filter_date_str = date_limit.strftime("%m/%d/%Y %H:%M %p")
    filter_str = f"[ReceivedTime] >= '{filter_date_str}'"
    
    extracted_data = []
    
    # 遍历 Outlook 中挂载的所有账户 (Stores)
    for account in outlook.Folders:
        print(f"  -> 正在扫描账户: {account.Name}")
        try:
            # 获取收件箱 (默认文件夹类型 6 是收件箱)
            inbox = account.Folders("收件箱") 
        except Exception as e:
            try:
                inbox = account.Folders("Inbox")
            except:
                print(f"     [跳过] 无法在 {account.Name} 中找到收件箱。")
                continue
        
        try:
            print(f"     正在按时间过滤 ({days}天内)...")
            # 使用 Restrict 进行过滤，速度远快于遍历所有邮件
            messages = inbox.Items.Restrict(filter_str)
            # 排序方便我们处理最新的
            messages.Sort("[ReceivedTime]", True) 
            
            count = 0
            # 这里强制将 COM 对象转为 list 防止在循环中一直保持连接池
            for msg in messages:
                try:
                    # 只处理正常的邮件类型 (olMail)
                    if getattr(msg, "Class", None) != 43:
                        continue
                        
                    received_time = getattr(msg, "ReceivedTime", None)
                    if not received_time:
                        continue
                    
                    # datetime 转换处理时区问题
                    msg_date = datetime.datetime(
                        received_time.year, received_time.month, received_time.day,
                        received_time.hour, received_time.minute, received_time.second
                    )
                    
                    subject = getattr(msg, "Subject", "")
                    sender = getattr(msg, "SenderName", "")
                    body = getattr(msg, "Body", "")
                    
                    # 简单预过滤
                    lower_body = body.lower()
                    if "unsubscribe" in lower_body or "退订" in lower_body or "noreply" in sender.lower():
                        pass
                    
                    extracted_data.append({
                        "Account": account.Name,
                        "Date": msg_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "Sender": sender,
                        "Subject": subject,
                        "BodySnippet": body[:1000] # 只截取前 1000 字符，避免 Token 超限
                    })
                    count += 1
                except Exception as e:
                    # 某些邮件对象可能损坏
                    continue
                    
            print(f"     ✅ 从 {account.Name} 提取了 {count} 封近期的邮件。")
        except Exception as e:
            print(f"     [报错] 读取 {account.Name} 失败: {e}")
        
    return extracted_data

def analyze_with_ai(email):
    """
    调用大语言模型对邮件进行分析分类和总结。
    """
    if not ENABLE_AI_ANALYSIS or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return {
            "Category": "未分析",
            "Summary": "未配置 API Key",
            "ImportantInfo": ""
        }
        
    prompt = f"""
    你是一个专业的私人助理，擅长整理和分类邮件。
    请阅读以下邮件内容，判断其是否是“垃圾邮件”或“广告营销邮件”。
    如果是垃圾或广告邮件，请将 is_spam 设为 true。
    
    如果不是垃圾邮件，请为其分配一个最合适的 Category (分类)，例如：
    - 上课/学术
    - 校招/求职
    - 工作/项目
    - 通知/提醒
    - 个人事务
    - 其他
    
    然后，提取出邮件的核心 Summary (摘要，50字内)，并提炼出 ImportantInfo (重要信息：如时间、地点、Deadline、面试链接等，没有则留空)。

    请严格输出 JSON 格式，不要包含 markdown 标记。
    格式要求：
    {{
      "is_spam": false,
      "Category": "校招/求职",
      "Summary": "...",
      "ImportantInfo": "..."
    }}

    发件人: {email['Sender']}
    主题: {email['Subject']}
    正文片段: {email['BodySnippet']}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"     [API错误] 分析邮件失败: {str(e)}")
        return {
             "is_spam": False,
             "Category": "分析失败",
             "Summary": "AI调用出错",
             "ImportantInfo": ""
        }

def main():
    print("========================================")
    print("      Outlook AI 邮件智能整理工具       ")
    print("========================================\n")
    
    # 1. 提取邮件
    emails = extract_emails_from_outlook(days=DAYS_TO_EXTRACT)
    print(f"\n[*] 共提取到 {len(emails)} 封邮件，准备进行 AI 分析...\n")
    
    if len(emails) == 0:
        print("没有找到近期邮件。退出程序。")
        return
        
    if not ENABLE_AI_ANALYSIS or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("⚠️ 警告: 未配置 GEMINI_API_KEY，将跳过 AI 分析阶段。如需完整体验，请修改脚本开头的配置。\n")

    # 2. AI 分析
    processed_data = []
    for i, email in enumerate(emails, 1):
        print(f"[{i}/{len(emails)}] 正在分析: {email['Subject']} ...")
        
        ai_result = analyze_with_ai(email)
        
        # 过滤垃圾邮件和广告
        if ai_result.get("is_spam", False):
            print("  -> 🗑️ 被判定为垃圾/广告，已忽略。")
            continue
            
        print(f"  -> 归类为: [{ai_result.get('Category', '未分类')}]")
        
        # 将分析结果合并
        processed_data.append({
            "接收时间": email["Date"],
            "账户": email["Account"],
            "发件人": email["Sender"],
            "邮件主题": email["Subject"],
            "AI 智能分类": ai_result.get("Category", "未分类"),
            "一句话摘要": ai_result.get("Summary", ""),
            "核心要点 (时间/地点/链接)": ai_result.get("ImportantInfo", "")
        })
        
    # 3. 导出为 Excel
    if processed_data:
        df = pd.DataFrame(processed_data)
        
        # 按分类排序，方便查看
        df = df.sort_values(by=["AI 智能分类", "接收时间"], ascending=[True, False])
        
        export_path = os.path.join(os.path.dirname(__file__), EXPORT_FILENAME)
        
        # 调整 Excel 格式 (自动换行等)
        writer = pd.ExcelWriter(export_path, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='AI整理报告')
        
        # 自动调整列宽
        worksheet = writer.sheets['AI整理报告']
        for idx, col in enumerate(df.columns, 1):
            worksheet.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = 20
        
        writer.close()
        
        print("\n========================================")
        print(f"🎉 处理完成！共整理出 {len(processed_data)} 封有效邮件。")
        print(f"📊 报告已保存至: {export_path}")
        print("========================================")
    else:
        print("\n所有的邮件都被判定为垃圾邮件，或者没有成功分析的邮件，未能生成报告。")


if __name__ == "__main__":
    main()
