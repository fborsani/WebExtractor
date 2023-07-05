# WebExtractor
A tool written in python 3 designed to crawl a website and extract tags, text, comments and properties from the HTML code.
Uses the requests library to retireve the pages and Beatifulsoup to parse the page source code and extract the requested elements. The results can be stored as plaintext or in JSON format

## Usage

```
usage: webExtractor.py [-h] [-i] [-f] [-d MAX_DEPTH] [-o OUTPUT] [-oj OUTPUT_JSON] [-t TIMEOUT] [-w WAIT] [-H HEADER [HEADER ...]] [-C COOKIE [COOKIE ...]] [-v] [-vv]
                       url filter

Crawl and extract text from a website

positional arguments:
  url
  filter

options:
  -h, --help                                 Show this help message and exit
  -i, --ignore-cert                          Don't validate certificates when executing HTTPS requests
  -f, --follow-redirect                      Follow redirects when receiving 30X responses
  -d MAX_DEPTH, --max-depth MAX_DEPTH        When specified indicates the max number to pages to crawl from the starting point.
                                             Special values are 0 to parse only the specified url and -1 for no limits (same as not specifying the flag)
  -o OUTPUT, --output OUTPUT                 Path to output file
  -oj OUTPUT_JSON, --output-json OUTPUT_JSON Path to JSON output file
  -t TIMEOUT, --timeout TIMEOUT              Request timeout
  -w WAIT, --wait WAIT                       Time to wait between requests
  -H HEADER [HEADER ...], --header HEADER    Specify one or more HTTP headers in the format <name>:<value>
  -C COOKIE [COOKIE ...], --cookie COOKIE    Specify one or more cookies in the format <name>=<value>
  -v                                         Print additional information
  -vv                                        Print debug information about requests performed

```

## Examples

Extract all comments from website
```
python webExtractor.py <site> comment
```
Extract all links
```
python webExtractor.py <site> a.href
```
Extract all image URIs
```
python webExtractor.py <site> img.src
```
Extract all IDs and classes of divs
```
python webExtractor.py <site> divs.id,divs.class
```
