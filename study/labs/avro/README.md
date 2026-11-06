# Avro 실습: 직렬화와 스키마 진화

이 랩은 `fastavro`로 Avro binary payload를 만들고, Writer Schema와 Reader Schema가 달라질 때 필드가 어떻게 해석되는지 확인합니다. 기존 `apps/order-flow`는 수정하지 않습니다.

## 이 랩의 스키마 공급 방식

**이 랩은 로컬 `.avsc` 파일을 사용하는 Avro 실습이며, Schema Registry를 사용하지 않습니다.**

| 항목 | 이 랩의 동작 |
|---|---|
| 스키마 위치 | `schemas/` 아래의 `.avsc` 파일 |
| 로드 시점 | `codec.py`가 import될 때 파일을 읽고 `parse_schema()`로 준비 |
| 인코딩 | `encode_v1()`이 `WRITER_V1`을 직접 사용 |
| 디코딩 | `decode()`에 Writer Schema와 Reader Schema를 직접 전달 |
| 레지스트리 / 스키마 ID | 사용하지 않으며 payload에도 ID를 넣지 않음 |

따라서 소비자도 payload를 읽을 Writer Schema를 코드나 다른 설정에서 알고 있어야 합니다. 실제 RabbitMQ 환경에서 Schema Registry를 쓸지는 회사의 레지스트리 제품과 메시지 계약을 확인한 뒤 별도로 구현해야 합니다.

## 환경 준비

랩 디렉터리에서 프로젝트 전용 가상환경을 만들고 의존성을 설치하세요.

```sh
cd study/labs/avro
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

## 코드 흐름 읽기

`src/avro_lab/codec.py`에는 인코딩과 디코딩 코드가 구현되어 있습니다. 먼저 세 스키마를 비교하고 다음을 설명해보세요.

1. `user-signed-up-v1.avsc`가 Writer Schema로 저장한 payload에 필드명이 들어 있을까요?
2. v2가 추가한 `display_name`의 union과 `default`는 각각 무엇을 의미할까요?
3. `user-signed-up-incompatible.avsc`로 옛 payload를 읽으면 왜 실패할까요?

코드를 따라가며 `encode_v1()`이 `WRITER_V1`으로 payload를 쓰는 부분과 `decode()`가 Writer/Reader Schema를 함께 전달하는 부분을 확인하세요.

## 검증

```sh
python -m pytest -q
```

테스트는 다음을 검증합니다.

- v1 이벤트를 binary Avro로 왕복 변환하면 원래 필드가 보존됨
- v1 payload를 v2 Reader로 읽으면 기본값 `display_name=None`이 채워짐
- 기본값 없는 필수 필드를 추가한 Reader는 v1 payload를 읽지 못함

테스트가 통과한 뒤에는 v2 스키마의 새 필드에 기본값을 없애거나 타입을 바꾸어 보고, 어떤 호환성이 깨지는지 설명해보세요.

## 해석할 점

- Avro는 전송 형식과 schema resolution을 제공하고, Pydantic은 애플리케이션 경계에서 Python 데이터 검증과 변환을 담당합니다. 서로 대체 관계가 아닙니다.
- 이 랩은 Schema Registry와 RabbitMQ envelope/header 규약을 다루지 않습니다. 실제 메시지 소비자는 payload의 Writer Schema를 어떻게 찾을지 별도 계약이 필요합니다.
- `schemaless_*`는 schema ID나 파일을 payload에 포함하지 않습니다. 여기서는 Writer Schema를 코드에서 명시적으로 전달합니다.
