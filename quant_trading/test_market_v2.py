import requests

def test():
    # 尝试不同的 Header 组合
    url = "http://hq.sinajs.cn/list=sh600519"
    
    print("--- 尝试 1: 无 Header ---")
    r = requests.get(url)
    print(r.text[:100])
    
    print("\n--- 尝试 2: 浏览器 UA ---")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://finance.sina.com.cn/'
    }
    r = requests.get(url, headers=headers)
    # 强制 GBK 解码看看
    r.encoding = 'gbk'
    print(r.text[:100])

if __name__ == "__main__":
    test()