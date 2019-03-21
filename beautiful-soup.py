import bs4, requests
import datetime, time

new_update = False
now = datetime.datetime.fromtimestamp(1535662299) # datetime.datetime.now()

res = requests.get('https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223')
soup = bs4.BeautifulSoup(res.text)
for anchor in soup.select('div#mainContents p[id]'):
    try:
      cur_id_str = anchor.get('id')
      cur_id     = int(cur_id_str)
      cur_date   = datetime.datetime.fromtimestamp(cur_id)
    except ValueError:
      print ("[!] '%s' is not an integer, maybe Valve changed something." % cur_id_str)
      continue
      
    print (cur_id, time.ctime(cur_id), cur_date > now)
    
#    if (cur_date > now):
#      new_update = True
#      break
