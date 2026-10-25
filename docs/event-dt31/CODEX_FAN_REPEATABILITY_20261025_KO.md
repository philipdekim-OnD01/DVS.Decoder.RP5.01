# Codex 실행 지시 — 선풍기 반복성 DVS Event 시험 (2026-10-25)

## 0. 결정 / 작업 기준

- 사용자는 기존 손·손가락 대신 **선풍기의 회전 운동**을 반복 시험 대상으로 준비했다. 동일 조건에서 시간적으로 반복되는 Event 분포를 관측하는 것이 목표다.
- 정식 작업 체크리스트 및 진행 기록: [GitHub Issue #19](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/19). 본 문서보다 Issue 최신 댓글에 새 결과·증거가 있으면 우선 확인한 뒤 기록을 맞춘다.
- **RAW2 A는 현재 단일 운영 RP5의 센서·CSI를 사용 중**. 팬이 준비됐다고 독립 Event 센서/보드/CSI가 확보된 것은 아니다. 이번 지시는 분석 도구·반복 시험 프로토콜·증거 확인부터 시작하며 현재 장비의 실기 Event 모드 전환을 허가하지 않는다.
- 기존 완료: [PR #5](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/5) native Event engine 기반, [PR #13](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/13) 저장된 8MiB 샘플 디코더 A/B, [PR #17](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/17) file-only Event B 앱/960×720 Viewer/native 패키지 E2E. 기존 PR은 Draft 스택이며 자동 병합하지 않는다.
- 완료 기록은 **선풍기의 실제 Event 데이터가 아니다**. 기존 1,557 완성 프레임/1,469,217 SDK 이벤트, `unsynced_groups=830`, 새 launcher17 PASS 수치가 새 선풍기 측정으로 오인되지 않게 표시한다.

## 1. 선풍기 시험 조건 / 기록 양식

팬은 안정적으로 놓고 보호망 안쪽 회전 날개에 접촉하지 않는다. 카메라와 조명의 위치를 고정한다. 팬 속도 변경은 사람이 외부에서만 한다. 기구물·진동·광원 깜빡임을 분리하기 위해 OFF 조건을 필수로 둔다.

| 조건 ID | 타깃 | 비교 목적 | 실제 구동 시 기록 |
| --- | --- | --- | --- |
| FAN_OFF | 전원 OFF, 날개 정지 | 조명 flicker/배경/잡음 기저선 | 위치·조도·환경·시각 |
| FAN_LOW | 팬 저속 선택 | 저속 회전의 이벤트 공간/시간 패턴 | 선택한 팬 속도 단계·시작 안정화 여부 |
| FAN_HIGH | 팬 고속 선택 | 다른 회전 조건의 이벤트 패턴 | 속도 단계·조도·진동 여부 |

참고: OFF는 이벤트0을 보장하지 않는다. LOW/HIGH 이벤트율이 반드시 단조 증가한다고 미리 가정하지 않는다. 시간 bin에서 보인 반복 피크는 팬 회전수의 **후보 proxy**일 뿐이며 플리커/조명·셔터/트리거/alias를 통제하고 독립 tachometer 측정이 없으면 `RPM=UNKNOWN`이다.

각 trial 메타데이터: `trial_id, condition, operator_confirmed_fan_setting, clock_time, capture_host, sensor/receiver_identity, camera_to_fan_distance_measured_or_unknown, camera_view_angle, illumination_type/flicker_unknown, exposure_mode_if_known, ROI_polygon_or_box, recording_duration_observed, input_hash, data_origin, decoding_revision, gating_class`.

개발 단계에서는 이 trial 구조와 저장 파일 비교기만 만들고, 실제 팬 Event 데이터가 없을 경우 trial 측정값을 만들지 않는다. 나중에 안전한 전용 rig 승인이 생긴 경우 처음에는 동일한 시간 구간을 비교하도록 제안하며, 샘플링 횟수와 속도 설정은 실제 환경의 승인된 실험서에 고정한다. 과거 10초×3/총 다운타임15분 제한은 기존 운영 A를 중단하는 단일 장비 검증에만 유효한 **상한선이지 현재 실행 승인이나 필수 팬 녹화 길이가 아니다**.

## 2. 오프라인 계측 필드 / 판단 경계

동일한 입력 범위에서 계산:
- `source_sha256, source_type, parser_git_sha, decoder_revision, frame_count_completed, eof_incomplete_count`.
- `time_start_us/time_end_us, sensor_time_monotonic, frame_period_us_distribution`. timestamp wrap/epoch 처리 검증 없이 시간을 절대 센서 정확도라고 부르지 않는다.
- `event_total_completed_frames, event_on, event_off, ROI_event_count, ROI_area, ROI_events_per_second, spatial_occupancy, ROI_centroid/heatmap_aggregates`. SDK Stats 총 event와 완성 프레임 포함 event는 별도 범위.
- `time_bin_ms, count_by_bin, periodicity_candidate_hz, prominence_or_signal_quality, alias_and_flicker_caveat`. FFT/ACF 계산기의 검증용으로만 알려진 펄스 합성 신호 사용. 실제 fan RPM은 외부 계측 없이는 미판정.
- `unknown, invalid, unsynced_groups, sensor_frame_gaps, eof_partial_bytes, input_chunk_count, queue_drops, queue_high_water`. 큐0 drop은 CSI 물리 손실0을 뜻하지 않는다.
- `CSI_FS/FE/CRC/ECC, original_V4L2_sequence/bytesused, sensor_wire_WC/DT, physical_xy_accuracy`는 원본 보존된 진짜 수신 계측이 없으면 `NOT_OBSERVED`/UNKNOWN.

동일 팬 조건 반복 trial이 있을 때만 median/range/CV(표본 부족 시 NA)를 구하고 condition 간 비교를 수행한다. 데이터 없을 때는 합성 계산기 PASS만 주장한다. 원본 데이터가 없는데 팬 영상을 생성하거나 임의 픽셀로 “관측” 보고하지 않는다.

## 3. F0–F5 실행 계획

F0. **독립성·출처 검사.** `git fetch/status`, main AGENTS/Issue #19 latest, PR #17 head 및 그 의존 PR, Issue #7, PROGRESS 실제 확인. 새 브랜치는 실제 Event B 패키지 코드가 있는 PR #17 HEAD에서 출발해 separate Draft PR. 운영 중인 센서/CSI와 분리된 별도 B 실기 장비가 있는지 **읽기 전용/사용자제공 자료**로 검증. 확인 안 되면 `SHARED_OR_UNPROVEN`, live 불가.

F1. **선풍기 프로토콜 문서.** OFF/LOW/HIGH·안정화·고정 위치·조명·ROI·메타데이터·실패 기준과 반복 비교 표준화. 팬 속도(RPM) 측정기 미제공 시 명시적 UNKNOWN. 기존 손가락 fixture 요구 금지.

F2. **오프라인 지표 분석기.** PR #17 completed `frames.bin`, `metrics.json`, `status.json` 및 승인 Event 저장 입력에 한하여 읽기 전용. EventGroup/SensorFrame ABI 16B/6B 및 경계 검증. 새 임의 RAW2/Event byte 혼합 입력 금지. 시작/끝 미완성 출력과 통계범위를 분리. 데이터 시계열 bin/ROI 공간분포/ON-OFF/periodicity 후보를 적절한 검증값/불확실성과 함께 출력.

F3. **실기 준비의 판정까지만.** 실제 팬 센서 데이터가 없으면 `NOT AVAILABLE`. 독립 테스트 장비가 확인돼도 이 Issue만으로 I2C/DT/module/service/capture 실행 금지. 전용 장비에 필요한 센서 TX Event DT `0x31`, receiver DT descriptor, Word Count, frame/buffer geometry, wire FS/FE, V4L2 path, event file write, decode/Viewer 연결과 shutdown/health 요구를 설계하고 `GO/NO-GO` 사유를 보고한다. 동일 A 센서이면 Issue #7의 복구/GO gate 전까지 무조건 STOP.

F4. **최소 신규 회귀·파일 리플레이.** 오프라인 계산기 정확성(인공 OFF count0, ON/OFF ratio, known pulse frequency, ROI/boundary, malformed/truncated frame, timestamp wrap, empty window, alias warning)을 synthetic fixture로만. 실제 승인된 팬 Event 입력이 발견될 때만 file-only replay/측정을 수행한다. 새로 실기 촬영하거나 기존 완료 decoder/native/launcher test 전체를 이유 없이 다시 실행하지 않는다.

F5. **증거와 다음 결정.** 해당 작업 브랜치에서 실행명령/host/input SHA/tests/시간/한계와 체크포인트를 `PROGRESS.md`에 append→commit/push. 각 F 완료시 Issue #19 최신 댓글로 `DONE/EVIDENCE/TEST/BLOCKER/NEXT` 기록. 공개 가능한 코드/합성fixture/집계·문서만 별도 Draft PR로 제출. 실제 팬 데이터 파일/frames/이미지/비공개 SDK/setfile을 공개 Git에 넣지 않는다.

## 4. 안전 차단

`RAW2_A=UNTOUCHED`, `PHASE_C=HARD_BLOCKED`, Event `--device=PHASE_C_BLOCKED` 고정. 운영 Pi에서 service stop/restart, I2C read/write, `/dev/video*` open/STREAMON, 모듈·DT·media 변경, sensor setfile 적용, reboot, firstboot/legacy rollback/watchdog 호출 없음. 별도 프로그램·폴더는 독립 물리 장비가 아니라는 점을 반복 확인.

## 5. 완료 조건 및 마지막 보고

파일/mock 오프라인 분석 도구·합성 회귀 및 선풍기 측정 계획 완료가 본 지시의 Done. 실제 Event `DT=0x31` 센서 신호를 받는 실기는 별도 하드웨어 출처/승인/게이트 충족 이후 새 작업으로 넘길 것.

```text
FAN: available; OFF/LOW/HIGH plan recorded
RIG: independent confirmed | shared/unproven
INPUT: real fan Event file + SHA | not available
OFFLINE ANALYSIS: actual new tests and evidence
FAN_SENSOR_LIVE: NOT TESTED / separately authorized
RAW2 A: UNTOUCHED
PHASE C: HARD BLOCKED; --device=PHASE_C_BLOCKED
RESULT: commit / draft PR / blocker / exactly one NEXT
```
