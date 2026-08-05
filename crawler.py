import os
import glob
import requests
import pandas as pd
from datetime import datetime

DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)
TODAY = datetime.now().strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_etf_holdings_twse(fund_code):
    """ 從證交所 API 抓取 ETF 最新持股 """
    url = f"https://www.twse.com.tw/rwd/zh/ETF/fundHolding?response=json&stockNo={fund_code}"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        
        if data.get("stat") == "OK" and "data" in data:
            df = pd.DataFrame(data["data"])
            df = df.iloc[:, [0, 1, 2]]
            df.columns = ["stock_code", "stock_name", "weight"]
            df["weight"] = df["weight"].astype(str).str.replace("%", "").astype(float)
            return df
    except Exception as e:
        print(f"[{fund_code}] API 讀取異常: {e}")
    
    return pd.DataFrame(columns=["stock_code", "stock_name", "weight"])

def compare_holdings(fund_code, df_today):
    """ 比對今日持股與最新一次歷史紀錄的差異 """
    # 搜尋歷史資料檔案
    files = sorted(glob.glob(os.path.join(DATA_DIR, f"{fund_code}_*.csv")))
    
    # 排除今天的檔案，找到前一次的歷史檔案
    files_before_today = [f for f in files if not f.endswith(f"{TODAY}.csv")]
    
    if not files_before_today:
        # 第一天沒有歷史資料，全部標記為新進或現有持股
        df_today['diff'] = df_today['weight']
        df_today['status'] = '現有持股'
        return df_today
    
    # 讀取最近一次的歷史檔案
    last_file = files_before_today[-1]
    df_last = pd.read_csv(last_file)
    
    # 合併今天與前一次的持股進行比較
    merged = pd.merge(df_today, df_last, on=['stock_code', 'stock_name'], how='outer', suffixes=('_today', '_last'))
    merged['weight_today'] = merged['weight_today'].fillna(0)
    merged['weight_last'] = merged['weight_last'].fillna(0)
    
    # 計算比例差額 (今日 - 前一次)
    merged['diff'] = (merged['weight_today'] - merged['weight_last']).round(2)
    
    # 判定變動狀態
    def get_status(row):
        if row['weight_last'] == 0:
            return '新進'
        elif row['weight_today'] == 0:
            return '剔除'
        elif row['diff'] > 0:
            return '加碼'
        elif row['diff'] < 0:
            return '減碼'
        else:
            return '持平'
            
    merged['status'] = merged.apply(get_status, axis=1)
    return merged

def build_webpage(results):
    """ 生成支援顯示「每日變動」的 HTML 儀表板 """
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>00981A & 00991A 每日持股變動</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f4f6f9; padding: 25px; }}
        .card {{ margin-bottom: 20px; border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        .badge-新進 {{ background-color: #198754; }}
        .badge-加碼 {{ background-color: #d63384; }}
        .badge-減碼 {{ background-color: #0d6efd; }}
        .badge-剔除 {{ background-color: #dc3545; }}
        .badge-持平 {{ background-color: #6c757d; }}
        .badge-現有持股 {{ background-color: #212529; }}
    </style>
</head>
<body>
    <div class="container">
        <h2 class="text-center my-3 fw-bold">ETF 主動持股每日變動儀表板</h2>
        <p class="text-center text-muted mb-4">資料更新日期：{TODAY}</p>
        <div class="row">
    """
    
    has_data = False
    for fund_code, df in results.items():
        if not df.empty:
            has_data = True
            # 只篩選有變動的（加碼、減碼、新進、剔除），若第一天則全顯示
            changes = df[df['status'] != '持平'].sort_values(by='diff', ascending=False)
            
            html_content += f"""
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                        <span>{fund_code} 當日持股變動</span>
                        <span class="badge bg-secondary">異動 {len(changes)} 檔</span>
                    </div>
                    <div class="card-body">
                        <table class="table table-hover align-middle">
                            <thead class="table-light">
                                <tr>
                                    <th>股票代號/名稱</th>
                                    <th>狀態</th>
                                    <th>今日權重</th>
                                    <th>變動幅度</th>
                                </tr>
                            </thead>
                            <tbody>
            """
            for _, row in changes.iterrows():
                stock_label = f"<strong>{row['stock_code']}</strong> {row['stock_name']}"
                diff_str = f"+{row['diff']}%" if row['diff'] > 0 else f"{row['diff']}%"
                if row['status'] == '現有持股':
                    diff_str = "-"
                    
                html_content += f"""
                                <tr>
                                    <td>{stock_label}</td>
                                    <td><span class="badge badge-{row['status']}">{row['status']}</span></td>
                                    <td>{row['weight_today'] if 'weight_today' in row else row['weight']}%</td>
                                    <td class="{'text-danger fw-bold' if row['diff']>0 else 'text-primary fw-bold'}">{diff_str}</td>
                                </tr>
                """
            html_content += """
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            """
            
    if not has_data:
        html_content += """
        <div class="col-12 text-center my-5">
            <div class="alert alert-info" role="alert">
                今日投信資料更新中或連線維護中，請稍後重試。
            </div>
        </div>
        """
        
    html_content += """
        </div>
    </div>
</body>
</html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def main():
    targets = ["00981A", "00991A"]
    results = {}
    
    for code in targets:
        df_today = fetch_etf_holdings_twse(code)
        
        if not df_today.empty:
            # 進行新舊持股比對，標註變動幅度
            df_diff = compare_holdings(code, df_today)
            results[code] = df_diff
            
            # 將今天的持股儲存為 CSV（供明天比對使用）
            df_today.to_csv(os.path.join(DATA_DIR, f"{code}_{TODAY}.csv"), index=False, encoding="utf-8-sig")
            
    build_webpage(results)
    print("已成功比對變動並更新 index.html！")

if __name__ == "__main__":
    main()
