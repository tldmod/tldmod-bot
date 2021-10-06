import bs4, requests
import datetime, time
import subprocess

new_update = False
base_date = datetime.datetime.utcfromtimestamp(1535662299) # datetime.datetime.now()

def retrieve_page_contents(url):
  try:
    res = requests.get(url)
  except requests.exceptions.RequestException as e:
    print(e)
    return False 
  soup = bs4.BeautifulSoup(res.text, features='html5lib')
  return soup

def get_page_title(soup):
  # swy: careful about error'ing out
  for title_tag in soup.select('head > title'):
    return str(title_tag.string)
  return ""

def check_workshop_update(base_date):
  # swy: retrieve the main page from the changelog, grab another random Workshop page at the same time
  #      to ensure it's not a general going-offline thing for the whole platform.
  #      ignore that, we're looking for our own mod's problems.
  tld_soup = retrieve_page_contents('https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223?l=english')
  swc_soup = retrieve_page_contents('https://steamcommunity.com/sharedfiles/filedetails/changelog/742671195?l=english')

  tld_title_text = get_page_title(tld_soup)
  swc_title_text = get_page_title(swc_soup)

  # swy: seems like Valve doesn't want to respect HTTP error codes, even on errors it throws 200 pages
  #      take advantage of the title: "Steam Community :: Error", and maybe the body:
  #      > Error > Sorry! > An error was encountered while processing your request:
  #                       > That item does not exist. It may have been removed by the author.
  if 'error' in tld_title_text.lower():
    # swy: generalized error? then just bail out
    if 'error' in swc_title_text.lower():
      print("[!] generalized downtime in the Steam Workshop platform, Valve messed up. Ignoring.")
      return False
    else:
      print("[!] the page title is returning '%s', try to fix it on our end." % tld_title_text)
      subprocess.run(["handle-workshop-error"], shell=True)
      return False

  # swy: parse the page, find each potential changelog entry, and grab the latest date;
  #      as long as one of the entries is newer than the last time we checked we're done.
  for anchor in tld_soup.select('div#mainContents p[id]'):
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