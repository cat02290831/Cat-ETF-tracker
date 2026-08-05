import os
import glob
import requests
import pandas as pd
from datetime import datetime

DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)
TODAY = datetime.now().strftime("%Y-%m-%d")

def fetch_00981a():
    """ 抓取 00981A 統一投信持股 """
    url = "https://www.ezmoney.com.tw/API/Fund/GetETFData"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }
    payload = {"FundCode": "00981A"}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        # 解析統一投信 JSON 結構
        df = pd.DataFrame(data['Data']['Holdings'])
        df = df[['StockCode', 'StockName', 'Ratio']]
        df.columns = ['stock_code', 'stock_name', 'weight']
        df['weight'] = df['weight'].astype(float)
        return df
    except Exception as e:
        print(f"[00981A] 統一投信抓取失敗: {e}")
        return pd.DataFrame()

def fetch_00991a():
    """ 抓取 00991A 復華投信持股 """
    url = "https://www.fhtrust.com.tw/ETF/etf_detail/00991A"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        # 使用 pandas 直接解析 HTML 表格
        tables = pd.read_html(res.text)
        # 取得包含持股的表格 (通常為第一或第二個表格)
        for table in tables:
            if '股票名稱' in str(table) or '權重' in str(table):
                df = table.copy()
                df = df.iloc[:, [0, 1, 2]] # 拿前三欄：代號、名稱、比例
                df.columns = ['stock_code', 'stock_name', 'weight']
                df['weight'] = df['weight'].astype(str).str.replace('%', '').astype(float)
                return df
        return pd.DataFrame()
    except Exception as e:
        print(f"[00991A] 復華投信抓取失敗: {e}")
        return pd.DataFrame()

def build_webpage(results):
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
    </style>
</head>
<body>
    <div class="container">
        <h2 class="text-center my-3 fw-bold">ETF 主動持股每日追蹤儀表板</h2>
        <p class="text-center text-muted mb-4">更新日期：{TODAY}</p>
        <div class="row">
    """
    
    for fund_code, df in results.items():
        html_content += f"""
        <div class="col-md-6">
            <div class="card">
                <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                    <span>{fund_code} 官網即時持股</span>
                    <span class="badge bg-primary">共 {len(df)} 檔</span>
                </div>
                <div class="card-body">
                    <table class="table table-hover align-middle">
                        <thead class="table-light">
                            <tr>
                                <th>代號</th>
                                <th>股票名稱</th>
                                <th>持股權重 (%)</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        for _, row in df.iterrows():
            html_content += f"""
                            <tr>
                                <td><strong>{row['stock_code']}</strong></td>
                                <td>{row['stock_name']}</td>
                                <td class="text-primary fw-bold">{row['weight']}%</td>
                            </tr>
            """
        html_content += """
                        </tbody>
                    </table>
                </div>
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
    targets = {"00981A": fetch_00981a, "00991A": fetch_00991a}
    results = {}
    
    for code, fetch_fn in targets.items():
        df_today = fetch_fn()
        if not df_today.empty:
            results[code] = df_today
            df_today.to_csv(os.path.join(DATA_DIR, f"{code}_{TODAY}.csv"), index=False, encoding="utf-8-sig")
            
    if results:
        build_webpage(results)

if __name__ == "__main__":
    main()
