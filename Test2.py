import requests

url = 'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt'
r = requests.get(url=url)
res = r.text

proxies_list = []
for lines in res.split('\n'):
    proxy = ''.join(lines)
    proxies_list.append(proxy)

print(proxies_list)