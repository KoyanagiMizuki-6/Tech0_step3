#Streamlitでフロント画面を作成---

import streamlit as st

st.title("Suumo 重複物件除外サイト") #title
st.caption("Suumo上の重複物件を削除した形で物件検索できます")
st.caption("初期設定:賃料25万円以下、間取:2K/2DK/2LDK、最寄駅からの距離:徒歩5分")

st.sidebar.header('検索条件を選び「物件を表示」クリック')

#sidebarで検索条件を選び、mainに物件を表示させる
with st.form(key="condition_form"):
    #スライドバー
    rent = st.sidebar.slider('賃料', 0, 250000, 150000)
    madori = st.sidebar.multiselect('間取り', ('2K', '2DK', '2LDK'))
    menseki = st.sidebar.slider('専有面積', 0, 80, 40)   
    
    #ボタン
    submit_btn = st.sidebar.button('物件を表示')


st.subheader('自己紹介')
st.text('てきすと')
