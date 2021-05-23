import os
import platform

from selenium import webdriver

if platform.system() == 'Windows':
    print(f"x")
    driver = os.getcwd() + r'\driver\chromedriver_win'
elif platform.system() == 'Linux':
    print(f"y")
    driver = os.getcwd() + r'\driver\chromedriver'

print (driver)

options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument("--test-type")
options.add_argument("--headless")
options.add_argument("--test-type")
options.add_argument("--no-sandbox")
options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36")

driver = webdriver.Chrome(executable_path=r"D:/Documents/GitHub/OWID_Cogs/tiktok/driver/chromedriver_win", options=options)
url = 'https://www.tiktok.com/'
driver.get(url)