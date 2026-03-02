# 보안 규칙

이 파일은 매 세션 자동으로 로드됩니다. 아래 보안 규칙을 반드시 준수하세요.

## 환경 변수 및 시크릿

- **.env 파일 내용 절대 출력 금지**: 대화 중 `.env` 파일 내용을 그대로 보여주거나 커밋하지 말 것
- **시크릿 하드코딩 금지**: 아래 항목들을 코드에 직접 작성하지 말 것
  - `SECRET_KEY`, `API_KEY`, `ACCESS_TOKEN_SECRET`
  - DB 비밀번호, 외부 서비스 인증 정보
  - 모두 환경변수로 읽어야 함: `os.getenv("SECRET_KEY")`

## SQL 인젝션 방지

- **Raw SQL에 사용자 입력 직접 삽입 금지**
  - 잘못된 예: `f"SELECT * FROM users WHERE id = {user_id}"`
  - 올바른 예: SQLAlchemy ORM 쿼리 또는 파라미터 바인딩 사용
  - `text("SELECT * FROM users WHERE id = :id").bindparams(id=user_id)`

## 에러 응답

- **내부 예외 정보 노출 금지**
  - 잘못된 예: `raise HTTPException(detail=str(e))`
  - 올바른 예: 사용자 친화적 메시지 + 내부 로깅으로 분리
  ```python
  # 잘못된 방법
  except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))  # 내부 정보 노출!

  # 올바른 방법
  except Exception as e:
      logger.error(f"Internal error: {e}")
      raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다")
  ```

## 로깅

- **비밀번호, 토큰 로그 출력 금지**
  - `logger.info(f"User password: {password}")` 절대 금지
  - 민감 정보는 로그에서 마스킹: `****`

## 인증/인가

- **인증 누락 방지**: `create`, `update`, `delete`, `vote` 엔드포인트에 반드시 인증 의존성 추가
- **권한 검증**: 리소스 소유자 확인 필수 (내 데이터만 수정 가능)
  ```python
  # 반드시 확인
  if question.user_id != current_user.id:
      raise HTTPException(status_code=403, detail="권한이 없습니다")
  ```

## CORS

- **와일드카드 허용 금지** (프로덕션 환경)
  - 잘못된 예: `allow_origins=["*"]` (개발 환경 전용)
  - 올바른 예: `allow_origins=[settings.FRONTEND_URL]`

## 파일 업로드 (해당 시)

- 허용 파일 타입 화이트리스트 방식으로 검증
- 파일 크기 제한 설정
- 업로드 경로에 사용자 입력값 그대로 사용 금지 (경로 순회 공격 방지)
