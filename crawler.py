import os
import glob
import requests
import pandas as pd
from datetime import datetime

DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)
TODAY = datetime.now().strftime("%Y-%m-%d")

# 模擬完整瀏覽器 Header，防止被投信防爬蟲機制阻擋
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}

def fetch_00981a():
    """ 抓取 00981A 統一投信持股 """
    url = "https://www.ezmoney.com.tw/API/Fund/GetETFData"
    payload = {"FundCode": "00981A"}
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            holdings = data.get('Data', {}).get('Holdings', [])
            if holdings:
                df = pd.DataFrame(holdings)[['StockCode', 'StockName', 'Ratio']]
                df.columns = ['stock_code', 'stock_name', 'weight']
                df['weight'] = df['weight'].astype(float)
                return df
    except Exception as e:
        print(f"[00981A] 抓取失敗: {e}")
    return pd.DataFrame()

def fetch_00991a():
    """ 抓取 00991A 復華投信持股 """
    url = "https://www.fhtrust.com.tw/ETF/etf_detail/00991A"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            tables = pd.read_html(res.text)
            for table in tables:
                if '股票名稱' in str(table) or '權重' in str(table):
                    df = table.iloc[:, [0, 1, 2]].copy()
                    df.columns = ['stock_code', 'stock_name', 'weight']
                    df['weight'] = df['weight'].astype(str).str.replace('%', '').astype(float)
                    return df
    except Exception as e:
        print(f"[00991A] 抓取失敗: {e}")
    return pd.DataFrame()

def build_webpage(results):
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>00981A & 00991A 持股追蹤儀表板</title>
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
    
    if not results:
        html_content += """
        <div class="col-12 text-center my-5">
            <div class="alert alert-warning" role="alert">
                今日投信官網尚未更新持股或連線維護中，請稍後重試。
            </div>
        </div>
        """
    else:
        for fund_code, df in results.items():
            html_content += f"""
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                        <span>{fund_code} 即時持股</span>
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
    
    # 強制產出 index.html
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
            
    build_webpage(results)

if __name__ == "__main__":
    main()
