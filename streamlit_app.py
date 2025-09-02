import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 초기 설정 ---
st.set_page_config(page_title="고등학교 정보 조회", layout="centered")
API_KEY = "d38e5a2ba36c4ff4915e1075ec47d74a"  # 실제 키 입력 필요

CITY_CODES = {
    '서울특별시': 'B10', '부산광역시': 'C10', '대구광역시': 'D10',
    '인천광역시': 'E10', '광주광역시': 'F10', '대전광역시': 'G10',
    '울산광역시': 'H10', '세종특별자치시': 'I10', '경기도': 'J10',
    '강원특별자치도': 'K10', '충청북도': 'M10', '충청남도': 'N10',
    '전북특별자치도': 'P10', '전라남도': 'Q10', '경상북도': 'R10',
    '경상남도': 'S10', '제주특별자치도': 'T10'
}

@st.cache_data(ttl=3600)
def search_school(office_code, school_name):
    if not school_name:
        return []
    API_URL = "https://open.neis.go.kr/hub/schoolInfo"
    params = {
        'KEY': API_KEY,
        'Type': 'json',
        'pIndex': 1,
        'pSize': 100,
        'ATPT_OFCDC_SC_CODE': office_code,
        'SCHUL_NM': school_name,
        'SCHUL_KND_SC_NM': '고등학교'
    }
    try:
        response = requests.get(API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if 'RESULT' in data and data['RESULT']['CODE'] != 'INFO-000':
            st.error(f"API 오류: {data['RESULT']['MESSAGE']}")
            return []
        if 'schoolInfo' in data:
            return data['schoolInfo'][1]['row']
    except Exception as e:
        st.error(f"학교 검색 오류: {e}")
    return []

@st.cache_data(ttl=600)
def get_timetable(office_code, school_code, date, grade, class_nm):
    API_URL = "https://open.neis.go.kr/hub/hisTimetable"
    params = {
        'KEY': API_KEY,
        'Type': 'json',
        'pIndex': 1,
        'pSize': 10,
        'ATPT_OFCDC_SC_CODE': office_code,
        'SD_SCHUL_CODE': school_code,
        'ALL_TI_YMD': date,
        'GRADE': grade,
        'CLASS_NM': class_nm
    }
    try:
        response = requests.get(API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if 'RESULT' in data and data['RESULT']['CODE'] != 'INFO-000':
            if data['RESULT']['CODE'] == 'INFO-200':
                st.info("해당 날짜의 시간표 정보가 없습니다.")
            else:
                st.warning(f"API 메시지: {data['RESULT']['MESSAGE']}")
            return pd.DataFrame()
        if 'hisTimetable' in data:
            timetable_data = [
                {'교시': item['PERIO'], '과목': item['ITRT_CNTNT']}
                for item in data['hisTimetable'][1]['row']
            ]
            df = pd.DataFrame(timetable_data)
            df['교시'] = pd.to_numeric(df['교시'])
            return df.sort_values(by='교시').reset_index(drop=True)
    except Exception as e:
        st.error(f"시간표 조회 오류: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=600)
def get_meal_info(office_code, school_code, date):
    """조식, 중식, 석식 급식 정보를 조회하여 딕셔너리로 반환."""
    API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        'KEY': API_KEY,
        'Type': 'json',
        'pIndex': 1,
        'pSize': 100,
        'ATPT_OFCDC_SC_CODE': office_code,
        'SD_SCHUL_CODE': school_code,
        'MLSV_YMD': date
    }
    try:
        response = requests.get(API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if 'RESULT' in data and data['RESULT']['CODE'] != 'INFO-000':
            if data['RESULT']['CODE'] == 'INFO-200':
                st.info("해당 날짜의 급식 정보가 없습니다.")
            else:
                st.warning(f"API 메시지: {data['RESULT']['MESSAGE']}")
            return {}

        meal_info_dict = {}
        for row in data['mealServiceDietInfo'][1]['row']:
            meal_type = row['MMEAL_SC_NM']  # 조식, 중식, 석식
            dishes = row['DDISH_NM'].replace('<br/>', '\n').replace('.', '').strip()
            meal_info_dict[meal_type] = dishes

        return meal_info_dict

    except Exception as e:
        st.error(f"급식 조회 오류: {e}")
    return {}

# --- Streamlit UI 구성 ---

st.title("🇰🇷 고등학교 정보 조회")
st.info("나이스 교육정보 개방 포털 API를 활용합니다.")

# 0. 모드 선택 (시간표 or 급식)
mode = st.radio("조회 항목을 선택하세요:", ["시간표 조회", "급식 조회"], horizontal=True)

# 1. 지역 선택
selected_city_name = st.selectbox("1. 지역을 선택하세요:", list(CITY_CODES.keys()))
office_code = CITY_CODES[selected_city_name]

# 2. 학교 이름 입력
school_name_input = st.text_input("2. 학교 이름을 입력하고 Enter를 누르세요:", placeholder="예) 서울고등학교")

if school_name_input:
    with st.spinner(f"{selected_city_name}에서 학교를 검색 중입니다..."):
        search_results = search_school(office_code, school_name_input)

    if not search_results:
        st.warning("검색된 학교가 없습니다. 학교 이름을 다시 확인해주세요.")
    else:
        school_options = {f"{school['SCHUL_NM']} ({school['ORG_RDNMA']})": school for school in search_results}
        selected_school_display_name = st.selectbox("3. 학교를 선택하세요:", list(school_options.keys()))
        
        if selected_school_display_name:
            selected_school_info = school_options[selected_school_display_name]
            school_code = selected_school_info['SD_SCHUL_CODE']

            st.divider()
            st.subheader(f"🏫 {selected_school_info['SCHUL_NM']}")

            selected_date = st.date_input("날짜 선택", datetime.today())
            formatted_date = selected_date.strftime("%Y%m%d")

            if mode == "시간표 조회":
                col1, col2 = st.columns(2)
                with col1:
                    grade_input = st.text_input("학년", value="1", max_chars=1)
                with col2:
                    class_input = st.text_input("반", value="1", max_chars=2)

                if st.button("시간표 조회하기", use_container_width=True, type="primary"):
                    if not grade_input or not class_input:
                        st.error("학년과 반을 모두 입력해주세요.")
                    else:
                        with st.spinner("시간표를 불러오는 중입니다..."):
                            timetable_df = get_timetable(
                                office_code,
                                school_code,
                                formatted_date,
                                grade_input,
                                class_input
                            )
                        if not timetable_df.empty:
                            st.success(f"{selected_date.strftime('%Y-%m-%d')} 시간표")
                            st.dataframe(timetable_df, hide_index=True, use_container_width=True)
            else:  # 급식 조회
                if st.button("급식 조회하기", use_container_width=True, type="primary"):
                    with st.spinner("급식 정보를 불러오는 중입니다..."):
                        meal_info = get_meal_info(office_code, school_code, formatted_date)
                    if meal_info:
                        st.success(f"{selected_date.strftime('%Y-%m-%d')} 급식 정보")

                        if "조식" in meal_info:
                            st.text_area("조식", meal_info["조식"], height=150)
                        else:
                            st.info("조식 정보가 없습니다.")

                        if "중식" in meal_info:
                            st.text_area("중식", meal_info["중식"], height=200)
                        else:
                            st.info("중식 정보가 없습니다.")

                        if "석식" in meal_info:
                            st.text_area("석식", meal_info["석식"], height=200)
