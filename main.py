import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# 페이지 기본 설정 (타이틀 및 레이아웃)
st.set_page_config(page_title="어제 박스오피스", layout="wide")

st.title("🎬 어제자 박스오피스 순위")

# 1. 한국 시간(KST) 기준 어제 날짜 계산
utc_now = datetime.datetime.now(pytz.utc)
kst_timezone = pytz.timezone("Asia/Seoul")
kst_now = utc_now.astimezone(kst_timezone)
yesterday = kst_now - datetime.timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")
formatted_date = yesterday.strftime("%Y년 %m월 %d일")

st.caption(f"기준 일자: {formatted_date}")


# 2. KOBIS API 데이터 호출 함수 (캐시 적용: 1시간 = 3600초)
@st.cache_data(ttl=3600)
def fetch_box_office(api_key: str, date_str: str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": date_str}

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None


# 3. Streamlit Secrets에서 API 키 불러오기
if "KOBIS_KEY" not in st.secrets:
    st.error(
        "Secrets 설정이 필요합니다. `.streamlit/secrets.toml` 파일 또는 Streamlit Cloud 설정에서 "
        "`KOBIS_KEY`를 추가해 주세요."
    )
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# API 호출 수행
data = fetch_box_office(api_key, target_dt)

# 4. 예외 및 에러 처리 안내
if data is None:
    st.error(
        "요청 처리 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    )
    st.stop()

if "faultInfo" in data:
    st.error(
        "API 키가 올바르지 않거나 API 서버에서 오류가 발생했습니다. KOBIS_KEY 값을 확인해 주세요."
    )
    st.info(f"상세 오류: {data['faultInfo'].get('message', '알 수 없는 오류')}")
    st.stop()

daily_list = (
    data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
    if data
    else []
)

if not daily_list:
    st.warning(
        "조회된 영화 목록이 없습니다. API 상태나 입력된 날짜를 확인해 주세요."
    )
    st.stop()

# 5. 데이터 가공 및 숫자형 변환
df = pd.DataFrame(daily_list)

numeric_cols = ["rank", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# 순위 정렬
df = df.sort_values(by="rank").reset_index(drop=True)

# 6. 1위 영화 주요 지표 카드 표시
top_movie = df.iloc[0]

st.subheader(f"🏆 1위 영화: {top_movie['movieNm']}")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("일일 관객수", f"{top_movie['audiCnt']:,} 명")
with col2:
    st.metric("누적 관객수", f"{top_movie['audiAcc']:,} 명")
with col3:
    st.metric("스크린수", f"{top_movie['scrnCnt']:,} 개")

st.divider()

# 7. 관객수 상위 5편 막대그래프
st.subheader("📊 관객수 상위 5개 영화")
top_5_df = df.head(5)

# 시각화를 위해 순서 정렬 및 컬럼 변경
chart_data = top_5_df.set_index("movieNm")[["audiCnt"]]
chart_data.columns = ["관객수"]
st.bar_chart(chart_data)

st.divider()

# 8. 전체 순위 표 표시
st.subheader("📋 전체 순위 목록")

# 화면에 보여줄 컬럼 가공 및 이름 변경
display_df = df[
    ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].copy()
display_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수(명)",
    "누적관객수(명)",
    "스크린수",
]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(format="%d"),
        "관객수(명)": st.column_config.NumberColumn(format="%d"),
        "누적관객수(명)": st.column_config.NumberColumn(format="%d"),
        "스크린수": st.column_config.NumberColumn(format="%d"),
    },
)
