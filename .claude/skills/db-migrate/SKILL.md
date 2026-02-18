---
name: db-migrate
description: This skill should be used when the user asks to "create migration", "apply migration", "rollback migration", "DB 마이그레이션", "alembic", or wants to manage database schema changes.
version: 1.0.0
---

# DB Migration Manager

Alembic을 사용한 데이터베이스 마이그레이션을 간편하게 관리합니다. 복잡한 alembic 명령어를 자동화하고 안전한 실행을 보장합니다.

## 사용 시점

- SQLAlchemy 모델 변경 후 DB 스키마 동기화
- 새 도메인 추가 후 테이블 생성
- 마이그레이션 롤백 필요 시
- 마이그레이션 히스토리 확인

## 실행 플로우

### 1. 마이그레이션 생성 (`/db-migrate create`)

#### 1.1 모델 변경 감지

```bash
📋 현재 마이그레이션 상태 확인 중...

현재 리비전: ea29476 (head)
미적용 마이그레이션: 없음

🔍 모델 변경사항 스캔 중...
```

**자동 체크 항목:**
- [ ] src/domains/*/models.py 파일 스캔
- [ ] 기존 DB 스키마와 비교
- [ ] 변경사항 탐지 (추가/수정/삭제된 컬럼, 테이블)

#### 1.2 변경사항 요약

```markdown
감지된 변경사항:

📦 새 테이블:
  - product (id, name, price, description, create_date, user_id)

🔧 수정된 테이블:
  - question
    + 추가된 컬럼: view_count (Integer, default=0)
    - 삭제된 컬럼: old_field

⚠️ 주의사항:
  - old_field 삭제 시 기존 데이터 손실 위험
```

#### 1.3 마이그레이션 메시지 입력

```bash
마이그레이션 메시지를 입력하세요:
예시: "Add product table and view_count to question"

입력: _______
```

사용자 입력이 없으면 자동 생성:
- `"Auto-migration: Add product, Modify question"`

#### 1.4 마이그레이션 파일 생성

```bash
$ alembic revision --autogenerate -m "Add product table and view_count to question"

생성된 파일:
📄 alembic/versions/abc123def456_add_product_table_and_view_count.py

변경사항 미리보기:
```

```python
def upgrade() -> None:
    # 새 테이블 생성
    op.create_table('product',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('create_date', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 기존 테이블 수정
    op.add_column('question', sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'))
    op.drop_column('question', 'old_field')

def downgrade() -> None:
    op.drop_table('product')
    op.drop_column('question', 'view_count')
    op.add_column('question', sa.Column('old_field', sa.String(255)))
```

#### 1.5 확인 및 수동 편집 옵션

```bash
마이그레이션 파일을 확인하시겠습니까?
1. 바로 적용 (권장)
2. 파일 열어서 수동 편집
3. 취소

선택: _______
```

**수동 편집이 필요한 경우:**
- 컬럼명 변경 (Alembic은 삭제+추가로 인식)
- 데이터 마이그레이션 로직 추가
- 복잡한 제약조건 수정

---

### 2. 마이그레이션 적용 (`/db-migrate apply`)

#### 2.1 적용 전 안전 체크

```bash
🔒 안전 체크 실행 중...

✅ 현재 리비전: ea29476
✅ 적용할 마이그레이션: abc123def456
✅ DB 연결: 정상
✅ 백업 경로: ./backups/db_backup_20260215_1430.sql
```

**자동 백업 수행:**
```bash
$ mysqldump -u user -p db_name > ./backups/db_backup_$(date +%Y%m%d_%H%M%S).sql

백업 완료: ./backups/db_backup_20260215_1430.sql (12.3 MB)
```

#### 2.2 마이그레이션 적용

```bash
마이그레이션을 적용하시겠습니까?
⚠️  이 작업은 DB 스키마를 변경합니다.

[Enter] 계속  |  [n] 취소: _______
```

```bash
$ alembic upgrade head

INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade ea29476 -> abc123def456, Add product table and view_count to question

✅ 마이그레이션 적용 완료!

현재 상태:
- 리비전: abc123def456 (head)
- 테이블: question, answer, user, notification, product
- 적용 시간: 2026-02-15 14:30:45
```

#### 2.3 적용 후 검증

```bash
🔍 스키마 검증 중...

✅ product 테이블 생성 확인
✅ question.view_count 컬럼 확인
✅ 외래키 제약조건 확인

모든 검증 통과!
```

**자동 검증 쿼리:**
```sql
-- 테이블 존재 확인
SHOW TABLES LIKE 'product';

-- 컬럼 확인
DESCRIBE question;

-- 제약조건 확인
SELECT * FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_NAME = 'product';
```

---

### 3. 마이그레이션 롤백 (`/db-migrate rollback`)

#### 3.1 롤백 대상 선택

```bash
📜 마이그레이션 히스토리:

[4] abc123def456 (head) - Add product table and view_count to question (2026-02-15)
[3] ea29476 - Add notification system (2026-02-13)
[2] fb3b5ab - Add answer voter table (2026-02-10)
[1] 47f6291 - Initial tables (2026-02-01)

몇 단계 롤백하시겠습니까?
1. 1단계 (abc123def456 → ea29476)
2. 특정 리비전으로 (리비전 ID 입력)
3. 전체 롤백 (초기화)

선택: _______
```

#### 3.2 롤백 영향 분석

```bash
⚠️  롤백 영향 분석:

삭제될 테이블:
  - product (데이터 손실 위험!)

삭제될 컬럼:
  - question.view_count

복구될 컬럼:
  - question.old_field (데이터는 복구 불가)

정말 롤백하시겠습니까? [yes/no]: _______
```

#### 3.3 롤백 실행

```bash
$ alembic downgrade -1

INFO  [alembic.runtime.migration] Running downgrade abc123def456 -> ea29476

✅ 롤백 완료!

현재 상태: ea29476
백업 파일: ./backups/db_backup_20260215_1430.sql
```

---

### 4. 마이그레이션 히스토리 (`/db-migrate history`)

```bash
📜 마이그레이션 히스토리:

abc123def456 (head) ← 현재 위치
│   Add product table and view_count to question
│   작성자: Claude
│   날짜: 2026-02-15 14:30
│   파일: alembic/versions/abc123def456_add_product_table.py
│
ea29476
│   Add notification system
│   작성자: Claude
│   날짜: 2026-02-13 23:55
│
fb3b5ab
│   Add answer voter table
│   날짜: 2026-02-10 15:20
│
47f6291 (base)
    Initial tables
    날짜: 2026-02-01 10:00
```

---

### 5. 마이그레이션 상태 확인 (`/db-migrate status`)

```bash
📊 마이그레이션 상태:

현재 리비전: abc123def456 (head)
미적용 마이그레이션: 없음

DB 정보:
  - 호스트: localhost:3306
  - 데이터베이스: fastapi_db
  - 테이블 수: 8개
  - 마지막 마이그레이션: 2026-02-15 14:30:45

모델 변경사항: 없음 (동기화됨 ✅)
```

---

## 고급 기능

### 1. 데이터 마이그레이션 추가

모델 스키마뿐만 아니라 데이터 마이그레이션이 필요한 경우:

```python
# 생성된 마이그레이션 파일 수정
def upgrade() -> None:
    # 스키마 변경
    op.add_column('question', sa.Column('view_count', sa.Integer()))

    # 데이터 마이그레이션
    connection = op.get_bind()
    connection.execute(
        text("UPDATE question SET view_count = 0 WHERE view_count IS NULL")
    )

    # 제약조건 추가
    op.alter_column('question', 'view_count', nullable=False)
```

**SKILL이 제안하는 경우:**
- NULL 허용 → NOT NULL 변경 시 기본값 설정
- 컬럼 타입 변경 시 데이터 변환
- 테이블 분리/병합 시 데이터 이동

### 2. 여러 데이터베이스 환경

```bash
어떤 환경에 적용하시겠습니까?
1. development (localhost)
2. staging (staging-db.example.com)
3. production (prod-db.example.com)

선택: _______

⚠️  production 선택 시:
  - 백업 필수 확인
  - 읽기 전용 모드 권장
  - 롤백 계획 확인
```

### 3. 병합 마이그레이션 충돌 해결

```bash
⚠️  마이그레이션 충돌 감지!

브랜치 A: abc123def (Add product table)
브랜치 B: xyz789abc (Add category table)

해결 방법:
1. 자동 병합 (단순 병합 시도)
2. 수동 병합 (파일 직접 편집)
3. 새 마이그레이션 생성

$ alembic merge -m "Merge product and category" abc123def xyz789abc
```

---

## 안전 가이드라인

### ✅ 안전한 마이그레이션
- 새 테이블 추가
- 새 컬럼 추가 (NULL 허용)
- 인덱스 추가/삭제
- 제약조건 추가 (기존 데이터 검증 후)

### ⚠️ 주의 필요
- 컬럼 타입 변경
- NULL → NOT NULL 변경
- 컬럼 기본값 변경
- 외래키 추가 (기존 데이터 정합성 확인)

### 🚨 위험
- 테이블 삭제
- 컬럼 삭제
- 제약조건 삭제 (데이터 정합성 영향)
- 컬럼명 변경 (Alembic은 삭제+추가로 인식)

**위험한 작업 시 추가 확인:**
```bash
⚠️  위험한 작업 감지: 테이블 삭제

영향받는 데이터:
  - product 테이블: 1,234건
  - 외래키 참조: order (234건)

정말 실행하시겠습니까? 'DELETE PRODUCT TABLE' 을 입력하세요:
_______
```

---

## 에러 처리

### 마이그레이션 실패 시

```bash
❌ 마이그레이션 적용 실패!

오류: (1062, "Duplicate entry '1' for key 'PRIMARY'")

복구 작업:
1. 자동 롤백 실행 중...
   $ alembic downgrade -1
   ✅ 롤백 완료

2. 백업에서 복구 가능:
   $ mysql -u user -p db_name < ./backups/db_backup_20260215_1430.sql

3. 마이그레이션 파일 검토 필요:
   alembic/versions/abc123def456_add_product_table.py

문제 원인:
  - product 테이블에 이미 id=1인 레코드 존재
  - 마이그레이션 파일에서 중복 데이터 삽입 시도

해결 방법:
  - 마이그레이션 파일 수정 후 다시 시도
  - 기존 데이터 정리 후 재적용
```

---

## 통합 워크플로우

### 새 도메인 추가 시
```bash
1. /new-domain product
   → models.py 생성

2. /db-migrate create "Add product table"
   → 마이그레이션 파일 생성

3. /db-migrate apply
   → DB에 적용

4. 서버 재시작
   → 새 API 사용 가능
```

### 모델 수정 시
```bash
1. models.py 직접 수정
   → view_count 필드 추가

2. /db-migrate create "Add view_count to question"
   → 자동 감지 및 마이그레이션 생성

3. /db-migrate apply
   → 스키마 업데이트
```

---

## 참고 명령어

### 직접 Alembic 사용 (고급)
```bash
# 현재 리비전 확인
alembic current

# 히스토리 보기
alembic history

# 특정 리비전으로 이동
alembic upgrade abc123def

# 상대적 이동
alembic upgrade +2  # 2단계 앞으로
alembic downgrade -1  # 1단계 뒤로

# 마이그레이션 검증 (적용하지 않음)
alembic upgrade head --sql
```
