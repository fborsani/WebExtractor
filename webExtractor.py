import json
import re
from time import sleep
import requests
import argparse
from enum import Enum
from bs4 import BeautifulSoup, Comment, Tag
from urllib.parse import urlparse

urlsToScan = []
urlsScanned = []
urlExclusions = re.compile("^(\.|http|https|#|//).*")

class Settings():
    outputVerbose = 0
    outputFile = None
    outputFileJson = None
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
        parser.add_argument("-o","--output")
        parser.add_argument("-oj","--output-json")
        parser.add_argument("-t","--timeout",type=int, default=5000)
        parser.add_argument("-w","--wait",type=int, default=100)
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

        self.outputFile = args["output"]
        self.outputFileJson = args["output_json"]

        self.filters = args["filter"].split(",")
        
        urlParamList = self._parseUrl(args["url"])
        self.connectionParams["url"] = urlParamList[0]
        self.connectionParams["domain"] = urlParamList[1]
        self.connectionParams["timeout"] = args["timeout"]
        self.connectionParams["wait"] = args["wait"] / 1000
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

class OutputManager():
    verboseLevel = Settings.VerboseLevels.NONE
    file = None
    fileJson = None
    jsonData = {}

    def __init__(self, settings):
        outFilePath = settings.outputFile
        outFileJsonPath = settings.outputFileJson
        
        if outFilePath:
            self.file = open(outFilePath,"w")
        if outFileJsonPath:
            self.fileJson = open(outFileJsonPath,"w")

        self.verboseLevel = settings.outputVerbose

    def printMatches(self, results, currentUrl):
        if results:
            resultIsTag = isinstance(results[0],Tag)
            for element in results:
                outStr = ""

                if element:
                    if resultIsTag:
                        outStr = element.prettify()
                    else:
                        outStr = element

                    if self.verboseLevel is Settings.VerboseLevels.LOW or self.verboseLevel is Settings.VerboseLevels.HIGH:
                        outStr = currentUrl + ": " + outStr


                self.print(outStr.strip())

                if self.fileJson:
                    self.jsonData[currentUrl] = results


    def print(self, strIn):
        print(strIn)

        if self.file:
            self.file.write(strIn+"\n")

    def writeJsonFile(self):
        if self.fileJson:
            json.dump(self.jsonData,self.fileJson)


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
        if path and not urlExclusions.match(path):
                if path.startswith("/"):
                    path = domain+path
                else:
                    path = domain+"/"+path
                urlsToScan.append(path)
    urlsToScan.pop(0)
    urlsScanned.append(currentUrl)



if __name__== "__main__":
    s = Settings()
    om = OutputManager(s)

    domain = s.connectionParams["domain"]
    urlsToScan.append(s.connectionParams["url"])
    file = None

    for url in urlsToScan:
        if url not in urlsScanned:
            r = requests.get(
                             url,
                             verify=s.connectionParams["verifyCert"],
                             headers=s.connectionParams["headers"],
                             cookies=s.connectionParams["cookies"],
                             timeout=s.connectionParams["timeout"],
                             allow_redirects=s.connectionParams["followRedirect"]
                             )
            sleep(s.connectionParams["wait"])
            if(r.status_code == 200):
                soup = BeautifulSoup(r.text,"html.parser")
                om.printMatches(findElements(s.filters,soup),url)
                getNextPages(soup,domain,url)
            elif s.outputVerbose == Settings.VerboseLevels.HIGH:
                om.print("The request for url {} returned code {}".format(url,r.status_code))
    om.writeJsonFile()