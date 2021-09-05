import bs4, requests
import datetime, time
import subprocess

new_update = False
base_date = datetime.datetime.utcfromtimestamp(1535662299) # datetime.datetime.now()

def check_workshop_update(base_date):
  try:
    res = requests.get('https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223?l=english')
  except requests.exceptions.RequestException as e:
    print(e)
    return False 
  soup = bs4.BeautifulSoup(res.text, features='html5lib')

  # swy: careful about error'ing out
  for title_tag in soup.select('head > title'):
    title_text = str(title_tag.string)

    # swy: seems like Valve doesn't want to respect HTTP error codes, even on errors it throws 200 pages
    #      take advantage of the title: "Steam Community :: Error", and maybe the body:
    #      > Error > Sorry! > An error was encountered while processing your request:
    #                       > That item does not exist. It may have been removed by the author.
    if 'error' in title_text.lower():
      print("[!] the page title is returning '%s', try to fix it on our end." % title_text)
      subprocess.run(["handle-workshop-error"], shell=True)
      return False

  # swy: parse the page, find each potential changelog entry, and grab the latest date;
  #      as long as one of the entries is newer than the last time we checked we're done.
  for anchor in soup.select('div#mainContents p[id]'):
    try:
      id_str  = anchor.get('id')
      id      = int(id_str)
      id_date = datetime.datetime.utcfromtimestamp(id)
    except ValueError:
      print("[!] '%s' is not an integer, maybe Valve changed something." % id_str)
      continue

#    print (id_str, time.ctime(id), id_date > base_date)

    # swy: if the reported date is newer than the launch 
    if (id_date > base_date):
      print('[!] found new %s workshop update.' % time.ctime(id))
      base_date = id_date
      return {'date': id_date, 'str': id_str, 'int': id}


# check_workshop_update(base_date)