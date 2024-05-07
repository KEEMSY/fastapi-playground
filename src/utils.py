import os
import logging.config
from datetime import datetime

from config import LOG_FILE_PATH, LOG_FILE_EXT
from src.domains.async_example.constants import Environment

"""
[ 로깅 표준 방식 ]
logging.ini 를 사용하는 방법
- logging.ini 파일을 만들어서 설정을 저장한다.
- logging.config.fileConfig() 함수를 사용해서 설정을 읽어온다.
  - logging.config.fileConfig() 함수는 logging.config 모듈에 있는 함수로, 설정 파일을 읽어서 로깅을 설정한다.

다만 아직 개선해야 하는 사항이 존재함(24.05.06)
- 로깅 파일을 저장해야 함
- 디렉토리, 날짜, 포매팅을 커스텀하여 사용할 수 없음(혹은 내가 아직 해당 방법을 모름)
- 개발 환경 별(Prod, Dev, Test)에 따라 로깅 레벨을 다르게 설정할 수 있도록 개선 필요(아직 개발 환경 별 환경 세팅이 이뤄지지 않았음, 먼저 개발 환경을 구분할 수 있는 방법이 필요)
- 로깅 파일을 일정 기간마다 자동으로 삭제하도록 개선 필요
"""


def setup_logging():
    # Determine the base directory relative to the current script
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logging_config_path = os.path.join(base_dir, 'logging.ini')
    logging.config.fileConfig(logging_config_path, disable_existing_loggers=False)


setup_logging()
logger = logging.getLogger('uvicorn')

"""
[ 직접 로깅 모듈을 커스텀하여 개발하는 방식]
로깅 클래스 와 함수를 정의하여, 직접 원하는 입맛대로 커스텀하여 로깅한다.
- 디렉토리, 날짜, 포매팅을 커스텀하여 사용한다.
  - 디렉토리: logs/설정한 파일/연도_월/연도_월_일.log

다만 아직 개선해야하는 사항이 존재함(24.05.06)
- 개발환경별(Prod, Dev, Test)에 따라 로깅 레벨을 다르게 설정할 수 있도록 개선 필요(아직 개발 환경 별 환경 세팅이 이뤄지지 않았음, 먼저 개발환경을 구분할 수 있는 방법이 필요)
- 로깅 포매팅을 더 다양하게 설정하는 것일 필요한지, 아니면 지금 형태로 충분한지 판단 후, 개선 필요
- 로깅 파일을 일정 기간마다 자동으로 삭제하도록 개선 필요
"""


class SingletonLogging(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonLogging, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Logging(object, metaclass=SingletonLogging):
    _format_basic = '[%(levelname)s] [%(asctime)s] (%(name)s) %(message)s'
    _format_thread = '[%(levelname)s] [%(asctime)s] (%(name)s) (Id : %(thread)d, Name : %(threadName)s) Msg : %(' \
                     'message)s '

    _loggers = {}

    def get_logger(self, name: str, path: str = None, isThread: bool = False):
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger

            # 개발 환경 별 로깅 레벨을 설정하도록 개선 필요: 개발 환경을 구분하는 작업이 선행 되어야 함.
            # logger.setLevel(logging.DEBUG if Environment.is_debug or Environment.is_testing else logging.INFO)

            formatter = logging.Formatter(self._format_thread if isThread else self._format_basic)
            file_path = self.get_log_path(path if path else name)
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            self._loggers[name].addHandler(file_handler)

        return self._loggers[name]

    def get_log_path(self, path: str) -> str:
        year = str(datetime.today().year)
        month = datetime.today().strftime('%m')
        day = datetime.today().strftime('%d')

        rep_path = path.replace('/', '')
        rep_path = rep_path.replace('\'', '')

        # LOG_FILE_PATH / path /
        result = LOG_FILE_PATH + rep_path + os.path.sep
        self.make_path(result)

        # LOG_FILE_PATH / path / 2024_05
        result = result + year + "_" + month + os.path.sep
        self.make_path(result)

        # LOG_FILE_PATH / path / 2024_05 / 2024_05_06.log
        result = result + year + "_" + month + "_" + day + LOG_FILE_EXT
        return result

    def make_path(self, path: str, mode=0o755):
        if not os.path.exists(path):
            os.mkdir(path)
            os.chmod(path=path, mode=mode)
