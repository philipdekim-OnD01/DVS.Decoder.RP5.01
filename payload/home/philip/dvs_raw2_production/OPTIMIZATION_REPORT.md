# 손 윤곽·지연 최적화 적용 결과

2026-10-12, Raspberry Pi 192.168.0.177에 적용 완료. 기존 ffplay 영상 창과 우측 설정 패널을 유지함.

## 검증된 성능

- 이전 기록: 캡처 약 108fps, 새 영상 약 6fps. 약 42fps로 반복 출력되지만 새 영상은 센서 16프레임을 모은 뒤 생성되었음.
- 변경 후 6회 측정 평균: 캡처 약 946fps, 새 영상 약 58.6fps. WebSocket 실제 수신 검증에서도 58.7fps 확인.
- 캡처 처리율은 V4L2에서 처리한 프레임 수이며 센서의 목표 2000fps 달성을 의미하지 않음. 표시 목표 60fps와 새 영상 생성률은 구분함.
- dequeue/buffer/sequence gap/HDMI write/IPC send 오류 카운터는 0. RAW2 정렬 검사 실패는 지속되어 해당 프레임은 제외함(측정 구간 약 1%).
- 사용자 손 움직임 테스트에서 “손 윤곽이 보이고 반응도 빨라짐” 확인.

## 적용한 설정

| 항목 | 적용값 |
|---|---|
| 표시 모드 | Time Surface |
| 새 영상 출력 주기 | 목표 16.667ms, 기존 16프레임 대기 제거 |
| 시간 감쇠 τ | 25ms, 3τ 뒤 제거 |
| 표시 목표 | 60fps |
| 해상도 / 서브샘플링 | 960×720 / 1 |
| 점 크기 / 점 확장 | 1픽셀 / 끔 |
| 표시 gain | 125% |
| ON / OFF / 배경 | 흰색 / 하늘색 / 검정(로컬) |
| 공간 잡음 필터 | 켬, 최근 35ms의 인접 이벤트 사용 |
| Hot pixel 필터 | 켬, 입력 활성 프레임 20회/초 기준 |
| 센서 0x0157 / 0x0166 | 0x1F / 0x0F 유지 |
| 센서 0x0167 | 0x07 → 0x0F, 상위 예약 비트 보존 |
| 센서 0x0168 / 0x392C | 0x0F / 0x08 유지 |

매뉴얼 18~19쪽 Table 13과 식을 사용함. REF=15 및 MSB bank=1에서 ON LSB를 7→15로 변경하면 K_ON/K_REF가 20→10이 되어 ON 임계값이 낮아지고, 기존 OFF의 K_REF/K_OFF=10과 균형을 이룸. 매뉴얼은 gain/offset이 미정이라고 명시하므로 절대 밝기 변화율의 정확한 임계값은 산출하지 않음. 센서 쓰기는 read-modify-write와 즉시 readback 확인, 실패 시 원복.

센서는 빛의 변화에서 이벤트를 생성하므로 손 움직임의 윤곽 표시를 위한 설정임. 정지한 손의 일반 카메라 영상 복원이나 손동작 분류 모델을 추가한 것은 아님.

## 코드 변경

- `raw2_producer.cpp`: DMA 데이터를 캐시 가능한 RAM에 복사한 뒤 디코딩. DMA sentinel 초기화 범위를 실제 packed RAW2 영역으로 제한. 빈 바이트 생략, packed-byte 코드 집계. 미정의 11 코드는 통계에만 집계하고 유효 이벤트를 덮지 않음.
- 매뉴얼 37쪽 Figure 46과 실제 원시 샘플에서 0xCCCCCCCC 메타데이터 signature의 byte phase를 확인. PACK_BYTES 배열의 +176 위치를 반영하고 순환 경계 guard를 추가해 메타데이터 픽셀 혼입 감소.
- HDMI 송신은 새 입력만 전달. `frame_surface.py`는 새 입력을 한 번만 반영하고 최신 입력과 시간 감쇠를 기준으로 화면을 렌더링. 점 확장은 저장된 이벤트 좌표/극성을 변형하지 않음.
- `server_production.py`: `/control` WebSocket은 제어·통계만 전달. 영상 viewer당 pending 프레임을 1개로 제한해 느린 클라이언트의 무제한 누적 방지.
- `app_raw2.js`: RAW2 패킷을 실제 이벤트로 디코딩해 기존 Time Surface, 색상, ROI, 반전, polarity 등 표시 기능에 연결. 기존 RAW2 경로는 해당 설정들을 우회했음.
- RAW byte-rate 지표는 V4L2 할당 버퍼 크기 대신 실제 처리 packed 영역 크기로 계산하도록 바로잡음.

## 검증

장비에서 C++ decoder 테스트: packed 코드 집계, 순환 경계, 좌표 매핑, invalid 코드의 유효 이벤트 보존, synthetic 메타데이터 제외 검증 통과. Sparse 데이터의 decoder 비교는 약 2055→504μs/프레임(합성 RAM 입력 기준).

FrameSurface 5개 테스트: ON/OFF·ROI·반전·미정의 코드, 짧은 감쇠와 반복 프레임 갱신 방지, 시간상 인접한 가는 윤곽 보존, 확장 시 원본 이력 보존, hot pixel 입력 프레임 집계 검증. 센서 예약 비트 보존 검증, 실제 제어 연결에서 0x0167=0x0F 읽기, 영상 연결에서 RAW2 패킷 길이·ON/OFF 개수 일치·invalid 11 없음 확인. 서비스 active, 웹 HTTP 200.

## 실행 및 복원

실행 경로: `/home/philip/dvs_raw2_production/`. 기존 `dvs-raw2-production.service` 재실행 시 센서 profile과 표시 기본값이 자동 적용됨.

```sh
sudo systemctl restart dvs-raw2-production.service
```

최적화 직전 백업: `/home/philip/dvs_raw2_production/backup/hand-tuning-20261012/`.

```sh
bash /home/philip/dvs_raw2_production/rollback_hand_tuning.sh
```

롤백은 최적화 직전 바이너리·소스·시작 스크립트·설정 패널·웹 backend/frontend를 복원하고 서비스를 재시작함. 이전 시작 스크립트의 센서 초기화로 0x0167도 이전 값 0x07로 돌아감.
