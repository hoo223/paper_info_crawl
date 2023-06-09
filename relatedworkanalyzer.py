import os
import pickle
import time, random
import math
import requests
from bs4 import BeautifulSoup
from semanticscholar import SemanticScholar
import json
import tqdm
from difflib import SequenceMatcher


class RelatedWorkAnalyzer:
    def __init__(self) -> None:
        self.paper_list = {'keypaper':[]}
        self.S2_API_KEY = os.environ['S2_API_KEY']
        self.sch = SemanticScholar(api_key=self.S2_API_KEY)
        self.is_updated = False
        self.load_paper_list()

    def build_paper_list_from_txt(self):
        if os.path.exists('./paper_list.txt'): 
            f = open('paper_list.txt', 'r')
            lines = f.readlines()
            for i, line in enumerate(lines):
                items = line.split('_')
                year = items[0]
                title = items[-1].split('\n')[0]
                self.addNewPaper(title, keypaper=True)
            self.is_updated = True
            self.update_pkl()
        else: # txt 파일이 없으면 빈 딕셔너리 반환
            print('No txt file')
            
        # Save data_dict
        self.update_pkl()

    def load_paper_list(self):
        if os.path.exists('./paper_list_from_semantic.pkl'): # pkl 파일이 존재하면 불러옴
            print('load from pkl')
            self.load_pkl()
        else: # pkl 파일이 없으면 
            print('load from txt')
            self.build_paper_list_from_txt()

    def addNewPaper(self, paper, keypaper=False):
        if ' ' in paper: # title
            title, paperId, year = self.searchByTitle(paper)
            if self.isExistInList(paperId):
                return False
        else: # paperId
            paperId = paper
            if self.isExistInList(paperId):
                return False
            title, paperId, year = self.searchByPaperId(paperId) # get the rest of info.

        # add a new paper
        citations, references = self.getCitationInfo(paperId)
        self.paper_list[paperId] = {'title': title, 
                                    'year': year, 
                                    'references': references, 
                                    'citations': citations, 
                                    'citnuminlist': 0, 
                                    'refnuminlist': 0, 
                                    'isKeypaper': keypaper}
        print('Added {} in the list'.format(title))
        if keypaper:
            self.paper_list['keypaper'].append(paperId)
            print('Added to key paper list')

        return True
    
    def load_pkl(self):
        f =  open('paper_list_from_semantic.pkl','rb')
        self.paper_list = pickle.load(f)

    def update_pkl(self):
        if self.is_updated: # 업데이트 사항이 있는 경우에만
            print('update pkl')
            with open('paper_list_from_semantic.pkl','wb') as f:
               pickle.dump(self.paper_list, f)
            self.is_updated = False
        else:
            print('no update') 

    def searchByTitle(self, title, fields=['title','year','paperId']):
        print("Searching by title... {}".format(title))
        results = self.sch.search_paper(title, fields=fields)
        paperId = results[0].paperId
        title = results[0].title
        year = results[0].year
        return title, paperId, year
    
    def searchByPaperId(self, paperId, fields=['title','year','paperId']):
        results = self.sch.get_paper(paperId, fields=fields)
        paperId = results.paperId
        title = results.title
        year = results.year
        return title, paperId, year


    def isExistInList(self, paperId):
        if paperId in self.paper_list.keys():
            print('Already exists in the list!')
            return True
        else:
            return False

    def getCitationInfo(self, paperId):
        headers = {'x-api-key': self.S2_API_KEY}
        r = requests.post(
            'https://api.semanticscholar.org/graph/v1/paper/batch',
            headers=headers,
            params={'fields': 'citations,references,title'},
            json={"ids": [paperId]}
        )
        return r.json()[0]['citations'], r.json()[0]['references']
    
    def updateCitationInfo(self, paperId, reset=False):
        keys = self.paper_list[paperId].keys()
        if 'citations' not in keys or 'references' not in keys or reset: # if there is no citation info or reset is True
            citations, references = self.getCitationInfo(paperId)
            self.paper_list[paperId]['citations'] = citations
            self.paper_list[paperId]['references'] = references
            print(self.paper_list[paperId]['title'] + "'s citations, references are updated)")
            self.is_updated = True
        else:
            print(self.paper_list[paperId]['title'] + "'s citations, references are already updated)")

    def updataAllCitationInfo(self, reset=False):
        for paperId in self.paper_list.keys():
            if str(type(self.paper_list[paperId])) == "<class 'list'>":
                continue
            self.updateCitationInfo(paperId, reset)
    
    def addRefToList(self, paperId):
        for paper in self.paper_list[paperId]['references']:
            title = paper['title']
            paperId = paper['paperId']
            if not self.isExistInList(paper['paperId']):
                self.paper_list[paperId] = {'title': title, 
                                            'year': None, 
                                            #'references': [], 
                                            #'citations': [], 
                                            'citnuminlist': 0, 
                                            'refnuminlist': 0, 
                                            'isKeypaper': False}
                print("Added {} in the list".format(title))
                self.is_updated = True


    def addCitToList(self, paperId):
        for paper in self.paper_list[paperId]['citations']:
            title = paper['title']
            paperId = paper['paperId']
            if not self.isExistInList(paper['paperId']):
                self.paper_list[paperId] = {'title': title, 
                                            'year': None, 
                                            #'references': [], 
                                            #'citations': [], 
                                            'citnuminlist': 0, 
                                            'refnuminlist': 0, 
                                            'isKeypaper': False}
                self.is_updated = True

    def setKeyPaper(self, paperId):
        self.paper_list[paperId]['isKeypaper'] = True
        if paperId not in self.paper_list['keypaper']:
            self.paper_list['keypaper'].append(paperId)
        print(self.paper_list[paperId]['title'] + ' is set as a key paper')
        self.is_updated = True

    def removeKeyPaper(self, paperId):
        self.paper_list[paperId]['isKeypaper'] = False
        if paperId in self.paper_list['keypaper']:
            self.paper_list['keypaper'].remove(paperId)
        print(self.paper_list[paperId]['title'] + ' is removed from key paper')
        self.is_updated = True

    def printKeyPaper(self):
        for paperId in self.paper_list['keypaper']:
            print(self.paper_list[paperId]['title'])
            print(paperId, '\n')

    def similar(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    def findKeyPaperByTitle(self, title):
        for paperId in self.paper_list['keypaper']:
            if self.similar(self.paper_list[paperId]['title'], title) > 0.9:
                return paperId
        return None

    def updateCitNumInList(self, paperId): # citation 목록 중 리스트에 있는 논문이 몇 개인지 체크
        if 'citations' in self.paper_list[paperId].keys():
            self.paper_list[paperId]['citnuminlist'] = 0
            for paper in self.paper_list[paperId]['citations']:
                if paper['paperId'] in self.paper_list.keys():
                    self.paper_list[paperId]['citnuminlist'] += 1
                    self.is_updated = True

    def updateRefNumInList(self, paperId): # reference 목록 중 리스트에 있는 논문이 몇 개인지 체크
        if 'references' in self.paper_list[paperId].keys():
            self.paper_list[paperId]['refnuminlist'] = 0
            for paper in self.paper_list[paperId]['references']:
                if paper['paperId'] in self.paper_list.keys():
                    self.paper_list[paperId]['refnuminlist'] += 1
                    self.is_updated = True

    def updateCitNumInKeyList(self, paperId): # citation 목록 중 리스트에 있는 논문이 몇 개인지 체크
        if 'citations' in self.paper_list[paperId].keys():
            self.paper_list[paperId]['citnuminkeylist'] = 0
            for paper in self.paper_list[paperId]['citations']:
                if paper['paperId'] in self.paper_list['keypaper']:
                    self.paper_list[paperId]['citnuminkeylist'] += 1
                    self.is_updated = True

    def updateRefNumInKeyList(self, paperId): # reference 목록 중 리스트에 있는 논문이 몇 개인지 체크
        if 'references' in self.paper_list[paperId].keys():
            self.paper_list[paperId]['refnuminkeylist'] = 0
            for paper in self.paper_list[paperId]['references']:
                if paper['paperId'] in self.paper_list['keypaper']:
                    self.paper_list[paperId]['refnuminkeylist'] += 1
                    self.is_updated = True
    