#ライブラリをimport
import streamlit as st
from bs4 import BeautifulSoup
import re #不要文字削除
import requests
from time import sleep
import pandas as pd
import gspread 
from oauth2client.service_account import ServiceAccountCredentials
import json


#Streamlitでフロント画面を作成---

#メイン画面を作成

st.title("Suumo 重複物件除外サイト") #title
st.caption("Suumo上の重複物件を削除した形で物件検索できます")
st.caption("初期設定:賃料25万円以下、間取:2K/2DK/2LDK、最寄駅からの距離:徒歩5分")

#サイドバーを作成

st.sidebar.header('操作方法')

st.sidebar.header('1.「最新情報に更新」クリック')
scraping_btn = st.sidebar.button('最新情報に更新')
if scraping_btn:
    # 最後のページの数値を取得
    #引用先のURL（東京駅まで電車で10分以内、最寄駅から徒歩5分以内、家賃25万以内、2K/2DK/2LDKで検索）
    url = "https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ar=030&ta=13&bs=040&ekInput=25620&tj=10&nk=-1&ct=25.0&cb=0.0&md=05&md=06&md=07&et=5&mt=9999999&mb=0&cn=9999999&shkr1=03&shkr2=03&shkr3=03&shkr4=03&fw2=&pc=30"
    res = requests.get(url)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser') #取得したHTMLをBeautifulSoupで解析
    page_elements = soup.select("ol.pagination-parts a")
    page_numbers = [int(element.text) for element in page_elements]
    last_page = max(page_numbers)
    print(last_page)
    
    #空のリストを作成
    data_list = []
    
    # 正常にHTML情報が取得できるか確認してからデータ取得開始
    if res.status_code == 200:

        #全ページのデータ取得
        for page in range(1, last_page +1): 
            target_url = url.format(page)
            res = requests.get(target_url) #requestを使ってURLにアクセス
            sleep(1) #相手サイトの負荷軽減
            res.encoding = 'utf-8' #文字化け防止
            soup = BeautifulSoup(res.text, 'html.parser') #取得したHTMLをBeautifulSoupで解析
            contents = soup.find_all('div', class_= 'cassetteitem') #全ての物件情報取得

            #物件・部屋情報の取得
            for content in contents:
                detail = content.find('div', class_='cassetteitem-detail') #物件情報
                table = content.find('table', class_='cassetteitem_other') #部屋情報

                #物件情報から必要情報を取得
                name = detail.find('div', class_='cassetteitem_content-title').text
                address = detail.find('li', class_='cassetteitem_detail-col1').text

                #部屋情報を取得
                tr_tags = table.find_all('tr', class_='js-cassette_link')
                for tr_tag in tr_tags:
                    #部屋情報から必要情報を取得
                    floor, price, first_fee, capacity = tr_tag.find_all('td')[2:6]
                    #さらに細かい情報取得
                    rent, administration = price.find_all('li')
                    deposit, gratuity = first_fee.find_all('li')
                    madori, menseki = capacity.find_all('li')
                    #取得した全ての情報を辞書に格納
                    data = {
                        'name' : name,
                        'address' : address,
                        'floor': floor.text,
                        'rent' : rent.text,
                        'administration' : administration.text,
                        'deposit' : deposit.text,
                        'gratuity' : gratuity.text,
                        'madori' : madori.text,
                        'menseki' : menseki.text
                    }
                    #取得した辞書を格納
                    data_list.append(data)
                    
    #データフレームを作成
    df = pd.DataFrame(data_list)
    
    #DB全体の不要な文字を取り除く
    def remove_unwanted_chars(text):
        if isinstance(text, str):
            return re.sub('[\n\r\t]', '', text)
        return text
    # データフレームのすべての要素に関数を適用
    df = df.applymap(remove_unwanted_chars)
    
    df['floor'] = df['floor'].str.replace('階', '') #floorのデータの表現を統一
    
    #お金（rent, administration	, deposit, gratuity）を整数型に変換
    def yen_to_int(text):
        try:
            text = str(text)

            if '-' in text:
                amount = 0
            elif '万円' in text:
                amount = float(text.replace('万円', '')) * 10000
            else:
                amount = float(text.replace('円', ''))
        except ValueError:
            amount = 0 # 形式に一致しない場合は0を返す
        return int(amount)

    df['rent'] = df['rent'].apply(yen_to_int)
    df['administration'] = df['administration'].apply(yen_to_int)
    df['deposit'] = df['deposit'].apply(yen_to_int)
    df['gratuity'] = df['gratuity'].apply(yen_to_int)
    
    #mensekiのデータ（比例尺度）に変換
    df['menseki'] = df['menseki'].str.replace('m2','').astype(float)
    
    # 特定の列に基づいて重複を確認
    duplicate_rows = df[df.duplicated(subset=['address',  'floor', 'rent', 'menseki'])]

    # 重複件数の表示
    print(f"重複件数: {duplicate_rows.shape[0]}")

    # 重複データの表示
    print(duplicate_rows)
    
    # 重複データの削除
    df.drop_duplicates(subset=['address', 'floor', 'rent', 'menseki'], inplace=True)
    
    #スプレッドシートに転記
    SP_CREDENTIAL_FILE = "tech0-step3-suumo-data-5ad4dc84f3fe.json"
    SP_COPE = [
        "https://www.googleapis.com/auth/drive",
        "https://spreadsheets.google.com/feeds"
    ]
    SP_SHEET_ID = "1zWKnfAq6sBT4kjeWJ42W-5yBGeevcisgS6yPUph1qw8"
    SP_SHEET="suumo_lowdata"

    credentials = ServiceAccountCredentials.from_json_keyfile_name(SP_CREDENTIAL_FILE, SP_COPE)
    gc = gspread.authorize(credentials)

    sh = gc.open_by_key(SP_SHEET_ID)
    worksheet = sh.worksheet(SP_SHEET)

    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    

st.sidebar.header('2. 検索条件を選択し、「物件を表示」クリック')

#sidebarで検索条件を選び、mainに物件を表示させる

#スライドバー
#st.area = st.sidebar.multiselect('エリア', ('千代田区', '墨田区', '文京区', '中央区', '北区'))
st.rent = st.sidebar.slider('賃料', 0, 250000, 150000)
st.madori = st.sidebar.multiselect('間取り', ('2K', '2DK', '2LDK'))
st.menseki = st.sidebar.slider('専有面積', 0, 80, 40)   
  
#ボタン
submit_btn = st.sidebar.button('物件を表示')

if submit_btn:
    #スプレッドシートを読み込む
    SP_CREDENTIAL_FILE = "tech0-step3-suumo-data-5ad4dc84f3fe.json"
    SP_COPE = [
        "https://www.googleapis.com/auth/drive",
        "https://spreadsheets.google.com/feeds"
    ]
    SP_SHEET_ID = "1zWKnfAq6sBT4kjeWJ42W-5yBGeevcisgS6yPUph1qw8"
    SP_SHEET="suumo_lowdata"
    credentials = ServiceAccountCredentials.from_json_keyfile_name(SP_CREDENTIAL_FILE, SP_COPE)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SP_SHEET_ID)
    worksheet = sh.worksheet(SP_SHEET)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df['menseki'] = df['menseki'].astype(int)

    #検索条件に該当するものだけいれる
    condition1 = df['rent'] <= int(st.rent)
    condition2 = df['madori'].isin(st.madori)
    condition3 = df['menseki'] <= int(st.menseki)
    filtered_df = df[condition1 & condition2 & condition3]
    
    #データを表示
    st.dataframe(filtered_df)

 
