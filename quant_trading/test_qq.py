import requests

def test_qq():
    # 腾讯接口: http://qt.gtimg.cn/q=sh600519
    url = "http://qt.gtimg.cn/q=sh600519,sh688115,sz300750"
    print(f"Testing: {url}")
    
    try:
        r = requests.get(url, timeout=5)
        print(f"Status: {r.status_code}")
        print("Response:")
        print(r.text)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_qq()