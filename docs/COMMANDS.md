# 🎮 명령어 가이드

**DinoBot의 모든 명령어를 한눈에 확인하세요!**

## 📋 기본 명령어

### Task 관리

#### `/task` - Task 생성
```bash
/task person:홍길동 name:"로그인 기능 개발" priority:높음
/task person:김영희 name:"API 문서 작성" deadline:2024-01-15
/task person:정빈 name:"데이터베이스 설계" priority:중간
```

**파라미터:**
- `person` (필수): 담당자 이름
- `name` (필수): 작업 제목
- `priority` (선택): 우선순위 (높음, 중간, 낮음)
- `deadline` (선택): 마감일 (YYYY-MM-DD)

### 회의록 관리

#### `/meeting` - 회의록 생성
```bash
/meeting title:"주간 스프린트 회의" participants:홍길동,김영희
/meeting title:"기획 회의" participants:정빈,소현,동훈
/meeting title:"코드 리뷰" participants:홍길동
```

**파라미터:**
- `title` (필수): 회의 제목
- `participants` (필수): 참석자 목록 (쉼표로 구분)

### 문서 관리

#### `/document` - 문서 생성
```bash
/document title:"API 설계서" doc_type:개발문서
/document title:"프로젝트 기획안" doc_type:기획안
/document title:"회의록" doc_type:회의록
/document title:"개발 규칙" doc_type:개발규칙
```

**파라미터:**
- `title` (필수): 문서 제목
- `doc_type` (필수): 문서 유형 (개발문서, 기획안, 회의록, 개발규칙)

### 시스템 관리

#### `/status` - 시스템 상태 확인
```bash
/status
```

#### `/help` - 도움말
```bash
/help
```

#### `/fetch` - 최근 페이지 가져오기
```bash
/fetch
```

## 🔍 검색 명령어

### `/search` - 통합 검색
```bash
# 기본 검색
/search "API"

# 타입별 검색
/search "API" type:task
/search "회의" type:meeting
/search "설계" type:document

# 사용자별 검색
/search "개발" user:@정빈
/search "회의" user:@소현

# 기간별 검색
/search "API" days:7
/search "회의" days:30
/search "문서" days:90

# 복합 검색
/search "API 개발" type:task user:@정빈 days:14
/search "주간 회의" type:meeting user:@소현 days:7
```

**검색 옵션:**
- `type`: task, meeting, document
- `user`: @사용자명
- `days`: 7, 30, 90 (기본값: 90)

## 📊 통계 명령어

### 일별 통계

#### `/daily_stats` - 일별 활동 통계
```bash
# 오늘 통계
/daily_stats

# 특정 날짜 통계
/daily_stats date:2025-09-08
```

**결과:**
- 총 활동 수
- 타입별 분포 (task/meeting)
- 사용자별 분포
- 시간대별 상세 활동

### 주별 통계

#### `/weekly_stats` - 주별 활동 통계
```bash
# 이번 주 통계
/weekly_stats
```

**결과:**
- 주간 총 활동
- 요일별 분포
- 타입별 분포

### 월별 통계

#### `/monthly_stats` - 월별 활동 통계
```bash
# 이번 달 통계
/monthly_stats

# 특정 월 통계
/monthly_stats year:2025 month:9
```

**결과:**
- 월별 총 활동
- 주차별 분포
- 타입별/사용자별 분포

### 개인 통계

#### `/user_stats` - 개인 생산성 분석
```bash
# 최근 30일
/user_stats

# 최근 14일
/user_stats days:14
```

**결과:**
- 총 활동 수 및 일평균
- 가장 활발한 요일/시간
- 타입별 활동 분포

### 팀 통계

#### `/team_stats` - 팀 활동 비교
```bash
# 최근 30일
/team_stats

# 최근 7일
/team_stats days:7
```

**결과:**
- 팀 전체 활동
- 멤버별 활동 수 및 점수
- 상대적 생산성 비교

### Task 통계

#### `/task_stats` - Task 완료율
```bash
# 최근 30일
/task_stats

# 최근 7일
/task_stats days:7
```

**결과:**
- 총 Task 수
- 상태별 분포 (Done/In progress/Not started)
- 사용자별 완료율
- 최근 완료된 Task 목록

### 트렌드 분석

#### `/trends` - 활동 트렌드
```bash
# 최근 14일
/trends

# 최근 7일
/trends days:7
```

**결과:**
- 일평균 활동량
- 성장률 (전반기 vs 후반기)
- 가장 바쁜/조용한 날

## 🎯 명령어 사용 팁

### 효율적인 검색
1. **구체적인 키워드 사용**: "개발" 보다는 "API 개발"
2. **필터 조합**: 타입 + 사용자 + 기간으로 범위 좁히기
3. **최근 것부터**: days 값을 작게 해서 최신 것 우선

### 통계 활용법
1. **일일 스탠드업**: `/daily_stats`로 어제 활동 요약
2. **주간 회고**: `/weekly_stats`로 주간 패턴 분석
3. **개인 점검**: `/user_stats`로 개인 생산성 확인
4. **팀 관리**: `/team_stats`로 팀원별 기여도 비교

### 명령어 조합
```bash
# 빠른 확인
/search "키워드" days:3

# 정확한 탐색
/search "구체적 키워드" type:task user:@사용자

# 전체 탐색
/search "키워드" days:90
```

## ⚠️ 주의사항

### 명령어 제한
- 최대 20개 결과까지만 표시
- 최대 90일 이내 데이터만 검색
- 2글자 이상 키워드만 가능

### 권한 요구사항
- Task/Meeting 생성: 서버 멤버 권한
- 통계 조회: 서버 멤버 권한
- 시스템 관리: 관리자 권한

### 성능 고려사항
- 복잡한 검색은 시간이 걸릴 수 있음
- 통계 생성 시 차트 이미지 생성으로 지연 가능
- 대량 데이터 처리 시 응답 시간 증가

## 🔧 문제 해결

### 명령어가 작동하지 않는 경우
1. 봇이 온라인 상태인지 확인
2. 슬래시 명령어 권한 확인
3. 명령어 파라미터 형식 확인

### 검색 결과가 없는 경우
1. 키워드 철자 확인
2. 검색 범위 확대 (days 값 증가)
3. 타입 필터 제거

### 통계가 표시되지 않는 경우
1. 데이터베이스에 데이터가 있는지 확인
2. 권한 설정 확인
3. 봇 로그 확인

---

**더 자세한 정보는 [README.md](README.md)를 참조하세요!**
