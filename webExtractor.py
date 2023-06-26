import json
import re
import requests
from bs4 import BeautifulSoup, Comment, Tag
from urllib.parse import urlparse

urlsToScan = []
urlsScanned = []
urlExclusions = re.compile("^(http|https|#|//).*")


def printResults(resultList, url, printUrl=True, destFile=None):
    resultIsTag = isinstance(resultList[0],Tag)
    for element in resultList:
        elem = element
        
        if resultIsTag:
            elem = element.text

        if printUrl:
            elem = url+": "+elem

        print(elem)

        if destFile:
            destFile.write(elem)

def printJSONFile(resultList, url, destFile):
    jsonDict = {
        "url": url,
        "results": resultList
    }

    destFile.write(json.dumps(jsonDict))


def findElements(elementsList,soup):
    if elementsList:
        found = []

        for target in elementsList:
            if target == 'comment':
                found += soup.find_all(string = lambda text: isinstance(text,Comment))
            if target.find(".") != -1:
                args = target.split(".")
                tmpList = soup.find_all(args[0])
                for item in tmpList:
                    found.append(item.get(args[1]))
            else:
                found += soup.find_all(target)
        return found


def getNextPages(soup,domain,currentUrl):
    for link in soup.find_all("a"):
        path = link.get("href")
        if path:
            if not urlExclusions.match(path):
                if path.startswith("/"):
                    path = domain+path
                urlsToScan.append(path)
    urlsToScan.pop(0)
    urlsScanned.append(currentUrl)



if __name__== "__main__":
    verifyCert = True
    printResultUrl= True
    timeoutVal = 5000
    headerVal = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"}
    startUrl = "http://it.wikipedia.org/wiki/Pagina_principale"
    targetStr = "comment"
    destFile = None
    targetList = targetStr.split(",")

    domain = urlparse(startUrl).scheme+"://"+urlparse(startUrl).netloc
    urlsToScan.append(startUrl)
    file = None

    if destFile:
        file = open(destFile,"w")
    
    for url in urlsToScan:
        if url not in urlsScanned:
            r = requests.get(url,verify=verifyCert,headers=headerVal,timeout=timeoutVal)
            if(r.status_code == 200):
                soup = BeautifulSoup(r.text,"html.parser")
                printResults(findElements(targetList,soup),url,printResultUrl,file)
                getNextPages(soup,domain,url)


            

