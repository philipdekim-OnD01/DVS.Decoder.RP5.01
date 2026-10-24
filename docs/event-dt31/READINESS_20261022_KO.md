# Issue #7 Phase C readiness — NO-GO

2026-10-22. 최신 Issue #7과 PR #5 source review/handoff를 확인하고 안전한 read-only/file/mock 작업을 수행했다. **Phase C HARD BLOCKED / production_ready=false / live capture0회.**

## 이번에 추가 검증한 내용

| 항목 | 실제 결과 | 검증 범위 |
|---|---|---|
| bundle·startup·경합·프로세스 watchdog | 최종33건 macOS/Pi PASS, source hash 일치 | 합성 payload/fixture, 실제 hardware backend 없음 |
| systemd marker-only watchdog | 최종5건 PASS | PID1 parent, 별도 system.slice cgroup, source pin·보호 속성 확인 |
| 시험용 SSH client 종료 | PASS | client 종료 후 새 query 시 result 없음 → 이후 독립 unit이 NOOP marker 생성 |
| C++ file type/drift guard | 7건 Pi ASan/UBSan PASS | 일반 ext/tmpfs, symlink/FIFO/directory/virtual file·변조 거부 |
| 엔진 file/CLI guard | 6건 Pi ASan/UBSan PASS | --device/--force 거부, 특수·가상 파일 우회 거부 |
| 취득부 변경 후 sample 대조 | complete1557/events1469217/기존 output hash 일치 | 승인된 저장 샘플이며 실기 전송 성능 아님 |

기존 Gate A17 / adapter22 / restore24 및 기존 Viewer/file/queue 증거는 보존했다. 변경하지 않은 decoder 전체 suite를 반복하지 않았다. 새 입력 취득부를 바꾼 이유로 그 부분의 regression과 샘플 출력만 대조했다. Python suite에 ASan을 적용했다는 주장은 하지 않는다.

33건에는 외부 pin과 role/file hash, missing setfile, malformed saved register list, 잘못된 DT/geometry, 경로 traversal/symlink/명령 주입, 위조 live proof와 이전 성공, marker initial-check 후/중간 stage 생성, concurrent installer·restart·controller lock, file drift 및 cancellation 오류가 포함된다. 기대한 거부와 실제 거부가 일치해야 PASS로 기록했다.

## 실제 독립 watchdog의 관측과 실패 수정

