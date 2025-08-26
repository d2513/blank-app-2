import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 초기 설정 ---
st.set_page_config(page_title="고등학교 시간표 조회", layout="centered")

# 나이스 교육정보 개방 포털에서 발급받은 API 키를 입력하세요.
# https://open.neis.go.kr/
API_KEY = "d38e5a2ba36c4ff4915e1075ec47d74a"  # 👈 여기에 실제 발급받은 인증키를 입력하세요.

# 시도교육청 코드 (API 요청에 필요)
CITY_CODES = {
    '서울특별시': 'B10', '부산광역시': 'C10', '대구광역시': 'D10',
    '인천광역시': 'E10', '광주광역시': 'F10', '대전광역시': 'G10',
    '울산광역시': 'H10', '세종특별자치시': 'I10', '경기도': 'J10',
    '강원특별자치도': 'K10', '충청북도': 'M10', '충청남도': 'N10',
    '전북특별자치도': 'P10', '전라남도': 'Q10', '경상북도': 'R10',
    '경상남도': 'S10', '제주특별자치도': 'T10'
}

# --- API 호출 및 데이터 처리 함수 (캐시 적용) ---

# st.cache_data: 동일한 인자로 함수가 호출되면 API를 재요청하지 않고 저장된 결과를 즉시 반환 (속도 향상)
@st.cache_data(ttl=3600)  # 1시간 동안 캐시 유지
def search_school(office_code, school_name):
    """지정된 교육청에서 학교 정보를 검색합니다."""
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

        # API가 에러 코드를 반환하는 경우 처리
        if 'RESULT' in data and data['RESULT']['CODE'] != 'INFO-000':
            st.error(f"API 오류: {data['RESULT']['MESSAGE']}")
            return []

        if 'schoolInfo' in data:
            return data['schoolInfo'][1]['row']
    except requests.exceptions.RequestException as e:
        st.error(f"네트워크 오류가 발생했습니다: {e}")
    except (KeyError, IndexError):
        # 검색 결과가 없는 경우
        pass
    return []

@st.cache_data(ttl=600)  # 10분 동안 캐시 유지
def get_timetable(office_code, school_code, date, grade, class_nm):
    """학년, 반 정보를 포함하여 시간표를 조회합니다."""
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
            # 정보가 없는 것은 에러가 아니므로 경고로 표시
            if data['RESULT']['CODE'] == 'INFO-200':
                 st.info("해당 날짜의 시간표 정보가 없습니다. (휴일 또는 미입력)")
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

    except requests.exceptions.RequestException as e:
        st.error(f"시간표 조회 중 네트워크 오류가 발생했습니다: {e}")
    except (KeyError, IndexError):
        st.info("해당 날짜의 시간표 정보가 없습니다.")
    return pd.DataFrame()


# --- Streamlit UI 구성 ---

st.title("🚀 대한민국 고등학교 시간표 조회")
st.info("나이스 교육정보 개방 포털 API를 활용하여 데이터를 제공합니다.")

# 1. 지역 선택
selected_city_name = st.selectbox("1. 지역을 선택하세요:", list(CITY_CODES.keys()))
office_code = CITY_CODES[selected_city_name]

# 2. 학교 검색
school_name_input = st.text_input("2. 학교 이름을 입력하고 Enter를 누르세요:", placeholder="예) 서울고등학교")

if school_name_input:
    with st.spinner(f"{selected_city_name}에서 학교를 검색 중입니다..."):
        search_results = search_school(office_code, school_name_input)

    if not search_results:
        st.warning("검색된 학교가 없습니다. 학교 이름을 다시 확인해주세요.")
    else:
        # 학교 이름과 주소를 합쳐서 선택지에 표시 (동명 학교 구분)
        school_options = {f"{school['SCHUL_NM']} ({school['ORG_RDNMA']})": school for school in search_results}
        selected_school_display_name = st.selectbox("3. 학교를 선택하세요:", list(school_options.keys()))

        if selected_school_display_name:
            selected_school_info = school_options[selected_school_display_name]
            school_code = selected_school_info['SD_SCHUL_CODE']

            st.divider()
            st.subheader(f"🗓️ {selected_school_info['SCHUL_NM']} 시간표 조회")

            # 3. 날짜, 학년, 반 입력
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_date = st.date_input("날짜", datetime.today())
                formatted_date = selected_date.strftime("%Y%m%d")
            with col2:
                grade_input = st.text_input("학년", value="1", max_chars=1)
            with col3:
                class_input = st.text_input("반", value="1", max_chars=2)


            # 4. 시간표 조회 버튼
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
                        st.dataframe(timetable_df, hide_index=True, use_container_width=True)
                    # 정보가 없을 때의 메시지는 get_timetable 함수 내에서 처리
