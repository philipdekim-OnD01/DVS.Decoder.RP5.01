# Codex 독립 작업 지시 — Raspberry Pi Issue #1 먼저 해결 (2026-10-25)

**이 문서가 이번 사용자의 Codex 작업 우선순위다.** 기존 Event PR #5와 Blue-Green 계획을 버리는 것이 아니라 **새로운 hardware 실험 전에 RAW2 입력·센서 프레임의 증거 공백을 우선 해결**하는 작업을 분리한다.

## 0. 반드시 먼저 읽을 것 (읽기 순서)

1. [Pi Issue #1 본문 + **최신 댓글의 마지막 감사**](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1), 특히 [전체 RAW 감사](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6300566219), [센서 경계 감사](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6300872307).
2. [955/960 보고서·검증 스크립트·JSON commit `2c3b2f1`](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/commit/2c3b2f124d8f3ad3fb049bb207147c32adf60f3f), [Wrap21 v4](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/tree/wrap21-v4-20261020/experiments/wrap21_v4), `raw2_producer_wrap21.cpp`, `boundary_live_shadow.hpp`, 해당 커널 RP1 `cfe/csi2` 소스.
3. [Pi×Jetson 최종 교차 검토](./CROSS_PLATFORM_REVIEW_20261025_KO.md); [AGENTS](../../AGENTS.md), [Blue-Green 설계](./BLUE_GREEN_SWITCH_PLAN_KO.md), [RUNBOOK](./RP5_EVENT_RUNBOOK_KO.md), [현재 PR #5 작업 기록](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/blob/codex/rp5-event-phases-20261021/docs/event-dt31/PROGRESS.md).
4. 접근이 허용된 경우에만 **비공개** [Jetson 2026-10-25 기술자료](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/tree/main/docs/diagnostics/2026-10-25/)의 README/01/02/03/05와 공개 가능한 요지를 참고. Jetson의 [`dvs_gaps.py`](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/blob/main/e850/dvs-tools/dvs_gaps.py) 분석 아이디어와 [`check_session.py`](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/blob/main/jetson/dvs-recorder/check_session.py) 관측 지표를 **참고만** 한다. 비공개 repository에 접근할 수 없으면 NOT ACCESSIBLE로 기록하고, 비밀 소스 복제/권한 우회는 하지 않는다.
5. 주의: **Jetson 저장소의 Issue #1은 가정 기반 성능 시뮬레이션**이고 이 작업의 목표가 아니다. **Pi 저장소 Issue #1**이 우선.

## 1. 첫 작업 — Pi RAW2 971/976의 첫 잘못된 경계 위치 규명

**문제:** 호스트 레코드는 976×180B, 후보 마커 간격 971×180B; 200/200 Wrap21 호스트 분류 복구. 5블록/900B 차이는 **관측됨**, 센서 물리 5컬럼 손실은 **입증되지 않음**. 256개 후보의 Fig46 인접 고정필드 불일치와 +12 frame counter 후보 실패가 마지막 확정 감사. 이전 같은 12개 후보를 다시 훑는 것은 금지.

### 순서 (오프라인/읽기 전용만)
1. [Issue #1 마지막 감사](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6300872307)를 기준으로 **2026-10-13 동일 녹화**의 기존 보존 자료에서 `CSI-2 on-wire DT/WC/FS/FE`, 센서 embedded 실제 카운터 또는 검증된 Fig46 필드 위치 매핑이 있는지 **한정된 증거 출처 검사 한 번** 수행한다. 서로 다른 날짜/모드/보드 자료는 같은 촬영 증거로 합치지 않는다. 우선 artifact index/문서/코드만 읽고 대용량 RAW 전체 재스캔 금지.
2. 이미 증명된 `971`-marker 주기와 `Wrap21` 호스트 오분류는 보존. 같은 짧은 RAW 16레코드 및 기존 200건 산술만 활용해 `host record offset`, `candidate marker offset`, `candidate frame span`, `decode_raw2 first_pixel`, 실제 선택 960 source chunks 및 **embedded-flagged 5 chunks overlap**을 별도 컬럼으로 비교한다. 실제 진짜 센서 경계가 인증되지 않았다면 `sensor_frame=UNKNOWN`.
3. Fig46 fixed field와 candidate counter의 검증 실패를 **음성 결과**로 남긴다. 헤더 mapping 후보를 무제한 생성하지 않는다. 동일 촬영의 wire/문서 출처가 존재하고 식별이 검증될 때만 최소 재현 오프라인 검사를 설계한다.
4. 헤더 identity를 검증할 근거가 없다면 **UNKNOWN / STOP**으로 이슈에 종료 판단 보고. 물리 5컬럼 손실 또는 원인 레이어가 증명된 경우에만 **최초 오류 바이트/offset/코드 위치**, 비교 전후 한 샘플, 표적 회귀시험을 넣어 별도 소규모 PR로 제안한다. **패치 먼저 금지**.

### 필수 결과물
- 공개 가능 **짧은 `FACT / EVIDENCE / CONFLICT / UNKNOWN / DECISION` 표**와 해당 GitHub artifact/file/line/sha 링크.
- `first_bad_layer = sensor_wire | RP1_CFE_DMA | host_record_builder | marker_classifier | 960_chunk_reconstruction | UNKNOWN`; 증거 없으면 **UNKNOWN**.
- 재현 가능한 작은 오프라인 테스트 또는 명확한 NO-EVIDENCE 결론. 데이터가 부족한데 파일을 더 분석한 것처럼 성공 보고하지 않는다.
- [Pi Issue #1](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1)에 **아래 다섯 줄** 댓글:
  ```text
  FACT: [971/976 확인 사항; 후보와 센서 경계 구분]
  LOCATION: [첫 오류 레이어 / RAW offset / 소스 위치 또는 UNKNOWN]
  EVIDENCE: [sha / 작게 한정한 실측 / GitHub 링크]
  CHANGE/TEST: [수정 여부 / 수행한 실제 테스트만 PASS/FAIL/NOT TESTED]
  NEXT: [다음 단일 분별 검사 또는 UNKNOWN STOP]
  ```

**완료 기준:** 한정된 기존 증거로 실측 원인을 최초 레이어까지 구체적으로 입증 **또는** 확인 가능한 수신 wire/header 근거가 없음을 정직하게 명시하고 UNKNOWN으로 STOP. 같은 자료를 반복 계산하는 것은 완료로 세지 않는다.

## 2. 두 번째 작업 — Jetson 검증 방식을 Pi Event 오프라인 자료에 적용

Pi Issue #1 확인·정리 후에만 다음 순서로 진행한다.

1. PR #5 기존 `8MiB` 이벤트 샘플 SHA 및 native `17`건 PASS, `1,557` 완성 출력 프레임/`1,469,217` 이벤트/`830` unsynced 그룹 결과를 보존. 입력 분할 해시 불변성을 새로 다시 증명한 척하지 않는다.
2. **비공개 작업 공간**에서만 동일 저장 Event bytes를 구형 reference-b3/dual과 새 C++ decoder에 공급하고, `COLUMN/Group1/Group2/B2/B3/ON/OFF/센서 Timestamp`, byte 오프셋별 패킷·프레임 및 물리 좌표 신뢰도를 비교한다. 비공개 SDK/원본/대량 RAW는 public git commit 금지.
3. Jetson `dvs_gaps.py`의 **4B word 분류 및 fixed-boundary 연관 검사 방법**을 포맷이 호환되는 경우에만 안전한 합성 데이터/오프라인 sample에 적용. `unsynced_groups`가 V4L2 buffer, CSI frame, packet 손상 등 어디에 집중되는지 *한정해* 확인하고 실제 누락 프레임으로 단정 금지. RAW2 파일에 Event 파서를 적용하지 않는다.
4. Pi 수신·디코딩 파이프라인 계측 항목(송수신 DT/WC, host seq와 **검증된** sensor counter 분리, DQBUF→QBUF p99, queue/drop, CRC/ECC)을 **mock/file 모드 설계**에 반영. Jetson USERPTR나 센서 I2C 주소·명령을 Pi에 복제 금지.
5. 작은 코드/테스트 변경이 필요하면 별도 브랜치와 증거를 남기고, PR #5의 코드·Mock 성공 결과를 유지한다. 추측성 좌표 +5/+8/+128 보정 금지.

## 3. 병행 개발 및 실행 경계

- **RAW2 A(원본) 유지**, **Event B(새 프로그램) 독립 개발**, **최소 fail-closed A↔B Switcher는 현재 simulated-only**. 사용자 설계 결정을 훼손하지 않는다.
- **Phase C HARD BLOCKED**. `--device` 차단 유지. 새 CSI `0x31` 실기 수신, RAW2 stop/restart, 모듈/DT/receiver/media 변경, I2C read/write, 재부팅 및 `raw2_production_rollback.sh` 실행/예약 금지. 별도 검증된 승인 절차 전에는 기기의 live 상태를 건드리지 않는다.
- 파괴적 firstboot timer 및 기존 `raw2_production_start.sh` 재시작 위험은 여전히 유효. Jetson의 sensor-tool과 startup behavior가 Pi에 그대로 통한다는 전제 금지.
- 작업 위치: **Issue #1 RAW2 진단용 새 별도 분석 브랜치/작은 PR**을 우선 사용하고, **Event PR #5**는 완료된 실험·증거를 보존한다. PR #5에 교차 분석 결과를 기록하되 Issue #1 작업 때문에 Event code를 재작성하지 않는다.
- 실제 수행 명령·새로 생성한 evidence와 기존 evidence를 구별하고, 불필요한 재실험을 피한다. 기밀 Jetson/NRV 이메일·환자 RAW·SDK·setfile·센서 원본 문서는 공개 저장소에 절대 복사하지 않는다.

## 4. Codex 종료 보고 형식

```text
PI_ISSUE_1: FACT / LOCATION / EVIDENCE / UNKNOWN / NEXT
JETSON_METHOD_REUSED: named source + applicable algorithm; no unverified code transplant
TESTS_ACTUALLY_EXECUTED: commands + host + PASS/FAIL, or NOT TESTED
FILES_AND_COMMIT: branch + commit + Issue #1 comment + optional PR
RAW2_PRODUCTION: UNTOUCHED; NO LIVE CAPTURE
PHASE_C: HARD BLOCKED
```

이 문서는 새 지시지만 **Codex 실행 자체를 자동으로 시작하지 않는다**. Codex가 이 파일/Issue #1을 fetch해 작업을 진행해야 한다.
