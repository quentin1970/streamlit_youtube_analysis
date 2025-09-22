import os
import re
import streamlit as st
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="YouTube 인기 동영상",
    page_icon="▶️",
    layout="wide"
)

# 국가 코드와 이름 매핑
REGION_CODES = {
    '🇰🇷 대한민국': 'KR',
    '🇺🇸 미국': 'US',
    '🇯🇵 일본': 'JP',
    '🇬🇧 영국': 'GB',
    '🇨🇦 캐나다': 'CA',
    '🇦🇺 호주': 'AU',
    '🇩🇪 독일': 'DE',
    '🇫🇷 프랑스': 'FR',
    '🇮🇳 인도': 'IN',
    '🇧🇷 브라질': 'BR'
}

# 국가 코드를 한국어 이름으로 변환
CODE_TO_NAME = {v: k.split(' ')[1] for k, v in REGION_CODES.items()}

def get_channel_info(api_key: str, channel_id: str) -> Dict:
    """Fetch channel information including subscriber count."""
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        'part': 'statistics,snippet',
        'id': channel_id,
        'key': api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'items' in data and data['items']:
            item = data['items'][0]
            return {
                'statistics': item.get('statistics', {}),
                'snippet': item.get('snippet', {})
            }
        return {'statistics': {}, 'snippet': {}}
    except Exception as e:
        st.error(f"채널 정보를 가져오는 중 오류 발생: {e}")
        return {'statistics': {}, 'snippet': {}}

def get_popular_videos(api_key: str, region_code: str = 'KR', max_results: int = 30) -> List[Dict]:
    """Fetch popular videos from YouTube using direct API calls."""
    base_url = "https://www.googleapis.com/youtube/v3/videos"
    
    # Get popular videos with additional statistics
    params = {
        'part': 'snippet,statistics,contentDetails',
        'chart': 'mostPopular',
        'regionCode': region_code,
        'maxResults': max_results,
        'key': api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        videos = []
        channel_cache = {}  # 채널 정보 캐시
        
        for item in data.get('items', []):
            video_id = item['id']
            channel_id = item['snippet']['channelId']
            
            # 채널 정보 가져오기 (캐시에 없을 경우에만 API 호출)
            if channel_id not in channel_cache:
                channel_cache[channel_id] = get_channel_info(api_key, channel_id)
            
            channel_data = channel_cache[channel_id]
            channel_stats = channel_data.get('statistics', {})
            channel_snippet = channel_data.get('snippet', {})
            
            video = {
                'id': video_id,
                'title': item['snippet']['title'],
                'channel': item['snippet']['channelTitle'],
                'channel_id': channel_id,
                'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                'views': int(item['statistics'].get('viewCount', 0)),
                'likes': int(item['statistics'].get('likeCount', 0)),
                'comments': int(item['statistics'].get('commentCount', 0)),
                'subscribers': int(channel_stats.get('subscriberCount', 0)) if channel_stats else 0,
                'published_at': item['snippet']['publishedAt'],
                'duration': item['contentDetails'].get('duration', 'PT0S'),
                'channel_thumbnail': channel_snippet.get('thumbnails', {}).get('default', {}).get('url', '')
            }
            videos.append(video)
            
        return videos
    except Exception as e:
        st.error(f"YouTube API 오류가 발생했습니다: {e}")
        return []

def format_count(count: int) -> str:
    """Format large numbers to a more readable format."""
    if count >= 100000000:
        return f"{count / 100000000:.1f}억"
    elif count >= 10000:
        return f"{count / 10000:.1f}만"
    return f"{count:,}"

def format_duration(duration: str) -> str:
    """Convert ISO 8601 duration to human-readable format."""
    
    # Extract hours, minutes, and seconds using regex
    hours = int(re.search(r'(\d+)H', duration)[1]) if 'H' in duration else 0
    minutes = int(re.search(r'(\d+)M', duration)[1]) if 'M' in duration else 0
    seconds = int(re.search(r'(\d+)S', duration)[1]) if 'S' in duration else 0
    
    # Format as HH:MM:SS or MM:SS
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

def format_published_date(published_at):
    """Format published date to a relative time string."""
    published = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%SZ')
    now = datetime.utcnow()
    delta = now - published
    
    if delta.days > 365:
        years = delta.days // 365
        return f"{years}년 전"
    elif delta.days > 30:
        months = delta.days // 30
        return f"{months}개월 전"
    elif delta.days > 0:
        return f"{delta.days}일 전"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours}시간 전"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes}분 전"
    else:
        return "방금 전"

