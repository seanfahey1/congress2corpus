# congress2corpus

## Description

This app extracts corpus data from .pdf files of US Senate hearings and debates distributed by `govinfo.gov` and 
`congress.gov`. This was written as part of my LING571 final project @ SDSU.

Sample documents I used for testing:
* [January 10, 1991](https://www.govinfo.gov/content/pkg/GPO-CRECB-1991-pt1/pdf/GPO-CRECB-1991-pt1-6-1.pdf)
* [January 11, 1991](https://www.govinfo.gov/content/pkg/GPO-CRECB-1991-pt1/pdf/GPO-CRECB-1991-pt1-7-2.pdf)
* [January 12, 1991](https://www.congress.gov/102/crecb/1991/01/12/GPO-CRECB-1991-pt1-8-1.pdf)


## Install

```
git pull https://github.com/seanfahey1/congress2corpus.git
cd congress2corpus && pip install .
```
Note: This application was written for python 3.10+ but will probably work with earlier versions. Python and pip must 
be installed and on your $PATH.  


## Use

From any command line/terminal application, run the following:

```
congress2corpus -p [path_to_pdf_file_1.pdf] [path_to_pdf_file_2.pdf] [...] [path_to_pdf_file_n.pdf] --start [YYYY-MM-DD] --end [YYYY-MM-DD] -o
[desired output directory]
```

#### Special thanks to the maintainers of [this great list](https://github.com/unitedstates/congress-legislators) of US congressional legislatures that helped with political party assignments.
