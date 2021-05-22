from datetime import datetime, timedelta

import requests

url = 'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt'
r = requests.get(url=url)
res = r.text

proxies_list = []
for lines in res.split('\n'):
    proxy = ''.join(lines)
    proxies_list.append(proxy)

proxies = {'last-updated': '2021-05-22 12:40:28.662019', 'list': ['202.142.178.98:8080']}
print(proxies_list)
if len(proxies) == 0 or \
        (datetime.now() - datetime.strptime(proxies['last-updated'], '%Y-%m-%d %H:%M:%S.%f')) > timedelta(1):
    print('yeet')
else:
    print('wat')