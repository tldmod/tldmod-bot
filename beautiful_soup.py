import bs4, requests
import datetime, time

new_update = False
base_date = datetime.datetime.fromtimestamp(1535662299) # datetime.datetime.now()

def check_workshop_update(base_date):
  res = requests.get('https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223')
  soup = bs4.BeautifulSoup(res.text, features='html5lib')
  for anchor in soup.select('div#mainContents p[id]'):
    try:
      id_str  = anchor.get('id')
      id      = int(id_str)
      id_date = datetime.datetime.fromtimestamp(id)
    except ValueError:
      print("[!] '%s' is not an integer, maybe Valve changed something." % id_str)
      continue
      
#    print (id_str, time.ctime(id), id_date > base_date)
    
    # swy: if the reported date is newer than the launch 
    if (id_date > base_date):
      print("[!] found new %s workshop update." % time.ctime(id))
      base_date = id_date
      return id_date
