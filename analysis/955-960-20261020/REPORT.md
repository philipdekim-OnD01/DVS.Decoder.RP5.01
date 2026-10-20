# DVS 955/960 제한 분석 누적 보고서

최종 보고: 2026-10-21 04:35 KST. 사용자의 “지금해” 요청에 따라 예정된 05:00보다 일찍 정리한다. 원인 규명은 미완료다.

## 판정

971블록 간격은 디코딩 전 저장 DMA에 존재한다. 그러나 시그니처를 유효한 Fig46 센서 헤더로 검증하지 못했으므로, 971−16=955를 실제 센서 영상의 물리 컬럼 수로 확정할 수 없다. 최초 원인 레이어와 올바른 960컬럼은 아직 입증되지 않았다. 수정은 하지 않았다.

## 입력과 재현

- 입력: `recordings/2026-10-13/mipi-raw2-10s.dvsraw`의 처음 16개 호스트 레코드만.
- V4L2 sequence 37694–37709, payload 2,810,880B. 호스트 sequence는 센서 frame counter가 아니다.
- 16개의 (record header + payload) 연결 SHA256: `d39ee91aea93fe1605a189aff91326ae43803558642b3f4baeacf81daf46508b`.
- Pi의 같은 원본 첫16개 해시와 동일. 첫payload는 원래 1MiB DMA snapshot 앞175680B와 바이트 단위 일치.
- 첫payload SHA256: `01a066e5a192b10c8da3bcc996531fb7b3e4ca3298f3672b72ff0e2d2a3a66cf`.
- 첫 DMA snapshot SHA256: `53f74c65ef20cf78db5cc1fe806c334b1e8dda7b35d51181995d81632740bfbd`; 뒤872896B는 모두 A5.
- 재현 스크립트: `analyze.py`, `check_headers.py`, `header_invariants.py`, `counter_consistency.py`. 각각 원본을 읽기만 하며 별도 JSON 결과를 쓴다. 전체10초 재분석은 하지 않았다.

## 확인된 결과

| 확인 항목 | 결과 | 해석 한계 |
|---|---|---|
| 16블록 시그니처 run | 16/16 | 센서 프레임으로 인증되지 않음 |
| run 시작 간격 | 971블록 15/15 | 물리 컬럼 손실의 증거가 아님 |
| 단순 인접워드 해석 | 12후보 모두 고정 헤더 불일치 | 다른 필드 위치/interleaving을 배제하지 않음 |
| signature+4 BE32 | 000000e0, 256/256 | Fig46 기대100000e0와 불일치 |
| signature+8 BE32 | 00000000, 256/256 | Fig46 기대00010000와 불일치 |
| 각 고정워드 내부 순열 | popcount 불일치로 복원 불가 | 인접워드 가정에서만 배제 |
| signature+12 BE32 후보 | run내 동일값5/16; 모든slot +1인 인접쌍0/15 | 센서 frame counter로 사용 불가 |
| 저장 과정 | DMA prefix 그대로 복사 | DMA 이전/하드웨어 변환은 미확정 |
| PACK_BYTES 원인 주장 | 코드에서 bit30 설정만 확인 | signature+176 원인을 입증하지 않음 |

record0의 첫 marker chunk 시작 파일offset=155584, signature=155760, head0후보=155764, head1후보=155768, counter후보=155772. record1 signature=330572. 파일상의 거리에서 중간 record header32B를 제외하면174780B=971×180이다.

기존 decoder는 record0 first_pixel=880에서 chunks880..975,0..863을 같은 호스트 버퍼 안에서 순환 읽는다. 이는 저장 스트림의 다음 레코드의 chunks0..858로 이어지는 순서와 다르다. 다만 이 비교 자체는 올바른 센서 좌표/실제 프레임 구성을 입증하지 않으므로 아직 수정 근거가 아니다.

## 근거별 배제와 미확정

- 배제 가능: 디코더가 971 시그니처 간격을 생성했다는 설명. 해당 간격은 입력 RAW에 있다.
- 첫 레코드에서 배제 가능: 로컬 복사 또는 저장prefix 절단이 현재 헤더 후보 값을 만들었다는 설명. DMA snapshot과 동일하다.
- 배제 가능: 현재 인접 head0/head1 워드 내부의 순수 비트/바이트 순열로 Fig46 고정값을 복원하는 설명.
- 미확정: 센서의 실제 송신 바이트, 문서와 칩 revision의 일치, RP1 하드웨어에서의 변환, 다른 위치의 헤더 필드, 실제 센서 frame counter, 최초 손실 레이어.
- 시그니처는 payload 바이트다. Fig47의 embedded DT0x12와 수신 설정DT0x2a를 구분해야 하며, payload만으로 wire packet type을 역으로 단정하지 않는다.
- 20260915 및 별도256개 fullbuffer 진단은 20261013 동일 녹화의 wire/header 증거로 합치지 않는다.

## 검토 반영

독립 검토 #6292378529의 요구대로 host sequence와 sensor frame counter를 분리했고, 같은16개 RAW로 헤더 고정필드와 counter 후보를 검증했다. 유효한 헤더/카운터 판별에 실패했음을 그대로 보고했다. API 자동 검토는 키 미설정으로 SKIPPED이며 검토 통과가 아니다. 04:35 KST 확인 시 추가 독립 기술 의견은 없다.

## 안전 범위 및 실행 기록

서비스/센서 레지스터/Device Tree/RP1 드라이버/운영 바이너리 변경과 새 캡처 없음. 생산 저장소 `git status --short`는 비어 있다. 로컬 분석 산출물만 작성했다. 누적 heartbeat 메시지 수를 실제 수행 횟수로 계산하지 않는다. 모든 예정 재개가 실행됐다는 근거는 없다.

## 다음 단일 작업

현재 칩에 적용되는 embedded 필드 배치 또는 동일 녹화의 wire/header 보존 증거를 찾아, 고정필드와 frame counter를 동시에 검증한다. 그런 근거가 없으면 현 증거 한계를 유지하고 임의 bit mask/보간/960회 읽기만으로 완료를 선언하지 않는다.

## 이슈 기록

- 초기16레코드: https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6291138659
- 12후보 검사: https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6292420072
- Pi 원본 교차확인: https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6293087831
- 순열 불변량: https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6293388558
- 수신코드 감사: https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6297329937
- counter 일관성: https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6297522034
