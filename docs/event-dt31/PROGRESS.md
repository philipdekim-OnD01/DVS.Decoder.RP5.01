# RP5 Event DT 0x31 — 진행 기록 (업데이트 필수)

> 아래는 2026-10-21 기준 GitHub에서 확인 가능한 이력이다. Codex의 현재 로컬 작업 내용이나 RP5 실시간 상태를 자동 반영하지 않는다.
> 작업을 시작·재개할 때 [RUNBOOK](./RP5_EVENT_RUNBOOK_KO.md)과 이 파일을 확인한다. 실행 직후 실제 증거로 갱신한다.

## 현황

| 단계 | 상태 | 검증 근거/남은 작업 |
|---|---|---|
| Phase 1·2 — RP1 CFE / sensor 정적 분석 | **보고 완료** | [Draft PR #2](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/2) |
| Phase 3A — macOS C++ 코어 및 8 MiB 샘플 | **보고 완료** | [Draft PR #3](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/3); macOS arm64 빌드, complete frames 1557 / events 1469217, four-way fixed split hash match |
| Phase 3A — RP5 aarch64 네이티브 빌드 | **PASS / Gate A 통과** | 명시적 전송 승인 후 Pi GCC14.2 native 17건 통과; evidence/rp5-native-regressions-20261021.json |
| Phase 3A — randomized splits, malformed, wrap, EOF/discontinuity | **Pi native 17건 PASS** | experiments/event-offline/evidence/local-regressions-20261021.json; native 실행 필요 |
| Phase 3B — GREY/V4L2 experimental capture adapter | **미완료** | 오프라인 mock/fake producer 우선 |
| Phase 3B — bounded receive/decode pipeline 및 Viewer | **미완료** | 상태 계측 및 정상 종료 시험 필요 |
| Phase 3C — 실제 RP5 Event DT 0x31 수신 | **미실행** | preflight·rollback 통과 후 제한된 실험 |
| Phase 3D — RAW2 복구 확인 | **대기** | 실험 시작 시 반드시 검증 |

## 다음 실행 항목

- [ ] Codex 작업 브랜치, 로컬 상태 및 현재 PR #2·#3 HEAD 재검사.
- [ ] 민수 SDK/샘플의 승인된 접근 경로와 체크섬 재검증(원본 Git 커밋 금지).
- [ ] RP5 네이티브 코어 빌드·저장 샘플 재생·랜덤 split·잘린 EOF 회귀 시험.
- [ ] 독립 capture/decode 구조의 mock 테스트, queue metrics 구현.
- [ ] 실제 센서 변경 이전 preflight + 자동 rollback의 dry-run 증거 확보.
- [ ] 실기 시험은 runbook 내 명시된 제한과 stop condition을 모두 통과하는 경우에만.
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
