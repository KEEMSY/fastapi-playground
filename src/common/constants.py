from enum import Enum

class APIVersion(str, Enum):
    """
    API 버전 관리를 위한 열거형 클래스
    
    버전 업그레이드가 필요한 경우:
    1. Breaking Changes가 발생할 때
       - 응답 구조가 완전히 변경되는 경우
       - 필수 파라미터가 추가되는 경우
       - 기존 필드의 타입이 변경되는 경우
    
    2. 하위 호환성이 깨질 때
       - 기존 필드가 제거되는 경우
       - 기존 엔드포인트의 동작 방식이 크게 변경되는 경우
    
    3. 새로운 비즈니스 로직 도입 시
       - 기존 로직을 유지하면서 새로운 기능을 추가해야 할 때
       - A/B 테스트가 필요한 경우
    
    버전별 사용 예시:
    - V1: 초기 안정화 버전
         - 기본적인 CRUD 작업
         - 단순한 응답 구조
    
    - V2: 기능 개선 버전
         - 향상된 응답 구조 (메타데이터 추가)
         - 새로운 필터링 옵션
         - 최적화된 쿼리 처리
    
    - V3: 차세대 버전
         - 완전히 새로운 아키텍처
         - 새로운 보안 정책
         - 고급 기능 지원
    
    사용 시 주의사항:
    1. 버전 변경 시 사전 공지(및 협의) 필요
    2. 버전 별 문서화 필수
    """
    V1 = "v1"  # 초기 안정화 버전
    V2 = "v2"  # 기능 개선 버전
    V3 = "v3"  # 차세대 버전 