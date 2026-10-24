# S5KRC1S / RP5 — 원본 RAW2 보존형 Blue-Green 전환 설계

- 결정: 2026-10-25 사용자 요청. **원본을 수정하지 않고 새 Event Packet 실행 경로를 별도 제작**하며, 실패 시 검증된 원본 RAW2로 전환한다.
- 상태: **설계 결정 / 구현·실기 전환 미검증**. `Phase C HARD BLOCKED` 및 `--device PHASE_C_BLOCKED` 유지. 본 문서는 자동 실행 승인이나 복구 성공 근거가 아니다.
- 현재 작업: [PR #5](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/5), [Issue #7](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/7). [RUNBOOK](./RP5_EVENT_RUNBOOK_KO.md), [RESTORE_PLAN — PR #5](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/blob/codex/rp5-event-phases-20261021/docs/event-dt31/RESTORE_PLAN_KO.md), [PROGRESS](./PROGRESS.md)를 함께 읽는다.

## 2026-10-25 진단 우선순위 (Jetson 교차 검토 반영)

원본 RAW2(A) 보존 및 신규 Event(B) 독립 개발의 방향은 유지하면서 **먼저 [Pi Issue #1](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1)의 RAW2 971/976 호스트 마커와 미검증 센서 프레임 경계를 읽기 전용으로 정리**한다. 검증된 Jetson 교훈은 버퍼 즉시 반환·센서 카운터와 호스트 sequence 구분·레지스터 readback 기록 방법이다. 공통 원인/통일 패치가 입증된 것은 아니다.

Codex 작업 기준: [독립 작업 지시](./CODEX_PI_FIRST_DEBUG_20261025_KO.md) / [전체 기술 교차 검토](./CROSS_PLATFORM_REVIEW_20261025_KO.md). RAW2 실기 전환이나 기존 복구 차단 해제를 의미하지 않는다.

## 2026-10-25 현재 실행 우선순위 정정

- **다음 Codex 작업: [Issue #15](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/15)**. 현재 RAW2(A)를 계속 가동하고 기존 코드를 변경하지 않으면서 Event(B)를 별도 빌드·파일 재생·Mock·Viewer로 완성한다. 아래 §5의 '복구 기능 확장보다 새 프로그램 완성' 원칙이 우선이다.
- Pi RAW2 [Issue #1](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/1)은 한정 증거 감사 뒤 UNKNOWN/STOP. Event [Issue #11](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/11)은 저장 8MiB 입력 오프라인 비교 P0–P5 완료 ([PR #13](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/13), 미병합 Draft). 기존 분석을 다시 우선 수행하지 않는다.
- **현재 오프라인 B 개발에는 복귀 구현이 필요 없다.** 동일 센서/CSI 하드웨어를 A와 B가 공유하는 상황에서 **장차 라이브 전환**을 시도할 경우에는 복귀 능력의 입증이 별도 필수다. 그러한 하드웨어 전환은 계속 [Issue #7](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/7) 차단 조건에 묶이고 **Phase C HARD BLOCKED** 및 `--device PHASE_C_BLOCKED`을 유지한다. 새 승인 없는 실기 작업 금지.

## 1. 가장 중요한 원칙

**기존 RAW2는 불변의 known-good(A/Blue), Event Packet은 독립 개발 후보(B/Green)**. 신규 기능을 기존 프로덕션 소스, 바이너리, 서비스, 모듈 설정, sensor setfile에 덮어쓰지 않는다. 기존 성공한 디코더·Mock·watchdog 검사 코드는 버리지 않고 검증된 구성요소로 재사용한다.

- **A — RAW2 Production**: 현재 CSI-2 `DT=0x2A`, 센서 초기화/setfile/프로파일, receiver의 DT 설정, RP1 CFE / media graph, V4L2, producer, Web·HDMI 서비스.
- **B — Event Engine**: 별도 디렉터리·프로세스/서비스 정의와 전용 설정으로 `DT=0x31` 입력, V4L2 수신, 디코더, 960×720 Viewer를 개발·검증. 먼저 file/mock로 검증한다.
- **Switcher (최소 오케스트레이터)**: 장비 상태 snapshot과 사전 점검, 단일 장치 소유권 관리, 모드 전환 호출 및 원본 복귀 절차·정상 동작 확인만 담당한다. 복잡하고 상시 실행되는 별도의 범용 '복구 애플리케이션'을 새로 만드는 것이 목표는 아니다.
- **Backup ≠ restoration**: 기존 프로그램을 디스크에 보존한 것만으로 센서 레지스터, receiver descriptor DT, 모듈 probe 상태, media graph, V4L2 스트림이 복원되지는 않는다. **A로 돌아와 정상 영상·이벤트/버퍼 카운터를 재확인해야 전환 성공**이다.
- 별도 프로세스/서비스/폴더는 **동일 S5KRC1S 카메라·CSI 포트를 물리적으로 분리하지 않는다**. 같은 센서를 A와 B가 동시에 STREAMON 하는 설계는 금지한다. 이 설계는 *소프트웨어 Blue-Green + 하드웨어 순차 소유권 전환*이다.

## 2. 목표 구조와 배포

```text
                        [Samsung S5KRC1S + 단일 CSI-2/RP1 CFE]
                                            |
                        [단일 소유권 / Fail-closed Switcher]
                                 /                       \
                  A: 기존 RAW2 / DT=0x2A      B: 신규 Event / DT=0x31
                  원본 파일·서비스 불변       별도 실험 디렉터리·서비스
                  기존 Web/HDMI              Decoder → Event Engine → Viewer
                                 \                       /
                                   원본 RAW2 복귀·건강 확인
```

- 기존 버전 및 파일 해시는 관측된 **현재 정상 상태**를 기준으로 별도 비공개 immutable backup/bundle에 고정한다. private sensor register dump/setfile·민수 SDK 원문, 자격정보는 공개 Git에 올리지 않는다.
- 신규 프로그램·설정은 다른 위치에만 작성한다. 배포 스크립트도 운영 파일 교체·서비스 disable/enable·default target 변경을 수행하지 않는다.
- 개발 시 A를 계속 가동하고 B를 파일·mock·가짜 ioctl로 시험할 수 있다. **B의 실제 CSI-2 입력은 A를 중단해야 할 수 있으므로 실기 승인과 복귀 준비가 선행**되어야 한다.
- Switcher는 무조건 성공을 반환하는 shell script가 아니라 **상태 확인 및 단일 장치 소유권의 작은 상태 기계**로 설계한다. 허가되지 않은 상태/작업은 아무 것도 변경하기 전 거부한다.

## 3. 향후 전환 시나리오 (현재 실행 금지)

1. **Preflight**: 현재 A의 작동 커널/모듈/DT·media 그래프, 서비스 상태, 실제 센서 레지스터/DT, 정상 영상·데이터율·CSI 오류 baseline 확보 및 hash 검증. Event setfile/geometry/descriptor와 유효한 무재부팅 복귀 절차를 검증한다. 독립 watchdog은 실제 안전한 경로를 시험한다.
2. **A → B**: *모든 조건이 충족된 다음에만* 기존 A를 일시 정지하고, 검증된 센서 송신 `0x31` + RP1 CFE receiver `0x31` 바인딩과 DMA geometry를 확인한 뒤, B를 최대 10초 수신한다. 패킷 경계/타임스탬프/좌표·ON/OFF·FPS·CSI 오류를 기록한다.
3. **B → A**: B 장치를 정지·반납하고, pinned A runtime/센서 `0x2A`/receiver DT 재probe 상태/graph 등을 실제 원래 값으로 복원한 뒤, 기존 A를 안전한 방식으로 가동한다. 서비스 active만으로 성공 처리하지 않고 **새 sequence 증가, 정상 손가락 영상, Web/HDMI 및 오류 카운터**를 확인한다.
4. **실패 시**: 테스트 중단 및 오케스트레이터의 독립 watchdog에 의해 *검증된* A 복귀 경로만 시도한다. 복구 검증 실패 시 즉시 증거를 남기고 수동 개입을 요청한다. **reboot, override/config 삭제, 서비스 비활성화, legacy rollback 자동 대체 호출 금지.** 안전한 자동 복귀 경로가 준비되지 않았으면 **전환 자체를 시작하지 않는다**.
5. 최초 실기 검증 한도는 이전 합의의 **10초 × 최대 3회, 운영 중단 총 15분 이내**, 금지된 재부팅·영구 수정은 그대로 유지한다.

## 4. 절대 재사용하면 안 되는 기존 위험 경로

Pi에서 조사한 기존 `raw2_production_rollback.sh`는 *현재 RAW2 복귀*가 아니라 RP1 override/설정 제거, 서비스 비활성화, 모듈 변경 및 재부팅으로 이어진다. **B 실패 시 이 스크립트를 실행하거나 timer에 예약하는 것은 금지한다.**

`raw2_production_start.sh`는 단순한 프로그램 기동이 아니다. 센서 setfile/레지스터와 media graph를 다시 설정하며 `pending_first_boot_validation` 조건에서 파괴적인 first-boot 만료 타이머를 만들 수 있다. `Restart=on-failure` 자동 재시작까지 고려해야 하므로, **그대로 `systemctl restart`하는 것을 A 스위치 검증 완료로 간주하지 않는다**. 별도 안전한 시작 경로와 race/ownership 증명이 선행되어야 한다.

## 5. Codex 작업 우선순위 — 복구 기능 확장보다 새 프로그램 완성

1. **A 보존 우선**: 기존 RAW2 파일·서비스·센서·모듈·DT·미디어 설정을 변경하지 말고 기존 상태/해시/우회 위험을 읽기 전용으로 추적한다. 프로덕션에서 저장한 사본이 *현재* 센서 값이라는 근거는 없다면 NOT TESTED로 표시.
2. **B 독립 실행 완성**: PR #5의 기존 decoder·bounded queue·V4L2 adapter·Viewer를 새 Event-only 빌드/서비스 구성으로 조직한다. 모든 실험 실행은 file/mock 및 격리된 임시 디렉터리에서만 진행한다. 기존 `--device PHASE_C_BLOCKED` 유지.
3. **Switcher 최소 설계**: `A_ACTIVE`, `PREFLIGHT_OK`, `B_ACTIVE`, `RETURNING_TO_A`, `A_VERIFIED`, `MANUAL_INTERVENTION` 상태를 가진 **simulated only** 도구/테스트를 작성한다. 기존 restore dry-run/mock24와 readiness33 및 watchdog 테스트/증거는 삭제·재실행 남발하지 말고 활용한다.
4. **전환 조건을 검증 가능한 형태로 문서화**: A→B, B→A 중 실제 센서 I2C·모듈 probe/descriptor·CSI byte geometry가 필요한 구간을 식별하고, 그 단계에는 live backend/승인이 아직 없음을 표시한다. start/installer/firstboot race를 격리 시험으로 해결하고 독립 watchdog/health 확인의 실패 주입을 한다.
5. **검증과 GitHub 기록**: 새 작업은 기존 [PR #5](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/5) 개발 브랜치에서 진행하고 [Issue #7](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/7)을 추적한다. 각 완료 항목을 정확한 명령·실측·로그·파일 해시·남은 blocker로 `PROGRESS.md`에 기록해 commit/push한다. 소스/데이터 기밀을 지킨다.

## 6. Gate / Done 정의

| Gate | PASS의 근거 | 현재 |
|---|---|---|
| A | Pi native decoder 및 오프라인 회귀 | 기존 증거에서 PASS |
| B | 새 프로그램의 file/mock capture→decode→viewer/종료·fault injection | 기존 증거에서 오프라인 PASS, 실제 수신 미검증 |
| Switch 준비 | 불변 A baseline, 안전한 start/stop, **실제 원본 복귀 가능한 하드웨어 경로**, watchdog/health 연동이 각각 증명됨 | **미완료** |
| C | 실센서 MIPI `DT=0x31` 수신·decode·Viewer 측정 | **HARD BLOCKED / NOT TESTED** |
| D | A에 되돌린 뒤 실제 RAW2 정상 영상과 수신 지표 확인 | **NOT TESTED** |

**최종 목표는 예전과 같다: RP5에서 DVS Event Packet의 정상 좌표·시간·ON/OFF를 실시간 수신하고 Viewer에서 손/손가락을 올바르게 표현한 다음, 기존 RAW2로 안전하게 돌아오는 것.** 새로운 전략은 그것에 도달하는 구현·배포 방식을 단순화한 것이며, 새로운 승인 없이 장비를 전환하라는 지시가 아니다.
