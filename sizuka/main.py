#!/usr/bin/env python

from TabelogScraping import Tabelog

BASE_URL = "https://tabelog.com/tokyo/A1329/A132904/rstLst/RC/"

def main():
    tokyo_review = Tabelog(BASE_URL,test_mode=False, p_ward='東京都内')
    
    #CSV保存
    tokyo_review.df.to_csv("./out.csv")

if __name__ == "__main__":
    main()