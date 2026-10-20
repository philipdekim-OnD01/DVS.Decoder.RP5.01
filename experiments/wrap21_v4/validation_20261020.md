# Wrap21 v4 검증 보고서 — 2026-10-20

## 구분
- **기준 운영본:** `v2026.10.18-final` (현재 Raspberry Pi에서 운영 중이며 변경 없음)
- **이번 코드:** `experiments/wrap21_v4/raw2_producer_wrap21.cpp` + `raw2_wrap21.hpp`
- **상태:** 10초 오프라인 재생 및 20초 실시간 카메라 A/B **통과**. 장시간 안정화 시험 및 운영 반영 **미실시**.
- **H/W 노이즈:** 가능성을 인정하되 이번 SW 판정과 분리. 향후 하드웨어 안정화 후 평가.

## 원인 및 수정
`find_embedded_run()`이 976×180B 호스트 버퍼의 양 끝을 **원형**으로 이어 검사하여 다른 Embedded Marker 조각을 하나의 길이 21블록으로 오인하는 경우가 확인됐습니다. 기존 코드는 이때 `alignment_errors`만 올리고 `decode_raw2()` 호출을 생략합니다.

v4는 기존 16블록 정상 처리는 바꾸지 않으며, **버퍼 맨 앞/뒤의 Marker 조각만 존재하고 각 1~16블록, 합계가 정확히 21블록**인 경우에만 `recover_first_pixel()`로 첫 픽셀 위치를 교정합니다. 다른 비정상 Marker는 기존처럼 거부합니다. 변경은 `DVS_RAW2_WRAP21_RESCUE=1` 환경변수로만 활성화됩니다.

## 오프라인 검증 (저장 10초 RAW)
| 항목 | 결과 |
|---|---:|
| 입력 V4L2 레코드 | 16,140 |
| 기존 거부 | 200 (1.23916%) |
| Wrap21 복구 | **200/200** |
| 복구 후 해당 샘플의 남은 거부 | **0** |
| 기존 정상 레코드 판정 변경 | **0/15,940** |
| V4L2 시퀀스 누락 | 0 |
| Synthetic tests | 13 PASS |

실행 출력: `records=16140 legacy_rejected=200 wrap21_recovered=200 remaining_rejected=0 original_accepted_unchanged=15940 changed_valid=0 seq_gaps=0`

## 실시간 A/B 검증 — Raspberry Pi 5, 2026-10-20 13:19~13:20 KST
기존 운영 서비스를 중지하고 실험 바이너리를 20초 실행한 후 원래 서비스를 자동 복원했습니다.

| 항목 | 측정 |
|---|---:|
| 실험 입력 호스트 버퍼 | 22,474 |
| **Wrap21 복구** | **303** |
| **남은 정렬 거부** | **0** (20초 시험) |
| IPC 수신 영상 프레임 | 1,188 |
| 무효 IPC 데이터그램 | 0 |
| IPC ON / OFF 이벤트 합계 | 19,513,140 / 16,391,495 |
| 수신 측 경과시간 | 20.63초 |
| 샘플 capture_fps | 1,019.87 |
| 샘플 web_fps / hdmi_fps | 57.993 / 57.993 |
| V4L2 dequeue 오류 / 시퀀스 누락 / 오류 플래그 | 0 / 0 / 0 |
| IPC 송신 실패 | 0 |
| 기존 서비스 복구 | **RESTORE_OK**, 13:20:00 KST |
| 기존 바이너리 무결성 | **ORIGINAL_BINARY_UNCHANGED=YES** |

시험 보고서 원본은 Raspberry Pi의 `/home/philip/DVS.Wrap21.Live.AB.20261020-131930-639195/`에 있습니다. 저장소에는 대용량 개인 영상·RAW를 업로드하지 않았습니다.

## 장시간 운영 통계는 별도 판단
기존 운영본 누적 `raw2_boundary_embedded_runs_bad=307358`, Marker 간격 971/966/961/956 등의 관찰은 별도 현상이며 v4가 모두 해결했다고 볼 수 없습니다.
**955/960컬럼 차이, 센서 Embedded Header/Frame Counter/Timestamp 검증, 실제 물리 데이터 무손실 여부는 해결되지 않았습니다.**
20초 단기 테스트는 10분·1시간 장기 안정성을 대체하지 않습니다.
