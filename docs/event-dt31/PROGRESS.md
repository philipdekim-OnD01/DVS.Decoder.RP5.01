# RP5 Event DT 0x31 — 진행 기록 (업데이트 필수)

> 아래는 2026-10-21 기준 GitHub에서 확인 가능한 이력이다. Codex의 현재 로컬 작업 내용이나 RP5 실시간 상태를 자동 반영하지 않는다.
> 작업을 시작·재개할 때 [RUNBOOK](./RP5_EVENT_RUNBOOK_KO.md)과 이 파일을 확인한다. 실행 직후 실제 증거로 갱신한다.

## 현황

| 단계 | 상태 | 검증 근거/남은 작업 |
|---|---|---|
| Phase 1·2 — RP1 CFE / sensor 정적 분석 | **보고 완료** | [Draft PR #2](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/2) |
| Phase 3A — macOS C++ 코어 및 8 MiB 샘플 | **보고 완료** | [Draft PR #3](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/3); macOS arm64 빌드, complete frames 1557 / events 1469217, four-way fixed split hash match |
| Phase 3A — RP5 aarch64 네이티브 빌드 | **미확인** | 빌드 및 샘플 재생 기록 필요 |
| Phase 3A — randomized splits, malformed, wrap, EOF/discontinuity | **미완료/미확인** | 추가 regression tests 필요 |
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

## 2026-10-21 안전 차단 공지 — Gate C BLOCKED (Codex 현장 조사 보고)

- Codex가 보고한 문제: Pi의 기존 `raw2_production_rollback.sh`는 RAW2 원상복구 대신 RP1 override 삭제·서비스 비활성화·재부팅 수행. 이 스크립트를 Event Packet 복구 수단으로 **사용 금지**. 전체 현장 스크립트는 별도로 읽기 전용 검증 필요.
- 저장소에 보관된 `raw2_production_start.sh`는 센서 레지스터·media graph를 직접 변경하고 `pending_first_boot_validation` 존재 시 기존 rollback 타이머를 등록함. 운영 `systemctl restart`를 harmless dry-run으로 처리 금지.
- Phase B: 파일/mock을 이용한 개발과 mock/읽기 전용 복구 경로 조사만 허용. Phase C: 자동 복구 경로의 실증 가능한 검증 전까지 **BLOCKED**, 운영 중단/센서 쓰기 금지.
- PR #5가 Pi ARM64 17건 통과(Gate A PASS)를 기록함. 이 프로젝트 주 브랜치 진행 로그는 PR #5 개발 브랜치와 동기화가 필요하며, 17건 PASS는 live MIPI 실험 완료를 의미하지 않음.
- 정지 해제 조건: 별도 restore-to-current-RAW2 절차, 실제 환경 snapshot, 기존 rollback 경로 완전 배제, 독립 watchdog 및 실패 모드 mock 테스트, 운영 영향·복원 검증 계획, 미해결 복구 위험 해소. 실제 다운타임 없이 dry-run을 통과한 것만으로 복구 성공 판정 금지.

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
