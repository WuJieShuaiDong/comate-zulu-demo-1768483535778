import requests
import akshare as ak

def test_sina(code_list):
    print(f"\n=== 测试新浪接口: {code_list} ===")
    
    # 构造多种前缀组合
    sina_codes = []
    for code in code_list:
        if code.startswith('6'):
            sina_codes.append(f"sh{code}")
        elif code.startswith('8') or code.startswith('4'):
            sina_codes.append(f"bj{code}")
        else:
            sina_codes.append(f"sz{code}")
            
    url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
    print(f"请求URL: {url}")
    
    try:
        headers = {'Referer': 'http://finance.sina.com.cn'}
        resp = requests.get(url, headers=headers, timeout=5)
        print(f"状态码: {resp.status_code}")
        print("返回内容 (前200字符):")
        print(resp.text[:200])
        
        # 尝试解析
        for line in resp.text.splitlines():
            if '="' in line:
                print(f"解析成功: {line}")
            else:
                print(f"解析失败/无数据: {line}")
    except Exception as e:
        print(f"请求报错: {e}")

if __name__ == "__main__":
    # 测试几个典型代码: 主板, 科创, 创业
    codes = ["600519", "688115", "300750"]
    test_sina(codes)