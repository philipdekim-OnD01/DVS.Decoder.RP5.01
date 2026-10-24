# RAW2 971/976 — 한정 출처 감사와 선택 범위, UNKNOWN/STOP

2026-10-25 KST. 사용자 요청 및 `CODEX_PI_FIRST_DEBUG_20261025_KO.md`에 따라 Pi Issue #1을 우선 조사했다. 시작 개발 HEAD53b6cf9에서 별도 `codex/raw2-971-provenance-20261025`를 만들었다. Event PR #5의 코드/증거는 변경하지 않았다.

| 구분 | 결과 | 근거 |
|---|---|---|
| FACT | host976×180B, candidate-marker971×180B. 900B 차이는 저장 입력에 존재 | `selection.json` 첫16레코드, 15간격; 기존 2c3b2f1 evidence와 같은 sample SHA |
| EVIDENCE | 동일 촬영 source 문서는 CSI wire header/ECC/CRC를 제공하지 않는다고 명시. Pi packager는 `<QQ4I>` host metadata만 읽고 payload를 건너뛰어 통계 작성 | `local-provenance.json`, `pi-provenance.json`; 아래 출처 hash |
| CONFLICT | Fig46 인접 고정필드 및 +12 counter 후보 실패는 이전 감사의 음성 결과. 이번에 12후보 재검사하지 않음 | [센서 경계 감사 #6300872307](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6300872307) |
| UNKNOWN | 인증된 sensor_frame, 실제 wire DT/WC/FS/FE, 실제960컬럼과 최초 오류 레이어 | `first_bad_layer=UNKNOWN`; candidate marker를 sensor frame으로 승격하지 않음 |
| DECISION | **UNKNOWN/STOP**. 패치/추가 캡처 없음 | 같은 촬영의 검증된 wire/header 신원 자료 없이는 근본 원인 확정 불가 |

## 한 번의 한정 출처 확인

로컬 `recordings/2026-10-13` 10개 항목과 Pi `/home/philip/dvs-recordings` 13개 항목을 depth1로 검사했다. 목록/작은 문서 hash만 수집하고 큰 RAW/tar/wsraw/영상 내용은 이 출처 검사에서 읽지 않았다. 256항목·text262144B 제한. 이번 검사는 해당 두 폴더와 기존 분석/문서/수신 소스에 한정하며 **장비 전체의 증거 부재를 증명하지 않는다**. 다른 촬영의 로그를 대신 사용하지 않았다.

목록에 식별된 Pi metadata/packaging log/package_raw.py/record.py 네 파일만 추가로 읽었다. 실행하지 않았다. metadata JSON과 log는 host seq/gap 및 size/hash 통계이며 wire 로그가 아니다. package_raw.py는 host record header만 읽고 payload를 seek하며 `full_dma_sample` tail만 집계한다. record.py는 웹소켓 R2F1 저장 도구이며 같은 MIPI 촬영의 wire identity가 아니다. 패키징 도구/파일 존재만으로 모든 과거 촬영 동작을 증명하지 않는다.

| Pi 출처 | SHA256 | 판별 |
|---|---|---|
| mipi-raw2-10s.json | 5d31595498496ba853409a1632621e88e7a564c9000cf1eda94e9ccec29a4022 | host metadata, wire 미제공 명시 |
| package_raw.log | 39ed06a2590e059864bdb6e675c47992d7007e6533bf00bae0ebc014d9957fbf | 동일 집계 JSON |
| package_raw.py | 987251a425ceded35072f10259d8255df3b989a275a96766973d47b5f2ef4e0d | 컨테이너 집계/압축 도구; 실행 안 함 |
| record.py | 9f6e7ae7d72ca29e8475b891f65fef5ca0a510919029be8fefbf9e8707d5684b | 별도 websocket 저장; 실행 안 함 |

원본 proprietary 문서/RAW/SDK/setfile은 공개 Git에 복제하지 않았다. 수신 코드 `drivers/rp1_cfe/csi2.c:239`의 packet counter 구현 존재는 10월13일 촬영과 동시 저장된 counter 증거가 아니다. 현재 debugfs/I2C는 읽지 않았다.

## 최초16개 host와 원형 재구성의 구분

`check_selection.py`는 RAW 파일 헤더32B와 최초16개 header+payload만 읽었다(2,811,424B). SHA256 `d39ee91aea93fe1605a189aff91326ae43803558642b3f4baeacf81daf46508b` 일치. candidate marker chunk864,859,…,789; 971간격15/15. 기존 헤더 배치 후보를 재생성하지 않았다.

record0의 marker 파일offset155584, signature155760; record1 marker330396. 중간 host header32B를 뺀 간격174780B. record0 first_pixel880, 선택 source chunk880..975,0..863은 nominal960개이며 이 record 안의 marker flags 중첩은0이다. 그러나 serial96에서 같은 record의 chunk0으로 되돌아간다. chronological 다음 바이트는 record1 chunk0이므로 같은 센서 프레임의 순차960컬럼이라는 근거가 없다. candidate0 종료 뒤부터 candidate1 시작까지는955개 **chunk 간격**이며 물리 컬럼 수로 인증된 값이 아니다.

## Wrap21은 별도 candidate marker5개를 포함

아래는 [기존 전체 감사 #6300566219](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6300566219)의 세 사례에 대한 **산술 검증**이다. 이번에 record173–175나200건을 RAW에서 재실행한 결과가 아니다. 이전200/200 판정 결과를 새로 인증하지 않는다.

| host record | 이전tail+현재head | 현재head+tail | 다음 candidate marker 시작 | first_pixel / 선택 source chunks | flagged 중첩 |
|---|---|---|---|---|---|
| 173 | 1+15=16 | 15+6=21 | chunk970 | 15 / 15..974 | 970..974 (5) |
| 174 | 6+10=16 | 10+11=21 | chunk965 | 10 / 10..969 | 965..969 (5) |
| 175 | 11+5=16 | 5+16=21 | chunk960 | 5 / 5..964 | 960..964 (5) |

원형 classifier가 별개 candidate 조각을21로 합치는 문제와 nominal960 source chunks에 다른 marker flag5개가 들어오는 문제를 구분한다. `raw2_wrap21.hpp:8–18`은 좁은 host 분류 복구이며 sensor header 인증/컬럼 복구가 아니다. `raw2_producer_wrap21.cpp:264–272`의 modulo976과 signature offset+176으로180B 읽기, 557–558행 cached prefix 복사, 575–585행 first_pixel 경로를 확인했다. `source-pins.json`이 읽은 소스 commit/hash를 고정한다. 표의 중첩은 **source chunk flag** 기준이며 +176 shifted window의 실제 byte 범위나 검증된 물리 좌표와 동일하다고 주장하지 않는다. boundary_live_shadow.hpp 역시 SAME flags를 관찰하므로 독립 센서 counter 인증 수단이 아니다.

## 실제 실행 / 안전 / 종료 판단

- `python3 provenance_inventory.py <session-directory>` 로컬, `ssh ... python3 - /home/philip/dvs-recordings --pi-state < provenance_inventory.py` Pi: bounded inventory 완료. 발견된 작은 관련4파일 읽기 완료.
- `python3 check_selection.py <existing-raw> --results selection.json` 로컬: PASS(first16 입력 신원/선택 범위, audit-derived3개 산술). 전체 RAW 재스캔/12후보 재실행/960 센서 컬럼 검증은 NOT TESTED.
- Pi 관측 UTC2026-10-24 21:39:04 (=KST10월25일06:39:04): RAW2 active/enabled, PID683775, NRestarts0. 서비스/센서/I2C/모듈/DT/media 변경0, 새캡처0. live 복구 시험 아님.
- **first_bad_layer=UNKNOWN**. 971 규칙의 센서/RP1 원인을 규명했다고 보고하지 않는다. 이미 입증된 host marker 분류와 재구성 위험을 센서 wire 원인과 구별했다. 별도 수정 PR 없음; 이 PR은 분석/증거만이다.
- 다음 단일 분별 조건: **동일10월13일 촬영에 연결되는 인증된 wire trace 또는 검증된 해당 chip/packing header mapping**이 확보되어야 한다. 현재 자료만으로는 UNKNOWN/STOP. 운영 변경·새캡처로 이를 해소하려 시도하지 않는다. Event Phase C HARD BLOCKED 유지.
