import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time

class Tabelog:
    """
    食べログスクレイピングクラス
    test_mode=Trueで動作させると、最初のページの３店舗のデータのみを取得できる
    """
    def __init__(self, base_url, test_mode=True, p_ward='東京都内', begin_page=1, end_page=1):

        # 変数宣言
        self.store_id = ''
        self.store_id_num = 0
        self.store_name = ''
        self.score = 0
        self.ward = p_ward
        self.review_cnt = 0
        self.review = ''
        self.columns = ['store_id', 'store_name', 'score', 'ward', 'review_cnt', 'review']
        self.df = pd.DataFrame(columns=self.columns)
        self.__regexcomp = re.compile(r'\n|\s') # \nは改行、\sは空白

        page_num = begin_page # 店舗一覧ページ番号

        if test_mode:
            list_url = base_url + str(page_num) +  '/?Srt=D&SrtT=rt&sort_mode=1' #食べログの点数ランキングでソートする際に必要な処理
            self.scrape_list(list_url, mode=test_mode)
        else:
            while True:
                list_url = base_url + str(page_num) +  '/?Srt=D&SrtT=rt&sort_mode=1' #食べログの点数ランキングでソートする際に必要な処理
                if self.scrape_list(list_url, mode=test_mode) != True:
                    break

                # INパラメータまでのページ数データを取得する
                if page_num >= end_page:
                    break
                page_num += 1
        return

    def scrape_list(self, list_url, mode):
        """
        店舗一覧ページのパーシング
        """
        r = requests.get(list_url)
        if r.status_code != requests.codes.ok:
            return False

        soup = BeautifulSoup(r.content, 'html.parser')
        soup_a_list = soup.find_all('a', class_='list-rst__rst-name-target') # 店名一覧

        if len(soup_a_list) == 0:
            return False

        if mode:
            for soup_a in soup_a_list[:2]:
                item_url = soup_a.get('href') # 店の個別ページURLを取得
                self.store_id_num += 1
                self.scrape_item(item_url, mode)
        else:
            for soup_a in soup_a_list:
                item_url = soup_a.get('href') # 店の個別ページURLを取得
                self.store_id_num += 1
                self.scrape_item(item_url, mode)

        return True

    def scrape_item(self, item_url, mode):
        """
        個別店舗情報ページのパーシング
        """
        start = time.time()

        r = requests.get(item_url)
        if r.status_code != requests.codes.ok:
            print(f'error:not found{ item_url }')
            return

        soup = BeautifulSoup(r.content, 'html.parser')

        # 店舗名称取得
        # <h2 class="display-name">
        #     <span>
        #         麺匠　竹虎 新宿店
        #     </span>
        # </h2>
        store_name_tag = soup.find('h2', class_='display-name')
        store_name = store_name_tag.span.string
        print('{}→店名：{}'.format(self.store_id_num, store_name.strip()), end='')
        self.store_name = store_name.strip()

        # # ラーメン屋、つけ麺屋以外の店舗は除外
        # store_head = soup.find('div', class_='rdheader-subinfo') # 店舗情報のヘッダー枠データ取得
        # store_head_list = store_head.find_all('dl')
        # store_head_list = store_head_list[1].find_all('span')
        # #print('ターゲット：', store_head_list[0].text)

        # if store_head_list[0].text not in {'ラーメン', 'つけ麺'}:
        #     print('ラーメンorつけ麺のお店ではないので処理対象外')
        #     self.store_id_num -= 1
        #     return

        # 評価点数取得
        #<b class="c-rating__val rdheader-rating__score-val" rel="v:rating">
        #    <span class="rdheader-rating__score-val-dtl">3.58</span>
        #</b>
        rating_score_tag = soup.find('b', class_='c-rating__val')
        rating_score = rating_score_tag.span.string
        print('  評価点数：{}点'.format(rating_score), end='')
        self.score = rating_score

        # 評価点数が存在しない店舗は除外
        if rating_score == '-':
            print('  評価がないため処理対象外')
            self.store_id_num -= 1
            return
    #    # 評価が3.5未満店舗は除外
    #     if float(rating_score) < 3.5:
    #         print('  食べログ評価が3.5未満のため処理対象外')
    #         self.store_id_num -= 1
    #         return

        # レビュー一覧URL取得
        #<a class="mainnavi" href="https://tabelog.com/tokyo/A1304/A130401/13143442/dtlrvwlst/"><span>口コミ</span><span class="rstdtl-navi__total-count"><em>60</em></span></a>
        review_tag_id = soup.find('li', id="rdnavi-review")
        review_tag = review_tag_id.a.get('href')

        # レビュー件数取得
        print('  レビュー件数：{}'.format(review_tag_id.find('span', class_='rstdtl-navi__total-count').em.string), end='')
        self.review_cnt = review_tag_id.find('span', class_='rstdtl-navi__total-count').em.string

        # レビュー一覧ページ番号
        page_num = 1 #1ページ*20 = 20レビュー 。この数字を変えて取得するレビュー数を調整。

        # レビュー一覧ページから個別レビューページを読み込み、パーシング
        # 店舗の全レビューを取得すると、食べログの評価ごとにデータ件数の濃淡が発生してしまうため、
        # 取得するレビュー数は１ページ分としている（件数としては１ページ*20=２0レビュー）
        while True:
            review_url = review_tag + 'COND-0/smp1/?lc=0&rvw_part=all&PG=' + str(page_num)
            #print('\t口コミ一覧リンク：{}'.format(review_url))
            print(' . ' , end='') #LOG
            if self.scrape_review(review_url) != True:
                break
            if page_num >= 1:
                break
            page_num += 1

        process_time = time.time() - start
        print('  取得時間：{}'.format(process_time))

        return

    def scrape_review(self, review_url):
        """
        レビュー一覧ページのパーシング
        """
        r = requests.get(review_url)
        if r.status_code != requests.codes.ok:
            print(f'error:not found{ review_url }')
            return False

        # 各個人の口コミページ詳細へのリンクを取得する
        #<div class="rvw-item js-rvw-item-clickable-area" data-detail-url="/tokyo/A1304/A130401/13141542/dtlrvwlst/B408082636/?use_type=0&amp;smp=1">
        #</div>
        soup = BeautifulSoup(r.content, 'html.parser')
        review_url_list = soup.find_all('div', class_='rvw-item') # 口コミ詳細ページURL一覧

        if len(review_url_list) == 0:
            return False

        for url in review_url_list:
            review_detail_url = 'https://tabelog.com' + url.get('data-detail-url')
            #print('\t口コミURL：', review_detail_url)

            # 口コミのテキストを取得
            self.get_review_text(review_detail_url)

        return True

    def get_review_text(self, review_detail_url):
        """
        口コミ詳細ページをパーシング
        """
        r = requests.get(review_detail_url)
        if r.status_code != requests.codes.ok:
            print(f'error:not found{ review_detail_url }')
            return

        # ２回以上来訪してコメントしているユーザは最新の1件のみを採用
        #<div class="rvw-item__rvw-comment" property="v:description">
        #  <p>
        #    <br>すごい煮干しラーメン凪 新宿ゴールデン街本館<br>スーパーゴールデン1600円（20食限定）を喰らう<br>大盛り無料です<br>スーパーゴールデンは、新宿ゴールデン街にちなんで、ココ本店だけの特別メニューだそうです<br>相方と歌舞伎町のtohoシネマズの映画館でドラゴンボール超ブロリー を観てきた<br>ブロリー 強すぎるね(^^)面白かったです<br>凪の煮干しラーメンも激ウマ<br>いったん麺ちゅるちゅる感に、レアチャーと大トロチャーシューのトロけ具合もうめえ<br>煮干しスープもさすが！と言うほど完成度が高い<br>さすが食べログラーメン百名店<br>と言うか<br>2日連チャンで、近場の食べログラーメン百名店のうちの2店舗、昨日の中華そば葉山さんと今日の凪<br>静岡では考えられん笑笑<br>ごちそうさまでした
        #  </p>
        #</div>
        soup = BeautifulSoup(r.content, 'html.parser')
        review = soup.find_all('div', class_='rvw-item__rvw-comment')#reviewが含まれているタグの中身をすべて取得
        if len(review) == 0:
            review = ''
        else:
            review = review[0].p.text.strip() # strip()は改行コードを除外する関数

        #print('\t\t口コミテキスト：', review)
        self.review = review

        # データフレームの生成
        self.make_df()
        return


    def make_df(self):
        self.store_id = str(self.store_id_num).zfill(8) #0パディング
        se = pd.Series([self.store_id, self.store_name, self.score, self.ward, self.review_cnt, self.review], self.columns) # 行を作成
        self.df = self.df.append(se, self.columns) # データフレームに行を追加
        return
