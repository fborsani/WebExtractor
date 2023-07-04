import json
import re
from time import sleep
import requests
import argparse
from enum import Enum
from bs4 import BeautifulSoup, Comment, Tag
from urllib.parse import urlparse

class Settings():
    outputVerbose = 0
    depthLimit = -1
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
        parser.add_argument("-i","--ignore-cert",action="store_true", default=False, help="Don't validate certificates when executing HTTPS requests")
        parser.add_argument("-f","--follow-redirect",action="store_true", default=False, help="Follow redirects when receiving 30X responses")
        parser.add_argument("-d","--max-depth", type=int, default=-1, help="When specified indicates the max number to pages to crawl from the starting point. Special values are 0 to parse only the specified url and -1 for no limits")
        parser.add_argument("-o","--output", help="Path to output file")
        parser.add_argument("-oj","--output-json", help="Path to JSON output file")
        parser.add_argument("-t","--timeout",type=int, default=5000, help="Request timeout")
        parser.add_argument("-w","--wait",type=int, default=100, help="Time to wait between requests")
        parser.add_argument("-H","--header", type=str, action="append", nargs="+", help="Specify one or more HTTP headers in the format <name>:<value>")
        parser.add_argument("-C","--cookie", type=str, action="append", nargs="+", help="Specify one or more cookies in the format <name>=<value>")
        parser.add_argument("-v",action="store_true", help="Print additional information")
        parser.add_argument("-vv",action="store_true", help="Print debug information about requests performed")
        args = vars(parser.parse_args())

        if args["vv"]:
            self.outputVerbose = self.VerboseLevels.HIGH
        elif args["v"]:
            self.outputVerbose = self.VerboseLevels.LOW
        else:
            self.outputVerbose = self.VerboseLevels.NONE

        if args["max_depth"] is not None:
            self.depthLimit = args["max_depth"]

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
            for element in results:
                outStr = ""

                if element:
                    if isinstance(results[0], Tag):
                        outStr = element.prettify()
                    elif isinstance(results[0], list):
                        outStr = ",".join("\'"+str(i)+"\'" for i in element)
                    else:
                        if isinstance(element, list):
                            outStr = ",".join("\'"+str(i)+"\'" for i in element)
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

class Crawler():
    maxDepth = -1
    startUrl = ""
    domain = ""

    urlsScanned = []
    urlExclusions = re.compile("^(\.|http|https|#|//).*")

    parserOut = None
    parserlinks = None

    def __init__(self, settings:Settings, parser = None):
        self.startUrl = settings.connectionParams["url"]
        self.domain = settings.connectionParams["domain"]
        self.maxDepth = settings.depthLimit
        self.parserOut = parser
        self.parserLinks = Parser(settings, ["a"])

    def crawl(self):
        self.parserOut.parse(self.startUrl)
        self._getPages(self.startUrl,0)

    def _getPages(self, url:str, currentDepth: int):
        if self.maxDepth >= 0 and currentDepth >= self.maxDepth:
            return
        
        for link in self.parserLinks.parse(url):
            currUrl = link.get("href")
            print(url+" - "+str(currentDepth)+"/"+str(self.maxDepth))
            if currUrl and not self.urlExclusions.match(currUrl) and currUrl not in self.urlsScanned:
                if currUrl.startswith("/"):
                    fpath = self.domain+currUrl
                else:
                    fpath = self.domain+"/"+currUrl
                self.parserOut.parse(fpath)
                self.urlsScanned.append(currUrl)
                self._getPages(fpath, currentDepth+1)
                
class Parser():
    s = None
    om = None
    match = []

    def __init__(self, s:Settings, match:list=None, om:OutputManager=None):
        self.match = match
        self.s = s
        self.om = om

        if match:
            self.match = match
        else:
            self.match = s.filters

    def parse(self,url:str):
        elements = []
        r = requests.get(
                    url,
                    verify=self.s.connectionParams["verifyCert"],
                    headers=self.s.connectionParams["headers"],
                    cookies=self.s.connectionParams["cookies"],
                    timeout=self.s.connectionParams["timeout"],
                    allow_redirects=self.s.connectionParams["followRedirect"]
                    )
        if(r.status_code == 200):
                elements += self.findElements(self.match,r)
                if self.om:
                    self.om.printMatches(elements, url)
        elif self.s.outputVerbose == Settings.VerboseLevels.HIGH:
            if self.om:
                self.om.print("The request for url {} returned code {}".format(url,r.status_code))
        return elements
  
    def findElements(self, elementsList:list, r):
        found = []
        if elementsList and r:        
            soup = BeautifulSoup(r.text,"html.parser")
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


if __name__== "__main__":
    s = Settings()
    c = Crawler(s, Parser(s, om=OutputManager(s)))
    #c = Crawler(s, Parser(s, om=None))
    c.crawl()