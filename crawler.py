import os
import json
import re
from datetime import datetime
from curl_cffi import requests

def fetch_safe_draw_data():
    url = "https://www.twse.com.tw/rwd/zh/announcement/publicForm?response=json"
    
    save_path = "data.json"
    
    print("正在透過【瀏覽器指紋偽裝】通道讀取抽籤日程...")
    
    try:
        response = requests.get(url, impersonate="chrome", timeout=15)
        response.raise_for_status()
        
        res_data = response.json()
        if isinstance(res_data, str):
            res_data = json.loads(res_data)
            
        fields = res_data.get("fields", [])
        raw_data = res_data.get("data", [])
        
        # 定位所需欄位的索引值
        try:
            stock_code_index = fields.index("證券代號")
            start_date_index = fields.index("申購開始日")
            end_date_index = fields.index("申購結束日")
        except ValueError:
            # 防呆：如果欄位名稱有變，帶入預設常見索引
            stock_code_index, start_date_index, end_date_index = 2, 5, 6

        today = datetime.now().date()
        filtered_stocks = []
        four_digit_pattern = re.compile(r"^\d{4}$")
        
        # 輔助函式：將民國年月日（115/06/05）轉為 Python date 物件
        def parse_tw_date(date_str):
            date_str = date_str.strip()
            if not date_str:
                return None
            try:
                year_part, month_part, day_part = date_str.split("/")
                western_year = int(year_part) + 1911
                return datetime(western_year, int(month_part), int(day_part)).date()
            except:
                return None

        for row in raw_data:
            if not isinstance(row, list) or len(row) <= max(stock_code_index, start_date_index, end_date_index):
                continue
                
            # 1. 篩選條件：必須是 4 位純數字個股
            stock_code_str = row[stock_code_index].strip()
            if not four_digit_pattern.match(stock_code_str):
                continue
                
            # 2. 解析申購開始與結束日期
            start_date = parse_tw_date(row[start_date_index])
            end_date = parse_tw_date(row[end_date_index])
            
            if not start_date or not end_date:
                continue
                
            # 3. 【核心邏輯變更】只要今天還沒超過申購截止日，就保留！
            if today <= end_date:
                # 自動判斷當前申購狀態
                if start_date <= today <= end_date:
                    status_text = "申購中"
                else:
                    status_text = "即將申購"
                
                # 組裝字典，並貼心加入 status 欄位讓前端可以直接用
                stock_item = {}
                for i, field_name in enumerate(fields):
                    if i < len(row):
                        stock_item[field_name] = row[i]
                
                stock_item["申購狀態"] = status_text
                filtered_stocks.append(stock_item)

        # 依據結束日期由近到遠排序，方便使用者優先看到快截止的股票
        filtered_stocks.sort(key=lambda x: parse_tw_date(x.get("申購結束日", "0/01/01")) or today)

        # 寫入 data.json
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(filtered_stocks, f, ensure_ascii=False, indent=4)
            
        print("--------------------------------------------------")
        print(f"✅ 資料更新成功！已篩選出所有「未截止」的個股")
        print(f"📂 檔案已儲存至: {save_path}")
        print(f"📊 當前可參與的抽籤檔盤點: {len(filtered_stocks)} 筆")
        print("--------------------------------------------------")
        
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    fetch_safe_draw_data()