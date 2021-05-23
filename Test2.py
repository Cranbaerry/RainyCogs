from TikTokApi import TikTokApi

t = TikTokApi()
t.proxy = "192.168.1.1"
t.proxy = None
t.getBytes(url='https://www.tiktok.com/', proxy='wat')
