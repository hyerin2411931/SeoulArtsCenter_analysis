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

# --- [차트 1] 연도별 관람객 추이 (유/무료/전체 선택) ---
st.subheader("1. 연도별 관람객 추이 분석")

# 1. 데이터 불러오기 (유료, 무료, 전체 합계 모두 가져오기)
sql1 = f"""
SELECT year, category, 
       SUM(paid) as 유료, 
       SUM(free) as 무료, 
       SUM(total) as 전체
FROM audience
WHERE category IN ({','.join(['?']*len(selected_category))})
GROUP BY year, category
ORDER BY year ASC
"""
df1 = pd.read_sql(sql1, conn, params=selected_category)

# 2. 사용자 선택 필터 (관람객 유형)
metric_option = st.radio(
    "보고 싶은 관람객 유형을 선택하세요:",
    ["전체", "유료", "무료"],
    horizontal=True,
    key="metric_radio" # 고유 키 설정
)

# 3. 시각화 (선택된 유형에 따라 y축 변경)
fig1 = px.line(
    df1, 
    x='year', 
    y=metric_option, 
    color='category', 
    markers=True,
    title=f"연도별 {metric_option} 관람객 추이",
    labels={'year': '연도', metric_option: f'{metric_option} 관람객 수'},
    color_discrete_map={'공연': '#1f77b4', '전시': '#ff7f0e'} # 색상 고정
)

# 차트 예쁘게 다듬기
fig1.update_layout(hovermode="x unified")
st.plotly_chart(fig1, use_container_width=True)

# 4. 인사이트
st.info(f"""
**💡 사용한 SQL:** `SUM(paid), SUM(free), SUM(total)`를 한 번에 계산하여 효율성을 높였습니다.  
**💡 인사이트:** 
- **{metric_option}** 관람객 데이터를 통해 연도별 성과를 확인할 수 있습니다.
- 유료 관람객이 줄어드는데 전체 관람객이 유지된다면, 무료 초대권이나 공공 행사가 늘어났음을 짐작할 수 있습니다.
- 반대로 유료 관람객이 늘어난다면 공연/전시의 콘텐츠 경쟁력이 강화되었다고 해석할 수 있습니다.
""")
# --- [차트 2] 장르별 작품 편수 vs 평균 관람객 분석 ---
st.subheader("2. 장르별 작품 편수 및 관람객 효율 분석")

# 1. 데이터 불러오기 (COUNT와 AVG 활용)
# performance의 type(기획/대관) 필터 및 duration_days > 0 조건 적용
sql2 = """
SELECT p.genre as 장르, 
       COUNT(p.title) as 작품편수, 
       ROUND(AVG(a.total), 0) as 평균관람객
FROM performance p
JOIN audience a ON p.title = a.title AND p.year = a.year
WHERE p.type = ? 
  AND p.duration_days > 0
GROUP BY p.genre
ORDER BY 작품편수 DESC
"""
df2 = pd.read_sql(sql2, conn, params=[selected_type])

# 2. 시각화 (이중 축 차트)
fig2 = go.Figure()

# 작품 편수 (막대 그래프)
fig2.add_trace(go.Bar(
    x=df2['장르'], 
    y=df2['작품편수'], 
    name='작품 편수 (건)',
    marker_color='royalblue',
    yaxis='y1'
))

# 평균 관람객 (라인 그래프)
fig2.add_trace(go.Scatter(
    x=df2['장르'], 
    y=df2['평균관람객'], 
    name='평균 관람객 (명)',
    line=dict(color='firebrick', width=3),
    mode='lines+markers',
    yaxis='y2'
))

# 레이아웃 설정 (이중 축)
fig2.update_layout(
    title=f"장르별 성과 지표 ({selected_type} 기준)",
    xaxis=dict(title="장르"),
    yaxis=dict(title="작품 편수 (건)", side='left', showgrid=False),
    yaxis2=dict(title="평균 관람객 (명)", side='right', overlaying='y', showgrid=True),
    legend=dict(x=1.05, y=1),
    hovermode="x unified"
)

st.plotly_chart(fig2, use_container_width=True)

# 3. 인사이트
st.info(f"""
**💡 사용한 SQL:**  
`COUNT(p.title)`로 장르별 공급량(편수)을, `AVG(a.total)`로 수요(관람객)를 계산했습니다.  
**💡 인사이트:** 
- 현재 **{selected_type}** 부문에서 가장 많은 작품이 상영된 장르는 **{df2.iloc[0]['장르'] if not df2.empty else 'N/A'}**입니다.
- **막대는 높은데 라인이 낮다면?** 해당 장르는 다작(多作)은 하지만 편당 흥행력은 고민해 볼 필요가 있습니다.
- **막대는 낮은데 라인이 높다면?** 소수의 작품으로 많은 관객을 모으는 '고효율 장르'임을 의미합니다.
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