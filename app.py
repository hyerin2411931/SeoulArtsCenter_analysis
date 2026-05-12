import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

# --- 페이지 설정 ---
st.set_page_config(page_title="예술의전당 데이터 분석", layout="wide")

# --- 데이터베이스 연결 함수 ---
def get_connection():
    db_path = 'SeoulArtsCenter.db'
    if not os.path.exists(db_path):
        st.error(f"⚠️ '{db_path}' 파일을 찾을 수 없습니다. 데이터베이스 파일이 같은 폴더에 있는지 확인해주세요!")
        st.stop()
    return sqlite3.connect(db_path)

# --- 메인 화면 타이틀 ---
st.title("🎨 예술의전당 공공데이터 분석 대시보드")
st.markdown("예술의전당 공연 및 관람객 현황을 한눈에 파악하는 대시보드입니다.")

conn = get_connection()

# --- 사이드바 필터 ---
st.sidebar.header("🔍 필터 설정")
selected_category = st.sidebar.multiselect(
    "공연/전시 구분", ["공연", "전시"], default=["공연", "전시"]
)
selected_type = st.sidebar.radio("공연 구분", ["기획", "대관"])

# --- [차트 1] 연도별 관람객 추이 ---
st.subheader("1. 연도별 관람객 추이 (유/무료 합산)")

sql1 = f"""
SELECT year, category, SUM(paid) as 유료, SUM(free) as 무료, SUM(total) as 전체
FROM audience
WHERE category IN ({','.join(['?']*len(selected_category))})
GROUP BY year, category
"""
df1 = pd.read_sql(sql1, conn, params=selected_category)

# 시각화
fig1 = px.line(df1, x='year', y='전체', color='category', markers=True,
              title="연도별 관람객 합산 추이",
              labels={'year': '연도', '전체': '관람객 수'})
st.plotly_chart(fig1, use_container_width=True)

st.info(f"""
**💡 SQL:** `SELECT year, category, SUM(total)... GROUP BY year, category`  
**💡 인사이트:** {selected_category} 분야의 연도별 관람객 변화를 확인할 수 있습니다. 
무료 관람객 대비 유료 관람객의 비중이 수익성에 큰 영향을 미치는 핵심 지표입니다.
""")

# --- [차트 2] 장르별 공연 건수 vs 평균 관람객 ---
st.subheader("2. 장르별 공연 건수 및 평균 관람객")

sql2 = """
SELECT p.genre, COUNT(p.title) as 공연건수, AVG(a.total) as 평균관람객
FROM performance p
JOIN audience a ON p.title = a.title AND p.year = a.year
WHERE p.type = ? AND p.duration_days > 0
GROUP BY p.genre
"""
df2 = pd.read_sql(sql2, conn, params=[selected_type])

# 이중 막대/라인 차트 시각화
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=df2['genre'], y=df2['공연건수'], name='공연 건수', yaxis='y1'))
fig2.add_trace(go.Scatter(x=df2['genre'], y=df2['평균관람객'], name='평균 관람객', yaxis='y2', mode='lines+markers'))

fig2.update_layout(
    title=f"장르별 성과 분석 ({selected_type} 기준)",
    yaxis=dict(title="공연 건수"),
    yaxis2=dict(title="평균 관람객 수", overlaying='y', side='right'),
    legend=dict(x=1.1, y=1)
)
st.plotly_chart(fig2, use_container_width=True)

st.info(f"""
**💡 SQL:** `JOIN performance AND audience... WHERE duration_days > 0`  
**💡 인사이트:** {selected_type} 공연 중 어떤 장르가 가장 많이 열리는지, 
또 공연 횟수 대비 관람객 동원력이 높은 알짜배기 장르가 무엇인지 비교 분석할 수 있습니다.
""")

# --- [차트 3] 서울 자치구별 공연장 규모별 인프라 분석 ---
st.subheader("3. 자치구별 공연장 규모 상세 분석 (대/중/소)")

# 1. 데이터 불러오기 (규모별 컬럼 추가)
sql3 = """
SELECT district, large, medium, small, total 
FROM venue_stats 
WHERE year = (SELECT MAX(year) FROM venue_stats)
ORDER BY total DESC
"""
df3 = pd.read_sql(sql3, conn)

# 2. 사용자 선택 필터 (라디오 버튼)
st.markdown("🔍 **보고 싶은 공연장 규모를 선택하세요:**")
size_option = st.radio(
    "규모 선택", 
    ["전체(Total)", "대형(Large)", "중형(Medium)", "소형(Small)"], 
    horizontal=True
)

# 선택한 옵션에 따른 컬럼 매핑
column_map = {
    "전체(Total)": "total",
    "대형(Large)": "large",
    "중형(Medium)": "medium",
    "소형(Small)": "small"
}
selected_col = column_map[size_option]

# 3. 시각화 (선택된 규모 강조 차트)
fig_selected = px.bar(
    df3, 
    x='district', 
    y=selected_col,
    title=f"자치구별 {size_option} 공연장 수",
    labels={selected_col: '공연장 수', 'district': '자치구'},
    color=selected_col,
    color_continuous_scale='Reds' if "Large" in size_option else 'Blues'
)
st.plotly_chart(fig_selected, use_container_width=True)

# 4. 전체 규모 비중 확인 (누적 막대 차트)
with st.expander("📊 자치구별 대/중/소 비중 한눈에 보기"):
    # Plotly로 누적 막대 차트를 그리기 위해 데이터 재구성 (Wide to Long format)
    df_melted = df3.melt(
        id_vars=['district'], 
        value_vars=['large', 'medium', 'small'],
        var_name='Size', value_name='Count'
    )
    
    fig_stack = px.bar(
        df_melted, 
        x='district', 
        y='Count', 
        color='Size',
        title="자치구별 공연장 규모 구성비",
        labels={'Count': '공연장 수', 'district': '자치구', 'Size': '규모'},
        barmode='stack' # 누적 형식
    )
    st.plotly_chart(fig_stack, use_container_width=True)

# 5. 인사이트
st.info(f"""
**💡 사용한 SQL:** `SELECT district, large, medium, small, total FROM venue_stats...`  
**💡 인사이트:** 
- **{size_option}** 기준으로 볼 때, 가장 인프라가 집중된 곳은 **{df3.loc[df3[selected_col].idxmax(), 'district']}**입니다.
- 대형 공연장은 주로 특정 구에 밀집되어 있는 반면, 소형 공연장은 여러 구에 골고루 분포되어 있는지 확인해보세요. 
- 누적 차트를 통해 전체 개수(`total`)가 적더라도 특정 규모(예: 소형)가 발달한 지역을 찾아낼 수 있습니다.
""")
conn.close()