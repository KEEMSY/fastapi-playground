# Async Basics: Task 실행 순서

## 해보기

실행하기 전에 `run_demo.py`의 출력 순서를 먼저 종이에 적어보세요.

```sh
python3 study/labs/async-basics/run_demo.py
```

예상과 실제 출력이 다르면, `create_task()`와 `await task` 사이에 이벤트 루프가 언제 제어권을 얻는지 설명해보세요.

## 코드 읽기

- `child()`는 호출만으로 실행되지 않는 코루틴 함수입니다.
- `asyncio.create_task(child())`는 코루틴을 Task로 감싸 현재 이벤트 루프에 실행 대상으로 예약합니다. 이 줄 안에서 `child()`가 즉시 실행되는 것은 아닙니다.
- `main()`은 다음 `await task`에서 Task 완료를 기다립니다. 이때 이벤트 루프는 `child()`를 실행할 수 있습니다.
- `asyncio.sleep(0)`은 실제 대기 시간보다 스케줄러에 제어권을 돌려주는 역할을 보여주기 위해 넣었습니다.
- `asyncio.run(main())`은 이벤트 루프를 만들고 최상위 코루틴을 실행한 뒤 루프를 정리합니다.

출력 순서는 Python asyncio의 일반적인 스케줄링 동작을 설명하는 예제입니다. `await`는 항상 제어권을 양도한다는 뜻이 아니며, 여기서는 아직 완료되지 않은 Task를 기다리므로 `child()` 실행이 진행됩니다.

## 자동 검증

표준 라이브러리 `unittest`만 사용합니다.

```sh
python3 -m unittest study/labs/async-basics/test_run_demo.py -v
```

테스트는 별도 프로세스로 데모를 실행하고 출력 순서를 확인합니다. 프로세스 경계를 두어 `asyncio.run()`이 만드는 이벤트 루프를 테스트 환경의 루프와 공유하지 않습니다.
