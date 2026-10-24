# RP5 Event DT 0x31 — 진행 기록 (업데이트 필수)

> 아래는 2026-10-21 기준 GitHub에서 확인 가능한 이력이다. Codex의 현재 로컬 작업 내용이나 RP5 실시간 상태를 자동 반영하지 않는다.
> 작업을 시작·재개할 때 [RUNBOOK](./RP5_EVENT_RUNBOOK_KO.md)과 이 파일을 확인한다. 실행 직후 실제 증거로 갱신한다.

## 현황

| 단계 | 상태 | 검증 근거/남은 작업 |
|---|---|---|
| Phase 1·2 — RP1 CFE / sensor 정적 분석 | **보고 완료** | [Draft PR #2](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/2) |
| Phase 3A — macOS C++ 코어 및 8 MiB 샘플 | **보고 완료** | [Draft PR #3](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/3); macOS arm64 빌드, complete frames 1557 / events 1469217, four-way fixed split hash match |
| Phase 3A — RP5 aarch64 네이티브 빌드 | **PASS / Gate A 통과** | 명시적 전송 승인 후 Pi GCC14.2 native 17건 통과; evidence/rp5-native-regressions-20261021.json |
| Phase 3A — randomized splits, malformed, wrap, EOF/discontinuity | **Pi native 17건 PASS** | experiments/event-offline/evidence/rp5-native-regressions-20261021.json; 17건 native PASS |
| Phase 3B — GREY/V4L2 experimental capture adapter | **mock22건 PASS / live BLOCKED** | Pi ASan/UBSan; 장치·버퍼·오류·cleanup 검증, engine --device 무조건 하드 차단 |
| Phase 3B — bounded receive/decode pipeline 및 Viewer | **오프라인 PASS** | Pi release + ASan/UBSan file/mock tests; 960×720 browser render 확인. live ioctl/CSI 미검증 |
| 별도 RAW2 restore 설계 | **dry-run/mock24건 PASS / live backend 없음** | firstboot 호출 관계·hash 확인 및 실패 시뮬레이션; 실제 복구 증명 아님 |
| Issue #7 startup/bundle readiness | **33건 로컬/Pi PASS / synthetic only** | source pin 일치; private live bundle 미생성·hardware backend 없음 |
| Issue #7 독립 watchdog | **실제 격리 unit5건 + SSH client 종료 PASS** | marker-only cgroup/취소/timeout 검증; 실제 복구 연동 미검증 |
| Phase 3C — 실제 RP5 Event DT 0x31 수신 | **BLOCKED / HARD HOLD** | 기존 rollback이 설정 삭제·서비스 disable·재부팅을 수행. 현재 RAW2용 복구/watchdog 미검증 |
| Phase 3D — RAW2 복구 확인 | **미실행 / 운영 보존 확인** | 모드 변경0회. 최종 active·sequence 증가·V4L2 오류0; 복구 시험 성공은 아님 |

## 다음 실행 항목

- [x] Codex 개발 브랜치·로컬/원격 상태와 기존 PR 코드·증거 확인.
- [x] 민수 SDK/샘플 접근·체크섬 및 Pi 전송 승인 확인(원본 Git 미포함).
- [x] RP5 native17건 PASS. 완료한 suite는 변경 사유 없이 반복하지 않음.
- [x] capture/decode·bounded queue·960×720 Viewer file 시험 및 adapter mock22건 PASS.
- [x] 별도 restore dry-run/mock24건 및 firstboot 호출 관계 확인. 기존 rollback 재사용 금지.
- [ ] **BLOCKED**: private live baseline·실제 복구 backend·safe startup/race·독립 watchdog 검증.
- [ ] **BLOCKED**: HARD HOLD 해제 및 운영 변경 명시 승인 전에는 실기/서비스 재시작 금지.
- [ ] 어떤 결과이든 RAW2 production 정상 복구를 증명하고 보고.

## 실행/인수인계 로그

### 2026-10-21 — 기본 문서 최초 생성

- 변경: `AGENTS.md` 및 `docs/event-dt31/` 문서로 계획·승인 경계·복구 필수 항목 정리.
- GitHub 코드·기기/커널/센서 설정은 이 문서 PR에서 변경하지 않음.
- 담당 Codex는 아래 새 기록을 **실행한 뒤** append하고 커밋할 것.

### 다음 기록 템플릿

```markdown
### YYYY-MM-DD HH:MM KST — Phase ...
- Branch / commit:
- Host / kernel / device (if observed):
- Commands actually executed:
- Artifacts / log paths and checksums:
- Measurements: frame count, event count, bytes/s, seq gaps, CSI errors, CPU/RAM/queue
- Pass / Fail / Not-tested:
- Production touched? Yes/No. Backup / rollback state:
- Blockers or uncertainties:
- Exact next safe action:
```

### 2026-10-21 22:38 KST — Phase A 재개: 로컬 회귀 통과, native 전송 차단
- Branch: `codex/rp5-event-phases-20261021`; 시작 commit `18b78b6`. `git fetch origin` 및 기존 offline 브랜치 fast-forward 완료. AGENTS/runbook/progress와 PR #2 보고서 및 PR #3 코드·results.json을 실제 읽었다. main 직접 변경 없음.
- SSH 관측: `philip@192.168.0.177`, PhilipRP5, Debian 13.2, aarch64, kernel `6.12.47+rpt-rpi-2712`, GCC 14.2.0, Python3 있음, clang++ 없음. /home 여유 약 5.0 GiB, /tmp 약 4.0 GiB. SSH 읽기 전용 조사 성공. 조사 범위의 /home/philip maxdepth4 검색에서는 이번 민수 SDK/샘플을 확인하지 못함(전체 파일시스템 부재를 단정하지 않음).
- 승인된 로컬 package/sample checksum을 기존 보고와 대조해 일치 확인: tar SHA256 `3e7bc2c35d8860fda70879ced04dcea9edbc7ff7daa3f41dcc44c94b2b9946b6`, sample SHA256 `962925dfaf87fcd1a16d04cd6e122d32558527b543f39acc2803926f2fc897b3`.
- 신규 코드: `prepare_core.py`는 임시 SDK 코어에 checked-anchor carry/reset/EOF partial-byte 및 incomplete-frame 통계를 적용한다. `phase_a.py`는 g++/CXX 네이티브 빌드 경로 및 17개 회귀시험을 제공한다. replay.cpp에 고정 seed 랜덤 chunk, 명시 gap offset, 확장 stats 지원 추가. 민수 원문/샘플/레지스터/바이너리는 Git에 넣지 않음.
- 실제 로컬 명령: `CXX=clang++ python3 experiments/event-offline/phase_a.py /private/tmp/dvs-event-audit/nrv-dvs-jetson-20261014/nrv-dvs-jetson/sdk /private/tmp/dvs-event-sample.bin /private/tmp/rp5-event-upload/local-new-regressions.json`.
- 결과: macOS arm64 clang C++20 코어 빌드 및 17건 PASS. fixed 1/4/4093/1048576 + random seed 20261021 분할, frame255→0 및 timestamp wrap(period 200us), CID 분리, 1/2/3 EOF 잔여 바이트, 미완성 Frame End, invalid x/y/sub timestamp, unknown/malformed word, gap 뒤 context/carry reset 및 재동기화. sample 완성 프레임 1557 / events 1469217 / invalid=unknown=frame_gaps=0; 5개 분할 출력 SHA256 `e15a8a75899f6352725e0a4fbcd73f537acd1496fda6ae8ac25cd17903be1798`. 이전 macOS 결과를 새 native 결과로 재사용하지 않음. fixed splits는 새 EOF/reset 계측이 기존 출력을 보존하는지 확인하는 regression 용도로 실행.
- 증거: `experiments/event-offline/evidence/local-regressions-20261021.json` (실제 compiler/platform/input hashes/각 실행 카운터). 이는 Pi 결과가 아님. source ABI 프레임 해시의 플랫폼 간 재현 여부도 native에서 확인 필요.
- 실패/차단: `scp /private/tmp/rp5-event-upload/phase-a.tar.gz philip@192.168.0.177:/tmp/dvs-event-phase-a-20261021.tar.gz`가 자동 승인 검토에서 실행 전 거절됨. 사유: 비공개 SDK 소스와 민감 샘플의 정확한 payload·remote destination에 대한 승인이 명확하지 않음. 우회 전송하지 않았다. 사용자에게 해당 자료를 이 Pi 임시 실험 경로로 전송하는 명시적 승인 필요. native build/tests는 NOT RUN; Gate A 미통과, Phase B/C/D 진행하지 않음.
- Production touched: No. 서비스 MainPID=683775, NRestarts=0, ActiveState=active 유지. 마지막 2초 관측 sequence 106088021→106089668. buffers/s 1062.604→825.887, raw bytes/s 186678203.057→145091870.607, web 약58fps, HDMI 약60fps. dequeue/buffer/sequence-gap errors 각각 0. 시각 영상 baseline이나 CSI error baseline은 미확보이며 Phase C preflight PASS로 해석하지 않음.
- 중단/복구: 실기 캡처 0회, 운영 중단 0초, 센서/모듈/서비스 설정 쓰기 없음. 변경이 없어 복구 명령 실행 없음. RAW2 복구 시험 성공을 주장하지 않음.
- 다음 안전 작업: 명시적 전송 승인 후, private SDK core/sample + public harness만 Pi 별도 디렉터리에 전송하고 source/sample hash 대조 → GCC C++20 native 17건 실행 → Gate A 판정·commit/push. 이후에만 Phase B. Phase C의 10초×최대3회/총 downtime15분 및 preflight/watchdog/복구 검증 조건은 그대로 적용.

### 2026-10-21 — Phase A 완료: RP5 native Gate A PASS
- 사용자에게서 private SDK core + 8MiB sample의 해당 Pi /tmp 전송에 대한 명시 승인 수신. scp 성공. 원격 경로 `/tmp/dvs-event-phase-a-20261021`, umask077. Production 변경 없음.
- 실제 명령: `nice -n 10 python3 phase_a.py sdk sample.bin native-results.json` (Pi). GCC14.2 / Linux aarch64 / kernel 6.12.47+rpt-rpi-2712. sample SHA256 기존과 일치. 17건 모두 PASS; fixed/random 분할 5건에서 frames1557/events1469217, invalid/unknown/frame_gaps0, 출력 hash 기존과 동일. 각 synthetic case의 실제 카운터는 `experiments/event-offline/evidence/rp5-native-regressions-20261021.json`에 보존.
- 모듈 읽기 전용 확인: rp1-cfe.ko SHA256 `0d09dbeaee5fda45bc3e24407254d19dd454c2f4fbb2a26c356b93bf47bfa3dd`, s5krc1s_min.ko `474d02b06165804310e91ee16dca70de691664f1b806783e3f4eda2dd6584153`, 보관 baseline과 일치. parameter DT42/link625MHz. 서비스 active. sudo -n 권한 확인 성공. rollback/validate 파일 존재만 확인했으며 실행 검증은 아직 아님.
- Gate A PASS. 실기 캡처0회/다운타임0초. 다음: Phase B bounded capture/decode pipeline + GREY adapter + 960×720 Viewer를 파일/mock로 검증. Phase C preflight는 아직 PASS 아님.

### 2026-10-21 22:58 KST — Phase B 오프라인 완료
- Branch `codex/rp5-event-phases-20261021`, Phase A commit `eec32b1` 이후. Pi 실험 경로 `/tmp/dvs-event-phase-b-20261021`. Production 장치 open/STREAMON 0회, 서비스/센서/모듈 변경 없음.
- 신규 `experiments/event-engine/`: C++ capture thread → bounded queue → decode(main) thread, file backpressure/live oldest-drop + gap, bounded MMAP GREY adapter 및 strict driver/card/bus 검사, 10초 cap, 종료 RAII. 960×720 PPM snapshot + canvas Viewer, byte/buffer/event/CPU/queue/decoder/CID/Frame End word 통계와 per-buffer CSV. CSI FS/FE/CRC/ECC는 미측정 null로 유지.
- 첫 `gate-1` 실패: metrics.json의 error 문자열 opening quote 누락 → JSONDecodeError. misleading-indentation 경고도 발견. 양쪽 수정 후 gate-2 통과. Frame End word 독립 계측과 fail-closed active-production 검사 보강 후 gate-3 release 최종 통과. 실패 로그는 Pi `gate-1.log`에 남겨 두었다.
- 최종 실제 명령: `nice -n 10 python3 /tmp/dvs-event-phase-b-20261021/event-engine/gate_b.py /tmp/dvs-event-phase-a-20261021/sdk /tmp/dvs-event-phase-a-20261021/sample.bin /tmp/dvs-event-phase-b-20261021/gate-3`; 동일 입력을 새 output `gate-asan --sanitize`로 native ASan/UBSan 검증. GCC14.2 C++20, -Wall -Wextra -Werror. SDK object 6개를 먼저 컴파일하고 engine/queue-test 각각 링크; 결과 JSON의 build_command는 동등한 monolithic 명령임을 주석으로 구분.
- release 파일 재생 실측: 8,388,608bytes / 2050 input buffers / 1557 complete frames / 1469217 events, elapsed1.04236s, process CPU103.569%, queue capacity8/high8/drop0/final0. 이는 **파일·Viewer·쓰기 포함 replay 수치**이며 센서 전송 성능이 아니다. 느린 소비자(cap1/delay2ms) elapsed4.68909s, CPU26.6108%, high1/drop0, 동일 frames/events/hash.
- 별도 counter: valid sensor Frame End words1558(CID0 1558), output frames1557; on706157/off763060/CID1events0; unsynced_groups830; invalid/unknown/frame_gaps0; EOF incomplete_frames1/partial_bytes0. 이 경계 관측으로 물리 센서 손실 유무를 단정하지 않는다.
- 큐 유닛: cap2/cap1 oldest drop 뒤 gap 표시, blocked producer stop/wakeup PASS. SIGTERM 종료 bound5초 PASS(실제 약0.509s 실행 후 interrupted 기록, 미소비 queue1은 기록 후 프로세스 종료). missing-input 오류 반환 PASS. active production일 때 nonexistent device path를 넣어 **open 이전 실행 거부** PASS.
- ASan/UBSan: 모든 위 gate PASS, 진단 오류 없음. release와 slow-consumer 모두 출력 hash Gate A와 일치. sanitized 속도는 계측 overhead가 있어 성능 평가에 사용하지 않는다.
- Viewer: Pi가 생성한 private PPM을 로컬 /private/tmp에만 회수하고 loopback8873에서 canvas 렌더 시각 확인. 960×720 ON green/OFF red 점 표시 확인. 영상/스크린샷/샘플은 Git에 넣지 않았으며 임시 서버·탭 종료. live HDMI 검증 아님.
- 증거: `experiments/event-engine/evidence/rp5-file-gate-b-20261021.json`, `rp5-asan-gate-b-20261021.json`; 원본 로그 Pi `gate-3.log`, `gate-asan.log`, 출력/원본 로그 삭제 없음.
- Gate B software/file/mock PASS. 실제 ioctl fault-injection/수신/CSI와 하드웨어 Viewer는 미검증. 다음 Phase C preflight에서 복구의 확실성을 판정해야 하며 실기 성공으로 간주하지 않는다.

### 2026-10-21 22:59 KST — Phase C preflight STOP, RAW2 운영 보존
- Phase A/B 완료 기록 push 후 C preflight 판정. 기존 rollback/validate를 실행 없이 읽었다. rollback이 RP1 override·production modprobe 삭제/서비스 disable/모듈 파일 변경/재부팅으로 reference-B3를 복원함을 확인했다. 현재 RAW2 원복과 다르며 승인 범위 밖 동작을 포함한다. 대체 무재부팅 복구·독립 watchdog dry-run도 미검증이므로 runbook STOP을 적용.
- 근거와 체크리스트/재개 요건: `docs/event-dt31/RECOVERY_PREFLIGHT_KO.md`. sensor setfile/geometry/current-state full backup/정상 시각 baseline 등도 아직 PASS가 아니며 기존 파일을 임의 적용하지 않았다.
- 최종 읽기 전용 관측(22:59:22 KST): MainPID683775/NRestarts0/active; sequence107291681→107293804(약2초); buffers/s847.929→1146.751, raw bytes/s148964165.448→201461218.942, web57.927→57.987fps/HDMI59.924→59.987fps. dequeue/buffer/sequence-gap errors 각각0. CSI debugfs 읽기/센서 I2C 명령0회.
- 증거: `docs/event-dt31/evidence/raw2-preserved-20261021.json` 실제 최종 지표 및 rollback/validate hash. RAW2 preserved=Yes; restored-after-event=NOT TESTED.
- 실기 DT0x31 capture0회/서비스 stop0회/모듈·DT·register 변경0회/downtime0초/재부팅0회. production 복구 명령은 변경이 없어 실행하지 않았다. private SDK·샘플은 승인된 Pi /tmp에만 저장하고 원본 로그/출력 보존; local review HTTP 서버 종료.
- 다음 작업은 실기 재시도가 아니다. 현재 RAW2용 무재부팅 복구안·watchdog dry-run 검증을 먼저 마련하고 STOP 원인을 해소해야 한다. 사용자에게 현 실패를 보고하며, C/D 성공이나 최종 목표 달성으로 표시하지 않는다.

### 2026-10-21 — 안전 차단: 기존 rollback.sh는 RAW2 복구가 아님
- Codex 현장 조사의 보고에 따르면 기존 `raw2_production_rollback.sh`는 RP1 override 삭제·RAW2 서비스 비활성화·재부팅을 수행한다. Event Packet 실험 복구용으로 절대 실행·예약·재사용하지 않는다. GitHub에서는 실제 Pi rollback 스크립트 원문을 직접 확인하지 못했으므로 현장 호출 관계 분석 결과를 추후 첨부할 것.
- GitHub main의 [PR #6](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/6)에서 AGENTS 및 RUNBOOK의 **Phase C HARD STOP**을 명시. RAW2 시작 스크립트 자체도 센서 setfile·레지스터·media graph 수정 및 pending-first-boot rollback 타이머 가능성이 있어 `systemctl restart`를 단순 dry-run으로 취급하지 않는다.
- Phase A Gate PASS 기록과 지금까지의 실행 결과는 그대로 보존. Phase B file/mock 기능과 별도 restore-to-current-RAW2 계획·mock 실패 시험만 계속 수행한다. 실제 운영 중단/센서 I2C 쓰기/드라이버 reload/rebind/DT override 변경/재부팅은 복구 경로 검증 전까지 금지.
- 증거가 없는 복구 성공 판정 금지. 운영 서비스를 건드리지 않은 mock PASS는 실제 RAW2 복원 성공을 뜻하지 않는다. 다음 Codex 작업에서는 실제 조사 증거, 위험한 호출 경로, 독립 watchdog의 안전성, 복구 검증을 PROGRESS에 append할 것.

### 2026-10-21 — Phase B 남은 어댑터 mock 검증 / 실기 코드 HARD HOLD
- 사용자 최신 지시와 origin `83dab0f`(PR #6 hard stop 문서 sync)를 반영. 기존 native file/queue/decode/Viewer 및 ASan 결과는 보존하고 동일 샘플 suite를 다시 실행하지 않았다.
- 새 `v4l2_mock_test.cpp`는 open/close/ioctl/mmap/munmap/poll을 모두 fake 함수로 치환하여 실제 장치0open으로 adapter만 검증. GREY/stride/capability/정확한bus/버퍼 수/size/bytesused/index, setup·requeue·STREAMON 실패, poll timeout/error/EINTR, DQBUF EAGAIN/EINTR, driver-error 및 부분 mmap 후 cleanup을 포함해 **22건 Pi ASan/UBSan PASS**.
- 발견·보완: unterminated capability 문자열은 bounded length로 비교, 요청0 geometry 및 empty bytesused를 거부하도록 보강. 큐·decode·Viewer file 처리 경로는 바꾸지 않음.
- 실험 engine은 이제 유효한 --device 명령도 **PHASE_C_BLOCKED**로 systemctl/device open/output 생성 전에 거부한다. 실제 Pi에서 가짜 nonexistent path로 exit1과 output 미생성 확인. gate_b.py의 future regression assertion도 해당 hard-hold 메시지로 갱신.
- 명령: Pi `/tmp/rp5-restore-offline-20261021`에서 `g++ -std=c++20 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer experiments/event-engine/v4l2_mock_test.cpp -o adapter-mock` → `./adapter-mock`. 별도로 engine-hard-hold를 GCC14.2/C++20로 링크하고 CLI 거부 시험. 기존 SDK objects를 재사용했으며 decoder regression 완료 단계를 재수행하지 않음.
- 증거: `experiments/event-engine/evidence/rp5-adapter-mock-20261021.json`, `rp5-hard-hold-20261021.json`. 기존 release/ASan file evidence 유지. hardware ioctl 및 실제 복구 성공이 아닌 mock 검증임.
- 운영 stop/restart/센서·I2C·모듈·DT·media graph 변경0회. 다음은 별도 restore 계획·mock 결과·호출 관계 기록이며 Phase C는 BLOCKED 유지.

### 2026-10-21 23:14 KST — restore 설계·dry-run·실패 시뮬레이션 완료 / Phase C BLOCKED
- 기존 rollback/start/validate/installer/systemd/firstboot 전체 파일과 관련 참조를 읽기 전용 분석. start56–58행은 pending 시 커널/모듈 검사보다 먼저 4분 destructive rollback timer를 생성; start142–143행은 validate 실행. validate 성공 시 marker/timer 정리, 실패 시 timer 유지. 서비스 Restart=on-failure/5s이며 installer가 marker를 생성하고 reboot함. 기존 스크립트 실행·수정·예약 없음.
- 현재 pending absent, expiry timer/service not-found/inactive. camera-root-watchdog timer는 disabled/inactive이며 script에 legacy restart 및 force-reboot 경로가 있어 새 watchdog으로 재사용하지 않음. system timer10/user timer0 관측. 조사 범위 밖의 모든 외부 호출 부재는 증명하지 않음.
- module/source/binary/config/DT/unit/drop-in/setfile/probe/profile/register-record/server/Python/tool 존재·해시 확인. DT42/link625MHz/pack1/strideY. 실제 RP1 sysfs parameter는 diag_pack_bytes/diag_stride_zero/verbose_debug만 관측되어 CSI error tracking을 확인했다고 주장하지 않음.
- 저장 레지스터 기록12행과 기존 startup assertion의 일치 여부만 검사(PASS); mtime2026-10-20 20:30:47. 현재 센서 I2C 값 검증 아님. 원문 setfile/레지스터 값은 Git에 포함하지 않음.
- 새 `experiments/event-restore/restore_current_raw2.py`: observed JSON read-only dry-run + OS temp sentinel fixture mock. pinned module/start/binary/DTBO hash 및 수신 파라미터 체크. 실제 systemd/I2C/module/shell backend와 live apply 옵션은 없음. 기존 rollback/start를 호출하지 않으며 mock action은 JSON state transition일 뿐. hardware readiness는 항상false, dry-run exit2가 정상 차단 결과.
- 최종 `test_restore.py` 24건 local/Pi PASS(초기21건 이후 hash/DT검사3건 추가). 복원 실패(sensor), 서비스 start 실패, sequence 정지/오류 증가/영상 실패, pending/timer 충돌·race, kernel/hash/enable-state drift, watchdog 미준비, deadline injection, 중복실행 lock, 멱등성, dry-run 무변경, production root/live-mode 거부. 실패 시 fake watchdog flag와 오류 증거 유지/수동 개입 표시; reboot/disable/delete fallback 없음.
- SSH 단절은 실제 접속을 끊지 않고 짧은 수명의 mock client가 독립session worker를 남긴 뒤 종료하는 방식으로 모사. 성공했으나 real SSH/logind/systemd cgroup 생존 검증은 아니며 fake armed flag가 실제 daemon 가동 증명도 아님. 실제 서비스 start 및 센서 쓰기로 시험하지 않았음.
- 명령: 로컬/Pi `python3 experiments/event-restore/test_restore.py --results <aggregate-json>`; 로컬 `python3 experiments/event-restore/restore_current_raw2.py --dry-run <readonly-inventory-json>`(exit2). Pi 작업 경로 `/tmp/rp5-restore-offline-20261021`. 기존file/queue/decoder/Viewer nativePASS 증거 보존.
- 증거: `experiments/event-restore/evidence/rp5-readonly-inventory-20261021.json`, `rp5-readonly-extra-20261021.json`, `recorded-register-check-20261021.json`, `dry-run-20261021.json`, `local-mock-v2-20261021.json`, `rp5-mock-v2-20261021.json`. 초기21건 결과도 보존.
- 전후 불변성 최종23:14:28: 점검 파일 metadata/hash 전부 동일, module parameters/graph hash 동일. PID683775/NRestarts0/active/enabled; sequence108187229→108189432; dequeue/buffer/sequence-gap errors0, web약58/HDMI약60fps. `rp5-after-invariants-20261021.json`에 보존.
- [상세 보고서](./RESTORE_PLAN_KO.md)에 위험한 호출 그래프, 별도 절차, 검증 한계, TOCTOU 및 남은 blockers 정리. RUNBOOK §8과 engine code 모두 Phase C BLOCKED 유지. 실제 복구 backend·완전한 private baseline/live register·정상 영상/CSI·safe startup·새 watchdog·실기 복구 검증 없이는 HOLD 해제 금지.
- 운영 서비스 stop/restart0회, I2C 읽기/쓰기0회, module/DT/media graph 변경0회, 기존 rollback 수정/실행/예약0회, 실기capture0회/downtime0초. 이번 mock PASS는 실제 RAW2 복원 성공이 아니다.

### 2026-10-22 — Issue #7 / PR #5 최신 지침 재개: 신규 readiness 검증
- `git fetch origin`; 시작/PR head `58327b82e637feeda74eeb7bf98dc614e83bbf05`. Issue #7 본문(댓글0), PR #5 최신 source review/handoff 댓글 및 AGENTS/RUNBOOK/RESTORE_PLAN/PROGRESS·기존 PR #2/#3 실제 코드/증거 확인. 이전 17/22/24건 증거 보존. 현재 단계는 live 실행이 아니라 GO/NO-GO readiness.
- 새 `experiments/event-readiness`: 외부 manifest SHA pin, 상대경로/O_NOFOLLOW, 파일 hash·12행 register 형식, setfile 필수, target DT/geometry 검증; readonly synthetic bundle fixture와 hardware backend 없는 isolated startup. marker check 직후·stage 중 생성, concurrent installer/service restart, 동시 controller lock, bundle drift/경로·schema·legacy command injection, fake prior success 거부 포함 **최종33건 로컬/Pi PASS**. 앞선31/32건 결과와 source hash도 증거에서 구분. 최종 양 호스트의 소스 hash를 Git 파일과 대조 예정.
- 별도 실제 manager-owned **marker-only systemd watchdog** 검증 수행. `rp5-dvs-rdy-<unique>-*.service` transient/collect unit만 새로 만들었으며 User/Group=philip, ProtectSystem=strict, ProtectHome, PrivateDevices/Network, NoNewPrivileges, DevicePolicy=closed, ReadWritePaths=자기tmp, RuntimeMaxSec/CPU/메모리 제한 적용. 기존 RAW2/legacy watchdog은 호출하지 않음.
- 최초unit 실패: strict readonly /tmp 상위에서 Python tempfile.gettempdir()가 쓰기 probe를 하다 실패. 초기 자체 journal 보존. 보호 설정은 완화하지 않고 Linux tmp 경로 검증을 무쓰기 방식으로 수정했다. 추가로 malformed cancel token 타입이 예외를 유발할 수 있음을 코드검토에서 확인해 타입검사를 추가하고 별도 negative case로 재검증.
- 최종 systemd5건 PASS: deadline→NOOP marker, 정상 nonce+run+mock proof 취소, 잘못된 token 무시, 잘못된 JSON token 타입 무시, RuntimeMaxSec에 의한 SIGTERM→NOOP alert. PID1 parent/별도 system.slice cgroup/실제 보호 속성 및 worker source pin 확인. systemd 자체 timeout journal도 보존. marker-only이며 실제 복구나 센서 동작은 하지 않음.
- 새 시험 전용 SSH client 하나만 종료한 후 새 SSH query로 result가 아직 없음을 확인하고, 이후 manager unit이 NOOP 결과를 생성함을 검증(PASS). worker cgroup은 query SSH session과 다름. 네트워크 단절/sshd 재시작/모든 logind 정책/하드웨어 복구 시험은 **NOT TESTED**. 기존 mock boolean과 구분한다.
- 파일 입력 우회도 검토: --device hard-block 유지. 새 RegularInput은 O_PATH inode 고정 후 일반 ext-family/tmpfs만 읽기 open하고 symlink/FIFO/directory/proc·sys 가상파일을 거부한다. 타입·변조7건 및 최종 엔진6개 음성/CLI guard를 Pi ASan/UBSan에서 PASS. 취득부가 바뀌었으므로 샘플 출력hash만 재대조: frames1557/events1469217/기존 hash 일치. 기존 decoder 전체 suite를 반복하지 않음.
- 실행/증거: `python3 experiments/event-readiness/test_readiness.py --results <json>`(로컬/Pi33건), Pi `systemd_sandbox_gate.py --work /tmp/dvs-watchdog-gate-20261022-v3`(실제 격리unit5건), 로컬 `test_ssh_exit.py --results <json>`(시험소유 SSH client 종료), C++7건 및 `test_engine_guards.py`(ASan). Pi workspace `/tmp/dvs-readiness-20261022`, `/tmp/dvs-fileguards-20261022`. 집계 결과는 `experiments/event-readiness/evidence/`에 저장. Python suite는 sanitizer 대상 아님; ASan/UBSan은 C++ file guard/engine에 적용.
- 읽기 전용 inventory: 실제 i2ctransfer는 `/usr/sbin/i2ctransfer`(`/sbin`도 같은 resolve), SHA256 `94dd49d676021518cda6aa0c4997bc5cd71bf04fea39216e57cbe71861b7c855`; `/usr/bin` 부재를 전체 부재로 해석하지 않음. 실행0회. kernel6.12.47, 양 loaded module srcversion이 modinfo 파일값과 일치. live FDT는 일반 사용자 PermissionError를 명시 후 sudo read-only SHA만 확인(원문 미반출). 현재 sensor register readback/CSI·정상 영상 baseline은 여전히 NOT TESTED.
- 중간 전후 invariant 07:01:22 KST PASS: 점검 파일/module parameters/media/service/pending 동일; RAW2 PID683775 active/enabled, NRestarts0, sequence 증가, reported V4L2 dequeue/buffer/sequence-gap0. 최종 unit/source 정리·추가 전후 확인은 후속 기록에 명시.
- Phase C HARD BLOCKED / production_ready=false. 실제 복구 backend·현재 레지스터/영상/CSI·기존 production startup의 firstboot race 통합·복구 watchdog 연결은 미검증. 신규unit은 자기 tmp marker만 쓰고 자동 collect했으며 운영 서비스 stop/restart·I2C·module/DT/media 변경·legacy rollback 호출0회.

### 2026-10-22 07:07 KST — Issue #7 readiness 최종 NO-GO 기록
- [READINESS_20261022_KO.md](./READINESS_20261022_KO.md)에 최종 GO/NO-GO matrix 및 실제 측정/한계를 기록. [PRIVATE_BUNDLE_SPEC_KO.md](./PRIVATE_BUNDLE_SPEC_KO.md)에 private 불변 bundle 설계와 module re-probe/get_frame_desc DT binding 계획을 명시. 실제 private bundle을 생성·봉인했다고 보고하지 않음. loaded srcversion 일치는 receiver descriptor/sensor 송신 DT 실측을 대신하지 않음.
- 최종33건 양 host/current Git source SHA 일치. 실제 systemd5건 및 SSH client 종료 unit의 ready.source_sha256도 최종worker와 일치 확인. 초기실패/31/32건 자료는 historical evidence로 보존하며 최종 coverage에 중복 가산하지 않음.
- 실제 unit5건 결과: expiry FIRED_NOOP1.2225s, valid cancel CANCELLED0.0562s, bad token FIRED_NOOP1.2205s, malformed token FIRED_NOOP1.2112s, manager RuntimeMaxSec3s→SIGTERM/TERMINATED_NOOP(worker elapsed2.5853s; unit startup시간과 구분). PID1 parent·별도 system.slice cgroup과 보호 속성 확인. 종료/취소 인증은 synthetic proof로만 시험. 실제 restore health 연동은 NOT TESTED.
- SSH 테스트는 이번 시험이 만든 client PID만 종료(return255)하고 새query 시 result가 아직 없음을 본 후 독립unit 결과생성을 확인. 기존 sshd/다른 SSH/네트워크는 변경하지 않았다. 실제 네트워크 단절·모든 logind·복구 backend 실행은 NOT TESTED.
- 새 file mode는 O_PATH inode pin 후 ext-family/tmpfs regular file만 읽기 open; proc/sysfs류·FIFO·symlink·directory·변조 거부. 최종 CPP7건/engine6guard ASan/UBSan PASS. 입력 구현이 변경됐기 때문에 승인 샘플 output hash만 재확인했으며 frames1557/events1469217 유지. legacy decoder를 수정하지 않음.
- 최종 운영 불변성07:07:33 KST PASS: 모든 조사 파일 hash/metadata, module parameters, media graph, service 및 pending 상태가 전후 동일. MainPID683775/NRestarts0/active/enabled; sequence 증가, buffers/s1021.589, raw bytes/s179472804.215, web58.976/HDMI59.976fps, reported V4L2 dequeue/buffer/sequence-gap0. CSI error-free로 해석하지 않음. 별도 transient test unit0개 남음. 증거 `rp5-inventory-final-20261022.json`, `rp5-invariants-final-20261022.json`, `rp5-watchdog-cleanup-final-20261022.txt`.
- 작업 중 생성한 것은 공개 readiness 코드, 합성 fixture 및 별도 marker-only temporary units뿐. RAW2 stop/restart0, I2C invocation0, sensor/module/DT/media writes0, legacy scripts/watchdog 실행0, 실기capture0, production downtime0초.
- 최종 판정 **NO-GO / Phase C HARD BLOCKED**. 현재production startup은 여전히 기존 경합 경로이며 변경하지 않음. 실제 backend/private live registers/정상 영상·CSI/안전 startup handover/실제복구와 watchdog 연동/GO sign-off가 미충족. Issue #7은 readiness report와 nonproduction harness 결과로 보고하고 실기 단계로 넘어가지 않는다.

## 2026-10-25 — Issue7 재확인 / watchdog request 강화 / NO-GO 유지

- origin fetch, AGENTS/RUNBOOK/기존 evidence 및 Issue7/PR5 최신 discussion 확인. 새 지침 없음. 기존 브랜치와 완료 결과 보존.
- Pi readonly inventory 05:42:02 KST: RAW2 active/enabled/PID683775/NRestarts0, sequence425660338→425662660, capture1128.176buffers/s, reported dequeue/buffer/sequence-gap0. pending absent/firstboot inactive. 10월22일 검사 파일 metadata/hash·params·media 요약 동일. 현재 정상 영상/CSI/I2C readback은 NOT TESTED.
- `watchdog_worker.py`: strict JSON type/identity/finite deadline 및 ready/result 재사용 거부. 시작 전 cancel까지 거부한 초기 구현이 기존33건 회귀에서 실패하여 수정했다.
- 신규 `test_watchdog_request.py` 로컬/Pi22 PASS, 기존 readiness 로컬/Pi33 PASS. 명령/실측/실패와 한계는 [10월25일 보고서](./READINESS_20261025_KO.md). 증거 `experiments/event-readiness/evidence/*20261025.json`. Python/temp 프로세스 시험이며 이번 worker의 systemd/SSH 재시험은 NOT TESTED. 이전 독립 unit 증거는 이전 source pin 범위로만 보존.
- production 변경0, I2C0, legacy rollback/start/validate 호출0. live backend와 private baseline/startup 통합/실기 복구 미검증이므로 Phase C HARD BLOCKED/NO-GO 유지. 다음 작업: 비운영 복구 backend와 health/cancel 연동 설계·실패 주입. 실제 장비 전환 금지.
