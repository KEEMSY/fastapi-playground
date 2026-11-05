# Avro 실습: 직렬화와 스키마 진화

이 랩은 `fastavro`로 Avro binary payload를 만들고, Writer Schema와 Reader Schema가 달라질 때 필드가 어떻게 해석되는지 직접 구현하고 확인하는 실습입니다. 기존 `apps/order-flow`는 수정하지 않습니다.

## 환경 준비

랩 디렉터리에서 프로젝트 전용 가상환경을 만들고 의존성을 설치하세요.

```sh
cd study/labs/avro
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

## 직접 구현할 작업

먼저 세 스키마를 비교하고 다음을 설명해보세요.

1. `user-signed-up-v1.avsc`가 Writer Schema로 저장한 payload에 필드명이 들어 있을까요?
2. v2가 추가한 `display_name`의 union과 `default`는 각각 무엇을 의미할까요?
3. `user-signed-up-incompatible.avsc`로 옛 payload를 읽으면 왜 실패할까요?

그다음 `src/avro_lab/codec.py`의 두 TODO를 구현하세요.

- `encode_v1`: `BytesIO`와 `schemaless_writer`를 사용해 v1 스키마로 dict를 Avro binary bytes로 인코딩합니다.
- `decode`: Writer Schema는 항상 v1이고, Reader Schema는 인자로 받은 스키마를 사용합니다. Avro binary에는 보통 Writer Schema가 함께 들어 있지 않으므로 decoder가 이를 알아야 합니다.

## 검증

```sh
python -m pytest -q
```

현재 테스트 3개는 `codec.py`의 두 TODO가 구현되기 전까지 `NotImplementedError`로 실패하는 것이 정상입니다. 구현 후에는 다음을 검증합니다.

- v1 이벤트를 binary Avro로 왕복 변환하면 원래 필드가 보존됨
- v1 payload를 v2 Reader로 읽으면 기본값 `display_name=None`이 채워짐
- 기본값 없는 필수 필드를 추가한 Reader는 v1 payload를 읽지 못함

테스트가 통과한 뒤에는 v2 스키마의 새 필드에 기본값을 없애거나 타입을 바꾸어 보고, 어떤 호환성이 깨지는지 설명해보세요.

## 해석할 점

- Avro는 전송 형식과 schema resolution을 제공하고, Pydantic은 애플리케이션 경계에서 Python 데이터 검증과 변환을 담당합니다. 서로 대체 관계가 아닙니다.
- 이 랩은 Schema Registry와 RabbitMQ envelope/header 규약을 다루지 않습니다. 실제 메시지 소비자는 payload의 Writer Schema를 어떻게 찾을지 별도 계약이 필요합니다.
- `schemaless_*`는 schema ID나 파일을 payload에 포함하지 않습니다. 여기서는 Writer Schema를 코드에서 명시적으로 전달합니다.