def main():
    st.title("YouTube 인기 동영상 🎬")
    
    # 사이드바 설정
    st.sidebar.title("설정")
    
    # Get API key from environment or secrets
    api_key = None
    
    # Method 1: Try to get from environment variables
    try:
        import os
        api_key = os.getenv('YOUTUBE_API_KEY')
        if api_key:
            st.sidebar.success("API key loaded from environment variables")
    except Exception as e:
        st.sidebar.warning(f"Environment variable error: {str(e)}")
    
    # Method 2: Try to get from secrets.toml
    if not api_key:
        try:
            # This is a safer way to access secrets that won't fail if secrets.toml doesn't exist
            if hasattr(st, 'secrets') and 'secrets' in st:
                api_key = st['secrets'].get('YOUTUBE_API_KEY')
                if api_key:
                    st.sidebar.success("API key loaded from secrets.toml")
        except Exception as e:
            st.sidebar.warning("Could not load API key from secrets.toml")
    
    # Method 3: Try direct file read as last resort
    if not api_key:
        try:
            import os
            secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
            if os.path.exists(secrets_path):
                import toml
                with open(secrets_path, 'r') as f:
                    secrets = toml.load(f)
                    api_key = secrets.get('secrets', {}).get('YOUTUBE_API_KEY')
                    if api_key:
                        st.sidebar.success("API key loaded from file")
        except Exception as e:
            st.sidebar.warning("Could not load API key from file")
    
    if not api_key:
        st.error("""
        ❌ YouTube API 키를 찾을 수 없습니다. 다음 방법 중 하나를 선택해주세요:
        
        **방법 1: 로컬에서 실행할 때**
        1. 프로젝트 루트에 `.env` 파일을 생성하세요.
        2. 다음 내용을 추가하세요:
           ```
           YOUTUBE_API_KEY=your_api_key_here
           ```
           
        **방법 2: Streamlit Cloud에 배포할 때**
        1. Streamlit Cloud의 앱 설정에서 'Secrets' 탭을 클릭하세요.
        2. 다음 내용을 추가하세요:
           ```
           [secrets]
           YOUTUBE_API_KEY = "your_api_key_here"
           ```
           
        [YouTube Data API](https://console.cloud.google.com/apis/library/youtube.googleapis.com)에서 API 키를 발급받을 수 있습니다.
        """)
        return
    
    # 지역 선택
    selected_region_key = st.sidebar.selectbox(
        '지역 선택:',
        list(REGION_CODES.keys()),
        index=0  # 기본값으로 대한민국 선택
    )
    region_code = REGION_CODES[selected_region_key]
    region_name = selected_region_key.split(' ')[1]  # 이모지 제거하고 한국어 이름만 추출
    
    # 결과 수 선택
    max_results = st.sidebar.slider("표시할 동영상 수:", 10, 50, 30, 10)
    
    st.markdown(f"### {region_name}에서 인기 있는 동영상 {max_results}개")
    
    # Add refresh button
    if st.sidebar.button("새로고침 🔄"):
        st.experimental_rerun()
    
    # Load videos
    with st.spinner(f'{region_name}의 인기 동영상을 불러오는 중...'):
        videos = get_popular_videos(api_key, region_code, max_results)
    
    if not videos:
        st.warning("동영상을 불러오는 데 실패했습니다. API 키를 확인해주세요.")
        return
        
    # 조회수(view_count) 기준으로 내림차순 정렬
    videos.sort(key=lambda x: x.get('views', 0), reverse=True)
    
    # Display videos in a grid
    cols = 3
    rows = (len(videos) + cols - 1) // cols
    
    for i in range(rows):
        row_videos = videos[i*cols:(i+1)*cols]
        cols_list = st.columns(cols)
        
        for idx, video in enumerate(row_videos):
            with cols_list[idx]:
                # 썸네일과 재생시간
                st.image(
                    video['thumbnail'],
                    use_container_width=True
                )
                
                # 제목
                st.markdown(f"**{video['title']}**")
                
                # 동영상 설명 (1줄 요약)
                if 'description' in video and video['description']:
                    # 설명이 긴 경우 50자로 제한하고 말줄임표 추가
                    description = video['description'].strip()
                    if len(description) > 50:
                        description = description[:47] + '...'
                    st.caption(description, help=video['description'])
                
                # 채널 정보
                col1, col2 = st.columns([1, 5])
                with col1:
                    if video['channel_thumbnail']:
                        st.image(video['channel_thumbnail'], width=30)
                with col2:
                    st.markdown(f"{video['channel']}")
                
                # 통계 정보
                st.markdown(f"👁️ {format_count(video['views'])}회 • ⏳ {format_published_date(video['published_at'])}")
                st.markdown(f"⏱️ {format_duration(video['duration'])}")
                
                # 구분선
                st.markdown("---")

if __name__ == "__main__":
    main()
