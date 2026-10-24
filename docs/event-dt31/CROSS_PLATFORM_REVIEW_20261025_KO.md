# S5KRC1S DVS — Raspberry Pi 5 × Jetson Orin 교차 검증 및 최종 권고

- 기준일: **2026-10-25 KST**.
- 범위: Raspberry Pi 5 / RP1 CFE, Jetson Orin / NVCSI–VI, Samsung S5KRC1S.
- 작업 성격: **기존 GitHub 이슈·보고서·코드 검토에 기초한 기술 판단/인수인계**, 새로운 Pi/Jetson 실험 결과가 아니다.
- **최우선 소스는 [Pi Issue #1](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1)의 마지막 독립 감사**다. [Jetson Issue #1](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/issues/1)은 **다른 이슈**, 4아키텍처 20조건 *가정 기반 시뮬레이션*이다.
- 별도 실행 명령: [CODEX_PI_FIRST_DEBUG_20261025_KO.md](./CODEX_PI_FIRST_DEBUG_20261025_KO.md). 기존 [Blue-Green 설계](./BLUE_GREEN_SWITCH_PLAN_KO.md)·[RUNBOOK](./RP5_EVENT_RUNBOOK_KO.md)·[PROGRESS](./PROGRESS.md)의 안전 제약 유지.

## 1. 교차 검토 출처와 검증 수준

| 출처 | 형식 | 활용/한계 |
|---|---|---|
| [Pi RAW2 Issue #1](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1), [전체 스트림 감사](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6300566219), [마지막 센서 경계 감사](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6300872307) | 독립 검토 및 기존 RAW 분석 | RAW2 호스트 경계 현상에 대한 **최신 우선 근거**; on-wire 신원까지 확인된 것은 아님 |
| [Pi RAW2 955/960 증거](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/tree/codex/955-960-analysis-evidence-20261021/analysis/955-960-20261020) | Python 분석·JSON·checksum | 같은 저장 RAW의 후보 마커/헤더 불일치; 원본 RAW는 공개 저장소에 없음 |
| [Pi PR #5](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/5) | RP5 native SDK·file/mock·복구 readiness 증거 | 8MiB Event sample의 결정적 재생, 실시간 `DT 0x31` 수신·실기 복구는 **NOT TESTED** |
| [Jetson 2026-10-25 dossier](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/tree/main/docs/diagnostics/2026-10-25/) | **비공개** 진단 보고서 01~05/README | 플랫폼 비교·이슈 분리·진단 방법; 권한 없는 Codex는 원문 접근을 추측하지 말 것 |
| [Jetson 실제 녹화 보고](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/blob/main/docs/test-report.md), [세션 검증 코드](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/blob/main/jetson/dvs-recorder/check_session.py) | Jetson 현장 기록·소스 | 개별 센서 모드·시간·장면·버퍼 구성에만 해당 |
| [Jetson Gap 진단 코드](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/blob/main/e850/dvs-tools/dvs_gaps.py), [센서 검증 설계](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/blob/main/jetson/sensor-tool/README.md) | 소스·방법 | 구조/알고리즘은 참고 가능하지만 Jetson I2C 명령이나 민감 SDK 소스를 공개 저장소로 복제 금지 |
| [Jetson Issue #1 모델](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/issues/1) | 네 경로 × 5부하 × 60초 가상 큐 모델 | **실측 손실률이 아님**. 제안 4-worker 무손실은 아직 구현·검증되지 않음 |

**원칙:** FACT(관측) / CORROBORATED(독립 대조) / HYPOTHESIS(원인 후보) / UNKNOWN(미입증)을 구분한다. Jetson에서 유사 징후가 있었다는 사실은 Pi의 공통 원인, 공통 패치 근거가 아니다.

## 2. 최우선: Pi Issue #1 — RAW2 971/976와 955/960

### FACT / CORROBORATED
- 보관된 기존 10초 RAW2의 **호스트 레코드**는 `976 × 180 = 175,680B`; 후보 마커 시작 간격은 `971 × 180 = 174,780B`. 차이 **5블록 = 900B**.
- 첫 16 호스트 레코드에서 **971 간격 15/15**. 전체 16,140 레코드 독립 감사에서는 **971 간격 16,220회**, 이외 **955 간격 1회·987 간격 1회** 보고.
- Wrap21 v4는 이전 거부 200/200건을 **호스트 마커 분류상 복구**, 기존 정상 15,940건 유지. V4L2 sequence gap 0은 호스트 측 관측이다.
- Wrap21 거부 200건에서 5블록 위상차와 원형 마커 판정 오류의 직접 관련이 검증됐다. 다만 그 중 명목상의 960-source-chunk 읽기 범위가 **다른 후보 마커의 embedded-flagged 5블록**을 포함한다는 관측이 있다. 분류 통과는 960 물리 픽셀 컬럼의 복원 증거가 아니다.
- 보관 첫16 레코드의 header+payload SHA-256: `d39ee91aea93fe1605a189aff91326ae43803558642b3f4baeacf81daf46508b`. 첫 payload는 원 DMA prefix와 byte-for-byte 일치.
- `0xCCCCCCCC` 후보의 인접 고정필드: +4 BE32 `000000e0`, +8 `00000000` (각 256/256). 사용한 데이터시트의 Fig.46 기대 `100000e0`, `00010000`와 불일치. +12 frame counter 후보도 동일 16-marker run 내 단일값 **5/16**뿐이어서 **실제 센서 카운터로 인증 실패**.

### UNKNOWN / 금지된 추론
- 후보 마커가 **진짜 embedded frame header인지**, 어떤 칩 revision·패킹 정의에 해당하는지, CSI-2 on-wire `DT/WC/FS/FE`가 해당 **동일 녹화**와 함께 보존돼 있는지 확인되지 않았다.
- `971−16=955`는 **센서 물리 5컬럼 손실을 증명하지 않는다**. 12후보/순열 반증은 검사한 *인접 워드 해석*에 국한된다.
- `(first_pixel+serial)%976`으로 960회를 읽었다고 **한 센서 프레임의 960컬럼을 올바로 복원한 것은 아니다**.
- 역사적인 `LEN_LIMIT/multipacket-line` 실험은 **별도 현상/센서 구성**이다. 기존 관측 `30 frame / discard 증가 960 = 32/frame`과 실험설정만으로 현재 RAW2 971의 원인이라 단정하지 않는다.

**다음 최소 분별 검사:** [마지막 Issue #1 감사](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1#issuecomment-6300872307)대로 **동일 2026-10-13 녹화의 기존 자료**에 `DT/WC/FS/FE` 또는 칩에 적용되는 검증된 헤더 매핑이 있는지 한정된 **읽기 전용 확인 한 번**. 보존되지 않았다면 **UNKNOWN으로 정지**. 추가 임의 비트마스크·12후보 반복·새 장시간 캡처·가짜 5컬럼 합성 금지.

## 3. Pi Event DT=0x31 (별도 스트림, 별도 성공 기준)

- Pi PR #5의 8MiB **저장된 Event Packet** 재생: RP5 C++ native regression **17 PASS**, 출력 **1,557 frames / 1,469,217 events**, ON **706,157**, OFF **763,060**, invalid/unknown **0/0**, `unsynced_groups=830`. 1B/4B/4093B/1MiB/랜덤 입력 split의 출력 해시 일치.
- 해당 file replay와 V4L2 adapter **22 mock PASS**, restore **24 mock PASS**, readiness/watchdog synthetic pass는 **CSI 실제 수신, 센서 연속성, 손가락의 물리 X/Y 정확성 또는 RAW2 실기 복구를 입증하지 않는다**.
- 과거 `reference-b3`는 B2/Group2/OFF를 완전 검증하지 못했고, 강한 128픽셀 주기와 영역 불균형이 있었다. 새 sample에서 ON/OFF가 출력되었다고 **기존 물리 bank 순서**가 검증된 것은 아니다.
- **권장 오프라인 2차 검사**: 동일 공개 가능하지 않은 원본을 비공개 작업 공간에서 고정하고 구형 reference parser와 새 SDK의 COLUMN/Group1/2/ON/OFF/timestamp 및 frame/byte 오프셋 차이를 정밀 비교. Jetson의 `dvs_gaps.py` 경계 집계 아이디어를 활용하여 `unsynced_groups`와 buffer/frame 경계의 상관관계를 시험하되, 이는 손실 증명도, RAW2에 직접 실행할 수 있는 도구도 아니다.

## 4. Jetson에서 재사용할 **검증된 교훈** (원인 이식은 금지)

| Jetson 자료상 관측 | Pi에 유효한 방법 | 전용 금지할 결론 |
|---|---|---|
| 기존 수신 loop(8 MMAP 버퍼, copy+parse+display)의 고부하 처리량 약 37.8개 1MiB buffer/s; 다른 수신 구성(USERPTR 32, 조기 QBUF, 분리 decode) 약 319개/s | RX dequeue→requeue 지연 p50/p95/p99, bounded queue drops/high-water, 독립 decoder worker를 **별도로 계측** | 구성·환경이 달라 8.4배 수치가 순수 구조 개선 효과라는 인과 주장 금지 |
| 15h 녹화 V4L2 sequence gap 0, 그러나 보고서 `frame_gaps` 경고 19회 | **Host V4L2 sequence, 센서 Frame End/counter, CSI CRC/ECC, queue starvation**를 각각 추적; 1MiB buffer ≠ sensor frame | CRC/V4L2 0 → 모든 센서 프레임 손실 0이라는 주장 금지. `frame_gaps` 경고도 실제 정확한 프레임 손실 수가 아님 |
| setfile 82개 register의 2026-10-16 읽기값 일치. 다른 이후 시험에서 기본값 회귀 보고 | live *readback* vs 저장된 setfile을 명확히 구분; streaming/driver lifecycle/전원·XRES·MCLK 타임라인 교차 | 같은 리셋 문제를 Pi에서 관측했다고 주장 금지. Jetson I2C 주소·명령을 Pi에 복제 금지 |
| Jetson 8픽셀 sawtooth 보고(포맷·방향·측정 방법 불명) | RAW2면 2-bit packing/stride, AER면 Group/B2/bit order/좌표/renderer를 각각 조사 | Pi 128픽셀/5블록과 공통 원인 단정 금지 |
| Jetson lane rate 2496Mbps에서 corr_err 8건/약2588초, 2298Mbps에서 0건/약1.5h(후자는 starvation 구간 포함) | 송수신 lane-rate·DT·WC·frame/line 설정 동시 검증 | 다른 보드의 최적 lane-rate를 Pi에 그대로 적용 금지 |

**Jetson Issue #1 시뮬레이션:** 4-worker integrated 0% 손실 등은 **가정 기반 산출물**이다. 제품 벤치마크/드라이버 검증 성적/실제 Pi 손실률로 보고할 수 없다.

## 5. 공동 계측 규격 및 DONE의 의미

각 검증은 모드와 샘플 해시, 칩/driver/kernel 출처, 레인 수·속도, setfile digest, 송신·수신 CSI `DT/WC`, CSI FS/FE, 수신 V4L2 `sequence/bytesused/stride`, 센서 Frame End/Counter 및 Timestamp, invalid/unknown, `unsynced_groups`, queue depth/drop/p99 service time, CRC/ECC, 관측 구간과 정상/오류 상태를 분리해 저장한다. 측정하지 않은 값은 **UNKNOWN**, 재생은 **OFFLINE**, 합성은 **MOCK**으로 명시한다.

완료 판정 단계:
1. **수신됨**: 호스트 DMA/V4L2 buffer와 실제 선로 패킷 식별이 맞음.
2. **일관되게 디코딩됨**: 동일 입력을 임의 청크로 분할해도 동일 이벤트/프레임 및 checksum.
3. **센서 물리 사실과 맞음**: 프레임 경계 인증, 실제 좌표/시간·ON/OFF와 동기화가 독립적으로 입증.
4. **운영 복귀 검증**: 한 센서/CSI 포트를 공유하는 RAW2(A)↔Event(B)에서 센서·receiver·media·실제 Viewer 상태가 완전히 정상 복귀.

현재 상태: RAW2 **Issue #1는 UNKNOWN**, PR #5의 **file/mock PASS는 유지**, 실센서 Event `DT0x31`/실제 RAW2 전환·복구는 **PHASE C HARD BLOCKED / NOT TESTED**. `--device PHASE_C_BLOCKED`을 해제하지 않는다.

## 6. 최종 작업 우선순위

1. **Pi Issue #1의 현재 마지막 독립 감사를 기준으로 971/976 마커/센서 프레임 신원 증거 공백을 끝까지 정리**. 더 이상의 동일 분석 반복보다 있는/없는 동시 wire/metadata 증거 한정 확인. 충분한 증거가 없으면 미확정 종료/보고.
2. Jetson `dvs_gaps.py`의 **경계 검사 방법**과 `check_session.py`의 **호스트 vs 센서 카운터 구분**을 참고하여 Pi Event 기존 sample에 안전하게 적용할 오프라인 설계/테스트.
3. 구형·신규 디코더 동일 원본 비교, `unsynced_groups=830`의 계층별 의미 및 물리좌표 미검증 범위 명확화.
4. 기존 RAW2를 불변 보존하면서 신규 Event Engine을 독립 파일/mock 구성으로 고도화. CPU/RAM/queue/WC·DTO/CSI 같은 지표는 실측 전 가정으로 기록.
5. 최소 fail-closed Blue-Green switcher 준비. `raw2_production_rollback.sh` 실행/예약 금지, start→firstboot timer 경합 해결, 비운영 환경에서 실제 원본 복구 및 watchdog 건강 확인이 가능해진 경우에만 별도 실기 GO 검토.
6. **결국 최종 목표**는 RP5 실센서 Event `DT=0x31` 수신·손가락 영상·센서 이벤트 정확성을 증명하고 RAW2(A)로 검증된 정상 복귀하는 것. 현재 달성 아님.

**접근/보안:** Jetson `nrv-dvs-Orin01`의 10/25 dossier는 비공개. 사용자 요청 범위의 비교 요지만 인용하며 팀 메일 원문·전용 SDK·setfile·레지스터 덤프·환자 데이터는 공개 저장소에 넣지 않는다. 접근되지 않으면 원문 인용/복제 없이 관련 URL·검증 수준을 남기고 중단한다.
