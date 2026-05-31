# 불법 도박 사이트 신고 대시보드

AI로 탐지된 불법 도박 사이트 목록을 조회하고 신고할 수 있는 웹 대시보드입니다.

## 파일 구조

```
dashboard/
├── index.html    # 메인 HTML 파일
├── style.css     # 스타일시트
└── app.js        # JavaScript (Supabase 연결 및 데이터 로딩)
```

## 사용 방법

### 1. 로컬에서 실행

브라우저에서 `index.html` 파일을 직접 열어서 사용할 수 있습니다:

```bash
# Windows
start dashboard/index.html

# Mac
open dashboard/index.html

# Linux
xdg-open dashboard/index.html
```

또는 간단한 HTTP 서버를 실행:

```bash
# Python 3
cd dashboard
python -m http.server 8000

# 브라우저에서 http://localhost:8000 접속
```

### 2. 기능

**통계 섹션:**
- 전체 불법 사이트 수
- 평균 신뢰도
- 최근 업데이트 시각

**테이블 섹션:**
- 파비콘 미리보기
- URL (클릭하면 새 탭에서 열림)
- 검색 키워드
- AI 신뢰도 (색상으로 구분)
- 수집 일시
- 상세보기 버튼

**검색 기능:**
- URL 또는 키워드로 실시간 필터링

**상세보기 모달:**
- AI 판단 이유
- 탐지된 키워드 목록

### 3. 데이터베이스 연결

Supabase 데이터베이스에서 `gambling_urls` 테이블의 불법 사이트 데이터를 실시간으로 조회합니다.

현재 설정된 연결 정보:
- URL: `https://brdwgsnffgsmubnfjmyi.supabase.co`
- Table: `gambling_urls`
- Filter: `is_illegal = true`

### 4. 신고 방법

1. 대시보드에서 불법 사이트 확인
2. 상세보기 버튼 클릭하여 AI 판단 이유 확인
3. URL을 복사하여 관련 기관에 신고:
   - 사이버범죄 신고: https://ecrm.police.go.kr/
   - 방송통신심의위원회: https://www.kocsc.or.kr/

## 주의사항

- 이 대시보드는 조회 전용(read-only)입니다
- Supabase ANON_KEY를 사용하므로 데이터 수정 권한이 없습니다
- 불법 사이트 URL 클릭 시 주의하세요

## 기술 스택

- HTML5
- CSS3 (반응형 디자인)
- JavaScript (ES6+)
- Supabase JavaScript Client (CDN)