새 `rp5-dvs-rdy-*` transient unit만 생성했다. worker는 `User=philip`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateDevices/PrivateNetwork=yes`, `NoNewPrivileges=yes`, `DevicePolicy=closed`, 자기 case tmp만 ReadWritePaths, 제한된 CPU/메모리/RuntimeMaxSec에서 실행된다. 요청된 전체 속성과 실제 확인한 핵심 속성/cgroup/ExecStart/source pin은 JSON 및 실행 코드에 남겼다. 기존 production/firstboot/camera watchdog은 실행·예약·정지하지 않았다.

최종 관측(worker 경과 시간, unit 전체 수명과 구분):

- 1.2초 deadline: 약1.2225초 후 `FIRED_NOOP_ALERT`.
- 정당한 run/nonce/합성 proof 취소: 약0.0562초 후 `CANCELLED_SANDBOX`.
- 잘못된 token: 약1.2205초 후 만료 NOOP; 취소되지 않음.
- 잘못된 JSON token 타입: 약1.2112초 후 만료 NOOP; worker를 죽이지 않음.
- unit RuntimeMaxSec3초, worker 요청6초: 약2.5853초의 worker 경과 후 SIGTERM을 받아 `TERMINATED_NOOP_ALERT`. manager journal의 “Service reached runtime time limit”/timeout을 별도 보존했다.

첫 시도는 tempfile의 쓰기 probe가 strict sandbox에 막혀 readiness 이전 실패했다. 보호를 완화하지 않고 Linux tmp 경로 확인을 무쓰기 방식으로 수정했다. 코드검토에서 발견한 non-string 취소 token의 예외 가능성도 타입 검사로 수정하고 회귀했다. 최초 실패와 앞선 버전 결과를 지우지 않았다.

실제 시험 소유 SSH client 하나를 종료한 뒤 worker가 계속 실행하는 것도 확인했다. worker PPID1 및 dedicated cgroup은 query SSH session과 달랐다. 이 검증은 기존 JSON boolean과 다르지만 **네트워크 케이블 단절/sshd 재시작/모든 logind 정책/실제 RAW2 restore는 NOT TESTED**다. 취소 proof는 합성 상태의 인증 메커니즘 시험이며 실제 복구 health 증명이 아니다. 모든 worker action은 marker-only이고 하드웨어 호출0회다. 종료한 unit들은 --collect로 자동 정리되어 마지막 목록0개였다.

## 읽기 전용 inventory와 운영 보존

- 실제 `i2ctransfer`: `/usr/sbin/i2ctransfer`, `/sbin` alias도 동일. SHA256 `94dd49d676021518cda6aa0c4997bc5cd71bf04fea39216e57cbe71861b7c855`. `/usr/bin` 부재를 전체 부재로 해석한 이전 모호성을 해소했다. **실행/I2C 접근0회**.
- kernel `6.12.47+rpt-rpi-2712`. `rp1_cfe` loaded/file srcversion `8C232B64FF7276822DD4563`, sensor `66BD4258C713EEC299A7720` 일치. 현재 sensor instance의 get_frame_desc 실측을 대신하지 않는다.
- live FDT는 일반 사용자에서 PermissionError를 기록하고, sudo read-only로 크기81160 및 SHA256 `9c96f1363d5981d0c05013cef34e19ec5a4cb2eadfb378df6b18edefe034da21`만 수집했다. 원본은 반출하지 않았다. kernel/DT/overlay 설치·수정 없음.
- 현재 setfile/probe/profile/운영 binary·unit/drop-in·modprobe·module·DTBO 파일 metadata/hash, service properties, graph, 저장 register12행 형식을 조사했다. 기존 파일과 새 합성 bundle payload를 혼동하지 않았다. full live register/visual/CSI baseline은 아직 없다.
- 최종07:07:33 KST: RAW2 PID683775 active/enabled, NRestarts0. sequence는 마지막 관측에서 증가했고 buffers/s1021.589, raw bytes/s179472804.215, web58.976fps/HDMI59.976fps, reported dequeue/buffer/sequence-gap0. 파일·모듈 파라미터·graph·service·pending은 작업 전후 동일했다. 이는 해당 관측 범위의 보존 증거이지 CSI error-free/복구 성공 주장이 아니다.

## GO/NO-GO matrix

| Gate | 상태 | 남은 증거 |
|---|---|---|
| read-only inventory/tool identity | PASS_READONLY | 실제 live register·visual/CSI 별도 절차 필요 |
| isolated startup에서 destructive timer 미호출 | PASS_SANDBOX | 실제 production unit/start 통합은 미변경·미검증 |
| bundle 무결성/입력 거부 | PASS_SYNTHETIC | 실제 private bundle 생성·독립 봉인·완전한 dependency closure 미완료 |
| 독립 systemd watchdog 생존/취소/timeout | PASS_MARKER_ONLY | 복구 backend 연결·모든 장애 정책·실제 health/cancel 연동 미검증 |
| runtime re-probe/get_frame_desc/송수신 DT | NOT TESTED | non-production 장비의 안전한 통합 시험 필요 |
| 실제 restore-to-current-RAW2 backend | NOT IMPLEMENTED / NOT TESTED | legacy start/rollback을 배제한 backend 및 handover 검증 필요 |
| 실제 정상 영상/CSI·센서 readback | NOT TESTED | 별도 위험 평가·승인 필요 |
| Phase C 실기 및 RAW2 복구 | **NO-GO / BLOCKED** | 위 모든 hard gate + 명시적 GO sign-off 전까지 금지 |

private bundle/receiver binding 설계는 [PRIVATE_BUNDLE_SPEC_KO.md](./PRIVATE_BUNDLE_SPEC_KO.md), 실행 코드와 정확한 test 경로는 `experiments/event-readiness/README.md`에 있다. `--device` blocker 및 `production_ready=false`는 그대로다. readiness 준비 작업이 실제 센서 시험의 별도 승인을 대신하지 않는다.
