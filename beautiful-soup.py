import bs4, requests
import time

res = requests.get('https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223')
soup = bs4.BeautifulSoup(res.text)
for anchor in soup.select('div#mainContents p[id]'):
    id = anchor.get('id')
    print (id, time.ctime(int(id)))