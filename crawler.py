import os
import glob
import requests
import pandas as pd
from datetime import datetime

DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)
TODAY = datetime.now().strftime("%Y-%m-%d")

def fetch_00981a():
    """ 00981A 統一台股增長主動式 ETF """
    url = "https://www.ezmoney.com.tw/ETF/Fund/GetHoldingsAPI?fundCode=00981A"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        df = pd.DataFrame(data['items'])
        df = df[['stock_code', 'stock_name', 'weight']]
        df['weight'] = df['weight'].astype(float)
        return df
    except Exception as e:
        print(f"00981A 抓取失敗: {e}")
        return pd.DataFrame(columns=['stock_code', 'stock_name', 'weight'])

def fetch_00991a():
    """ 00991A 復華台灣未來50主動式 ETF """
    url = "https://www.fhtrust.com.tw/api/ETF/Holdings?symbol=00991A"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        df = pd.DataFrame(data['Holdings'])
        df = df[['code', 'name', 'ratio']]
        df.columns = ['stock_code', 'stock_name', 'weight']
        df['weight'] = df['weight'].astype(float)
        return df
    except Exception as e:
        print(f"00991A 抓取失敗: {e}")
        return pd.DataFrame(columns=['stock_code', 'stock_name', 'weight'])

def compare_holdings(fund_code, df_today):
    files = sorted(glob.glob(os.path.join(DATA_DIR, f"{fund_code}_*.csv")))
    
    if not files:
        df_today['diff'] = df_today['weight']
        df_today['status'] = '新進'
        return df_today
    
    last_file = files[-1]
    df_last = pd.read_csv(last_file)
    
    merged = pd.merge(df_today, df_last, on=['stock_code', 'stock_name'], how='outer', suffixes=('_today', '_last'))
    merged['weight_today'] = merged['weight_today'].fillna(0)
    merged['weight_last'] = merged['weight_last'].fillna(0)
    
    merged['diff'] = (merged['weight_today'] - merged['weight_last']).round(2)
    
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
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>00981A & 00991A 每日持股變動</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f8f9fa; padding: 20px; }}
            .card {{ margin-bottom: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .badge-新進 {{ background-color: #198754; }}
            .badge-加碼 {{ background-color: #d63384; }}
            .badge-減碼 {{ background-color: #0d6efd; }}
            .badge-剔除 {{ background-color: #dc3545; }}
            .badge-持平 {{ background-color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2 class="text-center my-4">ETF 主動持股每日變動儀表板</h2>
            <p class="text-center text-muted">最後更新日期：{TODAY}</p>
            
            <div class="row">
    """
    
    for fund_code, df in results.items():
        changes = df[df['status'] != '持平'].sort_values(by='diff', ascending=False)
        
        html_content += f"""
        <div class="col-md-6">
            <div class="card">
                <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">{fund_code} 當日變動</h5>
                    <span class="badge bg-secondary">異動 {len(changes)} 檔</span>
                </div>
                <div class="card-body">
                    <table class="table table-hover align-middle">
                        <thead>
                            <tr>
                                <th>代號/股票</th>
                                <th>狀態</th>
                                <th>今日權重</th>
                                <th>變動(%)</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        for _, row in changes.iterrows():
            stock = row['stock_name'] if pd.notna(row['stock_name']) else row['stock_code']
            diff_str = f"+{row['diff']}%" if row['diff'] > 0 else f"{row['diff']}%"
            html_content += f"""
                            <tr>
                                <td><strong>{row['stock_code']}</strong> {stock}</td>
                                <td><span class="badge badge-{row['status']}">{row['status']}</span></td>
                                <td>{row['weight_today']}%</td>
                                <td class="{'text-danger' if row['diff']>0 else 'text-primary'}"><strong>{diff_str}</strong></td>
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
            df_diff = compare_holdings(code, df_today)
            results[code] = df_diff
            df_today.to_csv(os.path.join(DATA_DIR, f"{code}_{TODAY}.csv"), index=False, encoding="utf-8-sig")
            
    if results:
        build_webpage(results)

if __name__ == "__main__":
    main()
