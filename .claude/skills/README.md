# FastAPI-Playground Claude Code Skills

프로젝트 개발 속도를 향상시키는 커스텀 Claude Code SKILL 모음입니다.

## 📚 목차

- [SKILL이란?](#skill이란)
- [컨벤션 시스템](#컨벤션-시스템)
- [SKILL 목록](#skill-목록)
- [사용 플로우](#사용-플로우)
- [실전 시나리오](#실전-시나리오)
- [커스터마이징](#커스터마이징)

---

## SKILL이란?

**SKILL**은 Claude Code가 특정 작업을 수행할 때 참조하는 **프로젝트 특화 가이드**입니다.

### 작동 방식

```
사용자: "Product 도메인 추가해줘"
    ↓
Claude가 "new-domain" SKILL을 자동으로 로드
    ↓
SKILL 내의 컨벤션과 템플릿을 따라 코드 생성
    ↓
프로젝트 패턴과 100% 일치하는 코드 완성
```

### 기존 방식 vs SKILL 방식

| 작업 | 기존 방식 | SKILL 방식 |
|------|----------|-----------|
| 새 도메인 추가 | 기존 코드 복사 → 수동 수정 → 컨벤션 확인 (30분) | `/new-domain product` (2분) |
| 엔드포인트 추가 | router → service → repository 순차 작성 (15분) | `/add-endpoint` → 자동 생성 (3분) |
| DB 마이그레이션 | alembic 명령어 찾기 → 실행 → 검증 (10분) | `/db-migrate create` (1분) |
| 환경 전환 | docker-compose 파일 찾기 → 명령어 입력 (5분) | `/docker-env switch prod` (30초) |

---

## 컨벤션 시스템

### 1. 중앙 컨벤션 파일

```yaml
# .claude/skills/new-domain/conventions.yaml

naming:
  router:
    function: "{domain}_{action}"  # question_list
    prefix: "/api/{domain}"

  service:
    function: "{action}_{domain}"  # get_question

messages:
  errors:
    not_found: "{Domain}을 찾을 수 없습니다"
    no_permission: "권한이 없습니다."
```

### 2. 컨벤션 적용 예시

**입력:**
```
도메인: product
액션: create
```

**자동 생성되는 코드:**

```python
# router.py
@router.post("/create", status_code=status.HTTP_204_NO_CONTENT)
async def product_create(  # {domain}_{action}
    _product_create: product_schema.ProductCreate,  # 언더스코어 접두사
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    await product_service.create_product(...)  # {action}_{domain}

# service.py
async def create_product(  # {action}_{domain}
    db: AsyncSession,
    product_create: ProductCreate,
    user: User
):
    db_product = Product(
        name=product_create.name,
        price=product_create.price,
        create_date=datetime.now(),  # 표준 필드
        user=user
    )
    db.add(db_product)
    await db.commit()  # 명시적 커밋
```

### 3. 컨벤션 체크리스트

생성된 모든 코드는 자동으로 검증됩니다:

- ✅ 네이밍 규칙: `{domain}_{action}`, `{action}_{domain}`
- ✅ 한글 에러 메시지
- ✅ async/await 패턴
- ✅ 표준 필드: `create_date`, `modify_date`
- ✅ 권한 검증: `current_user.id != model.user_id`
- ✅ 관계 로딩: `selectinload`
- ✅ 명시적 커밋: `await db.commit()`

---

## SKILL 목록

### 1. `/new-domain` - 새 도메인 생성

#### 사용 시점
- 새로운 비즈니스 모듈 추가
- CRUD API가 필요한 엔티티 생성

#### 사용 방법
```bash
# 방법 1: 직접 호출
/new-domain product

# 방법 2: 자연어
"상품(Product) 도메인을 추가해줘"
"댓글 기능을 만들고 싶어"
```

#### 플로우
```
1. 도메인 정보 수집
   ├─ 도메인 이름 (product)
   ├─ 주요 필드 (name:String, price:Integer)
   ├─ CRUD 엔드포인트 선택
   ├─ 인증 필요 여부
   └─ 추가 기능 (투표, 검색 등)

2. 파일 생성
   ├─ models.py (SQLAlchemy 모델)
   ├─ schemas.py (Pydantic 스키마 6개)
   ├─ service.py (비즈니스 로직 6개 함수)
   └─ router.py (엔드포인트 5-6개)

3. main.py 라우터 등록
   └─ app.include_router(product_router.router)

4. DB 마이그레이션 (선택)
   └─ alembic revision + upgrade

5. 완료 리포트
   └─ 생성된 파일, 엔드포인트 목록, 다음 단계
```

#### 생성되는 엔드포인트
```
GET  /api/product/list              # 목록 조회 (페이징, 검색)
GET  /api/product/detail/{id}       # 상세 조회
POST /api/product/create            # 생성 (인증 필요)
PUT  /api/product/update            # 수정 (권한 검증)
DELETE /api/product/delete          # 삭제 (권한 검증)
POST /api/product/vote (선택)       # 투표 (이벤트 발행)
```

#### 예상 시간
- 수동: ~30분 (파일 생성, 코드 작성, 테스트)
- SKILL: ~2분 (질문 답변, 코드 생성)

---

### 2. `/add-endpoint` - 엔드포인트 추가

#### 사용 시점
- 기존 도메인에 새 API 추가
- 커스텀 비즈니스 로직 엔드포인트

#### 사용 방법
```bash
/add-endpoint

# 또는
"question에 좋아요 수 조회 API 추가해줘"
```

#### 플로우
```
1. 도메인 선택
   └─ 기존 도메인 목록에서 선택

2. 엔드포인트 정보 수집
   ├─ 이름: like_count
   ├─ 메서드: GET
   ├─ 경로: /api/question/like-count/{id}
   ├─ 파라미터: question_id:int
   ├─ 응답: LikeCountResponse (새 스키마)
   ├─ 인증: 필요
   └─ 로직: "좋아요 수 집계 및 사용자 투표 여부"

3. 스키마 생성 (필요 시)
   └─ schemas.py에 LikeCountResponse 추가

4. 서비스 함수 생성
   └─ service.py에 get_like_count() 추가

5. 라우터 엔드포인트 추가
   └─ router.py에 question_like_count() 추가

6. 테스트 안내
   └─ API 문서 URL, 샘플 요청
```

#### 지원 패턴
- **GET 단건**: `/resource/{id}` → 상세 조회
- **GET 목록**: `/resource/list?page=0&size=10` → 페이징
- **POST 생성**: `/resource` → 리소스 생성
- **PUT 수정**: `/resource` → 리소스 업데이트
- **POST 액션**: `/resource/{action}` → 커스텀 액션

#### 예상 시간
- 수동: ~15분 (3개 파일 수정)
- SKILL: ~3분

---

### 3. `/db-migrate` - DB 마이그레이션

#### 사용 시점
- 모델 변경 후 스키마 동기화
- 마이그레이션 롤백 필요 시
- 히스토리 확인

#### 명령어

##### 생성
```bash
/db-migrate create "Add view_count to question"
```
- 모델 변경사항 자동 감지
- 마이그레이션 파일 생성
- 변경사항 미리보기
- 수동 편집 옵션

##### 적용
```bash
/db-migrate apply
```
- 자동 백업 수행
- 안전 체크
- 스키마 적용
- 적용 후 검증

##### 롤백
```bash
/db-migrate rollback
```
- 히스토리 표시
- 영향 분석
- 안전 확인
- 롤백 실행

##### 상태 확인
```bash
/db-migrate status
```
- 현재 리비전
- 미적용 마이그레이션
- 모델 동기화 상태

##### 히스토리
```bash
/db-migrate history
```
- 마이그레이션 히스토리
- 리비전 트리
- 작성자/날짜 정보

#### 안전 기능
- ✅ 적용 전 자동 백업
- ✅ 위험한 작업 추가 확인
- ✅ 롤백 가능성 검증
- ✅ 데이터 손실 경고

#### 예상 시간
- 수동: ~10분 (명령어 찾기, 실행, 검증)
- SKILL: ~1분

---

### 4. `/docker-env` - 환경 관리

#### 사용 시점
- 개발/운영 환경 전환
- 성능 테스트 실행
- 모니터링 시작/중지

#### 명령어

##### 환경 전환
```bash
/docker-env switch prod
```
1. 현재 환경 감지
2. 전환 확인
3. 기존 환경 정리
4. 새 환경 시작
5. 헬스체크
6. 접속 정보 출력

##### 상태 확인
```bash
/docker-env status
```
- 현재 환경
- 서비스 상태 테이블
- 리소스 사용량
- 볼륨 크기

##### 로그 확인
```bash
/docker-env logs app
```
- 서비스 선택
- 실시간/범위 선택
- 필터링 (에러만)

##### 재시작
```bash
/docker-env restart app
```
- 전체/부분 선택
- 빌드 옵션
- 헬스체크

##### 정리
```bash
/docker-env clean
```
- 중지/삭제 범위 선택
- 볼륨 포함 여부
- 디스크 공간 확보

#### 지원 환경
```
dev          개발 (단일 인스턴스, 핫 리로드)
prod         운영 (3 레플리카, Nginx)
loadbalance  로드밸런싱 테스트
monitoring   Prometheus + Grafana
test-single  성능 테스트 (단일)
test-multi   성능 테스트 (멀티)
massive      대규모 테스트 (10+ 인스턴스)
```

#### 예상 시간
- 수동: ~5분 (파일 찾기, 명령어 입력)
- SKILL: ~30초

---

## 사용 플로우

### 시나리오 1: 새 기능 개발

```
[요구사항]
"상품(Product) 관리 기능 추가"

[전체 플로우]
1. /new-domain product
   ├─ 필드: name, price, description, stock
   ├─ CRUD 전체 생성
   └─ 투표 기능 제외

2. /db-migrate create "Add product table"
   └─ 마이그레이션 생성 및 적용

3. /docker-env switch dev
   └─ 개발 환경으로 전환

4. 테스트
   └─ http://localhost:7777/docs

5. /add-endpoint
   ├─ 도메인: product
   ├─ 이름: low_stock_alert
   ├─ 로직: "재고 10개 미만 상품 조회"
   └─ GET /api/product/low-stock

6. /docker-env switch prod
   └─ 운영 환경에서 최종 검증

총 소요 시간: ~10분
(수동 작업 시: ~2시간)
```

### 시나리오 2: 버그 수정 및 배포

```
[요구사항]
"question 테이블에 조회수 필드 추가"

[전체 플로우]
1. models.py 수동 수정
   └─ view_count = Column(Integer, default=0)

2. /db-migrate create "Add view_count to question"
   └─ 변경사항 자동 감지

3. /db-migrate apply
   ├─ 백업 자동 수행
   └─ 스키마 적용

4. service.py 수정 (조회 시 증가 로직)
   └─ question.view_count += 1

5. /docker-env restart app
   └─ 애플리케이션 재시작

6. /docker-env logs app
   └─ 에러 없는지 확인

총 소요 시간: ~5분
```

### 시나리오 3: 성능 테스트

```
[요구사항]
"로드밸런싱 성능 측정"

[전체 플로우]
1. /docker-env switch loadbalance
   └─ 로드밸런싱 환경 시작

2. /docker-env start monitoring
   └─ Prometheus + Grafana 추가 실행

3. 부하 테스트 실행
   └─ ab -n 10000 -c 100 http://localhost/api/question/list

4. /docker-env logs nginx
   └─ 로드밸런싱 동작 확인

5. Grafana 대시보드 확인
   └─ http://localhost:3000

6. 인스턴스 수 조정
   └─ docker-compose scale app=5

7. 재측정 및 비교

총 소요 시간: ~20분
```

---

## 실전 시나리오

### 아침 출근 후

```bash
# 1. 환경 상태 확인
/docker-env status

# 2. 개발 환경 시작
/docker-env switch dev

# 3. 최근 로그 확인
/docker-env logs app | grep ERROR

# 4. 새 작업 시작
/new-domain order
```

### 배포 전 체크

```bash
# 1. 운영 환경으로 전환
/docker-env switch prod

# 2. DB 마이그레이션 확인
/db-migrate status

# 3. 미적용 마이그레이션 적용
/db-migrate apply

# 4. 헬스체크
curl http://localhost:7777/

# 5. 모니터링 시작
/docker-env start monitoring
```

### 긴급 버그 수정

```bash
# 1. 현재 상태 백업
/db-migrate backup

# 2. 코드 수정
(직접 파일 편집)

# 3. 빠른 재시작
/docker-env restart app

# 4. 로그 실시간 모니터링
/docker-env logs app

# 5. 문제 발생 시 롤백
/db-migrate rollback
```

---

## 커스터마이징

### 1. 새 SKILL 추가

```bash
# 디렉토리 생성
mkdir -p .claude/skills/my-skill

# SKILL 정의
cat > .claude/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: This skill should be used when...
version: 1.0.0
---

# My Custom Skill

[설명 작성]
EOF
```

### 2. 컨벤션 수정

```yaml
# .claude/skills/new-domain/conventions.yaml 편집

# 예: 에러 메시지를 영어로 변경
messages:
  errors:
    not_found: "Resource not found"
    no_permission: "Permission denied"
```

### 3. 템플릿 커스터마이징

```python
# .claude/skills/new-domain/templates/router.py.tmpl

# 예: 모든 엔드포인트에 rate limit 추가
from slowapi import Limiter

@router.get("/list")
@limiter.limit("10/minute")
async def {domain}_list(...):
    ...
```

---

## 문제 해결

### SKILL이 작동하지 않을 때

```bash
# 1. SKILL 디렉토리 확인
ls -la .claude/skills/

# 2. SKILL.md 형식 검증
# - Frontmatter (---로 감싸진 YAML) 확인
# - name, description 필드 존재 확인

# 3. Claude에게 명시적으로 요청
"/new-domain을 사용해서 product 도메인 만들어줘"
```

### 컨벤션이 적용되지 않을 때

```bash
# conventions.yaml 문법 확인
python -c "import yaml; yaml.safe_load(open('.claude/skills/new-domain/conventions.yaml'))"

# Claude에게 컨벤션 참조 요청
"conventions.yaml의 네이밍 규칙을 따라서 코드를 생성해줘"
```

---

## 다음 단계

### 추가 개발 권장 SKILL

```
1. /test-gen
   - 테스트 코드 자동 생성
   - pytest fixture 생성

2. /api-client
   - Python/TypeScript 클라이언트 생성
   - OpenAPI 스키마 기반

3. /monitoring-check
   - Prometheus 지표 조회
   - 이상 징후 탐지

4. /event-system
   - 이벤트 생성
   - 핸들러 추가

5. /perf-test
   - 성능 테스트 실행
   - 결과 분석 리포트
```

### 학습 리소스

```
- Claude Code 공식 문서: https://docs.anthropic.com/claude-code
- SKILL 개발 가이드: /help skills
- 프로젝트 README.md: 환경 설정 및 구조
```

---

## 요약

| SKILL | 사용 시점 | 주요 기능 | 시간 절약 |
|-------|----------|----------|----------|
| `/new-domain` | 새 도메인 추가 | 전체 레이어 생성 | 30분 → 2분 |
| `/add-endpoint` | API 추가 | 엔드포인트 자동 생성 | 15분 → 3분 |
| `/db-migrate` | 스키마 변경 | 마이그레이션 관리 | 10분 → 1분 |
| `/docker-env` | 환경 전환 | 환경 관리 | 5분 → 30초 |

**일일 평균 시간 절약: ~2-3시간** 🚀

---

## 피드백

SKILL 개선 아이디어가 있으시면 언제든지 공유해주세요!

```bash
# 예시
"new-domain SKILL에 GraphQL 지원 추가해줘"
"docker-env에 자동 스케일링 기능 넣어줘"
```
