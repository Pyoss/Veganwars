from bs4 import BeautifulSoup
from urllib.request import urlopen
import urllib

proxy_html = urlopen('http://spys.one/proxys/DE/').read()

html = str(BeautifulSoup(proxy_html))
html_start = 'Немецкие прокси сервера.</h1>'
html = html[html.index(html_start):]
html = html.split('<font class="spy14">')
for n in html:
    print(n)