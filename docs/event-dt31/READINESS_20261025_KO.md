# 2026-10-25 재개 점검 — Phase C NO-GO

GitHub fetch 후 Issue #7 본문/댓글 및 PR #5 discussion을 재확인했다. 새로운 실기 지침은 없으며 기존 HARD STOP을 유지한다. 작업 브랜치는 `codex/rp5-event-phases-20261021`, 시작 HEAD `3a0a456`이다.

## 읽기 전용 실측

`ssh -o BatchMode=yes -o ConnectTimeout=10 philip@192.168.0.177 python3 - < experiments/event-readiness/read_inventory.py`를 실행했다. 증거는 `experiments/event-readiness/evidence/rp5-readonly-20261025.json`이다.

- 관측 시각 Pi 보고 2026-10-25 05:42:02 KST. kernel 6.12.47+rpt-rpi-2712. RAW2 active/enabled, PID683775, NRestarts0.
- 2초 간격 sequence425660338→425662660. 마지막 capture buffers/s1128.176, raw bytes/s198198044.941, web57.958fps, HDMI59.956fps. 보고된 dequeue/buffer/sequence-gap 오류 각각0. 영상 자체와 CSI CRC/ECC는 이번에 검증하지 않았다.
- pending marker absent, firstboot timer/service not-found/inactive, camera-root-watchdog timer disabled/inactive.
- 10월22일 최종 inventory와 공통 검사 파일의 전체 metadata/hash, module parameters 및 media graph 요약이 동일하다. 서비스 재시작/모드 복구 시험의 증거는 아니다.
- I2C 유틸리티는 실행하지 않았다. 저장 레지스터12행은 현재 센서 readback이 아니다. 비특권 live FDT 읽기는 PermissionError로 기록했으며 이번에 승격해서 재수집하지 않았다.

## watchdog 입력과 실행 재사용 방어

`watchdog_worker.py`의 JSON 요청을 엄격하게 검사한다. schema는 정수1, run은24자리 lowercase hex, token digest는64자리 hex, timeout은 유한한 숫자0.2~10초만 허용한다. bool/문자열/null/NaN/Infinity/잘못된 action/추가 key를 거부한다. exclusive lock 획득 후 이전 ready/result가 있으면 시작을 거부하여 이전 결과를 덮어쓰지 않는다.

시작 직전 도착한 cancel은 기존 프로토콜에 맞게 처리한다. 최초 구현은 cancel 파일도 재사용으로 거부하여 기존 회귀시험이 실패했다. 이 조건을 제거한 뒤 전체33건을 재검증했다. 실패한 버전은 Pi로 전송하거나 성공으로 기록하지 않았다. Pi 기존33건의 첫 실행은 정적 검사에 필요한 sibling restore mock 파일을 배치하지 않아 FileNotFoundError로 종료했다. `/tmp/dvs-watchdog-request-20261025/readiness/`와 sibling `event-restore/` 구조로 보완한 뒤 동일 suite를 재실행했다.

- `python3 experiments/event-readiness/test_watchdog_request.py --results ...`: 로컬/Pi 각각22 PASS. 19개 형식 거부, ready/result 재사용 거부2, 정상 NOOP expiry1. 이전 ready/result 파일 보존과 신규 결과 미생성을 검사한다.
- `python3 experiments/event-readiness/test_readiness.py --results ...`: 로컬/Pi 각각33 PASS. 변경된 worker의 기존 취소/잘못된 token/lock/종료 처리 포함. 변경되지 않은 decoder/Viewer suite는 반복하지 않았다.
- worker SHA256 `64c7c6944e4d63348b62a3f129a7a54645bcbbedb47148636861bdce8df5567c`가 로컬/Pi 신규22건 결과에서 일치한다.
- Pi 작업 경로 `/tmp/dvs-watchdog-request-20261025/`. 신규 시험은 일반 사용자 프로세스/temp 파일만 사용한다. 이번 변경 버전의 systemd/SSH 생존 시험은 **NOT TESTED**. 10월22일의 systemd5건/SSH 증거는 이전 source pin에만 해당하며 보존한다. ASan 적용 대상인 C++ 변경은 없다.

## 판정 및 다음 단계

**Phase C HARD BLOCKED / NO-GO, production_ready=false.** 운영 서비스 stop/restart, I2C 접근, sensor/module/DT/media 변경, 재부팅 및 live Event 수신0회. 기존 rollback/start/validate/installer 및 legacy watchdog은 실행하지 않았다.

아직 없는 것은 실제 current-RAW2 복구 backend, 완전한 private immutable baseline, 위험 평가된 현재 센서 readback/정상 영상/CSI baseline, 실제 receiver re-probe/get_frame_desc DT 및 Event geometry 검증, production startup과 destructive timer race의 안전한 통합, 실제 복구 health와 watchdog 취소 연동이다. 이를 mock PASS로 대체할 수 없다.

다음 안전 작업은 별도 비운영 환경에서 복구 backend와 건강 검증/취소 프로토콜을 통합하는 설계 및 실패 주입이다. 운영 장비에서는 현재 차단 조건이 충족되기 전까지 시험하지 않는다. 실제 DT0x31 수신과 RAW2 복구 성공은 모두 **NOT TESTED**다.
