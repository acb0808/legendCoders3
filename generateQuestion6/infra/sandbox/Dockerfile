# 격리 샌드박스 런타임 이미지 (T03.2)
# - 비특권 사용자, 읽기 전용 루트, 실행별 임시 쓰기 공간
# - 네트워크·DNS·동적 패키지 설치·호스트 mount 차단 (docker run 옵션으로 강제)
# - 입력 파일 하나와 결과 JSON 하나만 교환하는 runner

FROM python:3.12-slim

ARG SYMPY_VERSION=1.13.3
ARG MPMPATH_VERSION=1.3.0

# SymPy 와 승인된 수학 패키지만 고정 버전으로 설치
RUN python -m pip install --no-cache-dir \
        "sympy==${SYMPY_VERSION}" \
        "mpmath==${MPMPATH_VERSION}"

# 비특권 사용자 생성
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin sandbox

WORKDIR /sandbox
COPY runner.py /sandbox/runner.py

RUN mkdir -p /in /out /work && chown -R sandbox:sandbox /in /out /work

# 호스트 환경변수는 기본적으로 상속되지 않도록 이미지 전역에서 제거
ENV HOME=/home/sandbox
ENV PATH=/usr/local/bin:/usr/bin:/bin

USER sandbox

ENTRYPOINT ["python", "/sandbox/runner.py"]
