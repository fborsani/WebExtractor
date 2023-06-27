import json
import re
import requests
import argparse
from enum import Enum
from bs4 import BeautifulSoup, Comment, Tag
from urllib.parse import urlparse

urlsToScan = []
urlsScanned = []
urlExclusions = re.compile("^(http|https|#|//).*")

class Settings():
    outputVerbose = 0
    connectionParams = {}
    filters = []

    class VerboseLevels(Enum):
        NONE = 0
        LOW = 1
        HIGH = 2

    def __init__(self):
        parser = argparse.ArgumentParser(description='Crawl and extract text from a website')
        parser.add_argument("url")
        parser.add_argument("filter")
        parser.add_argument("-i","--ignore-cert",action="store_true", default=False)
        parser.add_argument("-f","--follow-redirect",action="store_true", default=False)
        parser.add_argument("-o")
        parser.add_argument("-oj")
        parser.add_argument("-t","--timeout",type=int, default=5000)
        parser.add_argument("-H","--header", type=str, action="append", nargs="+")
        parser.add_argument("-C","--cookie", type=str, action="append", nargs="+")
        parser.add_argument("-v",action="store_true")
        parser.add_argument("-vv",action="store_true")
        args = vars(parser.parse_args())

        if args["vv"]:
            self.outputVerbose = self.VerboseLevels.HIGH
        elif args["v"]:
            self.outputVerbose = self.VerboseLevels.LOW
        else:
            self.outputVerbose = self.VerboseLevels.NONE

        self.filters = args["filter"].split(",")
        
        urlParamList = self._parseUrl(args["url"])
        self.connectionParams["url"] = urlParamList[0]
        self.connectionParams["domain"] = urlParamList[1]
        self.connectionParams["timeout"] = args["timeout"]
        self.connectionParams["verifyCert"] = not args["ignore_cert"]
        self.connectionParams["followRedirect"] = args["follow_redirect"]
        self.connectionParams["headers"] = self._parseMultiValueParam(args["header"],":")
        self.connectionParams["cookies"] = self._parseMultiValueParam(args["cookie"],"=")

    def _parseMultiValueParam(self, headerList, separator):
        dict = {}
        if headerList:
            for subList in headerList:
                for entry in subList:
                    splitIdx = entry.find(separator)
                    if splitIdx > -1:
                        key = entry[:splitIdx].strip()
                        value = entry[splitIdx+1:].strip()
                        dict[key] = value
            return dict
        return None
    
    def _parseUrl(self, arg):
        url = arg
        domain = urlparse(url).scheme+"://"+urlparse(url).netloc
        return [url, domain]

    def getVerboseLevel(self):
        return self.verboseLevel
    
    def isHighVerbose(self):
        return self.verboseLevel == 2
    
    def isVerbose(self):
        return self.verboseLevel == 1



def printResults(resultList, url):
    if resultList:
        resultIsTag = isinstance(resultList[0],Tag)
        for element in resultList:
            elem = element
            
            if resultIsTag:
                elem = element.text

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
    s = Settings()

    verifyCert = True
    printResultUrl= True
    destFile = None

    domain = s.connectionParams["domain"]
    urlsToScan.append(s.connectionParams["url"])
    file = None

    if destFile:
        file = open(destFile,"w")

    for url in urlsToScan:
        if url not in urlsScanned:
            print(url)
            r = requests.get(
                             url,
                             verify=s.connectionParams["verifyCert"],
                             headers=s.connectionParams["headers"],
                             cookies=s.connectionParams["cookies"],
                             timeout=s.connectionParams["timeout"],
                             allow_redirects=s.connectionParams["followRedirect"]
                             )
            if(r.status_code == 200):
                soup = BeautifulSoup(r.text,"html.parser")
                printResults(findElements(s.filters,soup),url)
                getNextPages(soup,domain,url)
            else:
                print(r.status_code)