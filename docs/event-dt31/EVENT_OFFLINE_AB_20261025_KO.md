# Issue11 Event 오프라인 A/B — 진행 보고

## P0 환경·출처 고정

main AGENTS f7f9492 및 Issue11/최신 댓글, 개발 PROGRESS를 확인했다. main의 과거 PhaseA 미확인 표는 PR5의 실제 native17/evidence보다 오래된 기록이다. 기존 성공 suite는 재실행하지 않았다. RAW2 Issue1은 b1729b7/PR10 UNKNOWN/STOP으로 보존한다.

새 브랜치 `codex/event-unsynced-offline-20261025`는 PR5 head53b6cf9에서 분기했다. PR5 base18b78b6, 원본 PR5/PR10 변경 없음. main의 최신 AGENTS만 새 브랜치에 반영했다.

승인된 sample8,388,608B SHA256 `962925dfaf87fcd1a16d04cd6e122d32558527b543f39acc2803926f2fc897b3` 실물 일치. 원본은 비공개 /tmp에만 둔다. 기존 frame1557/events1469217/ON706157/OFF763060/unsynced830은 baseline이며 신규 PASS가 아니다.

구형 `/home/philip/dvs_encoder/s5krc1s_decoder.{cpp,hpp}`, `dvs_types.hpp`를 비공개 temp로 읽기 복사했다. source에 reference_b3_only 및 dual 분기가 존재한다. 해당 폴더는 Git repository가 아니므로 구형 historical commit은 **NOT AVAILABLE**; 정확한 파일 SHA로 분석 대상을 고정하며 과거 실행 binary와 동일하다고 주장하지 않는다. SDK 원본과 prepare_core patcher도 SHA 고정했다. `experiments/event-ab/evidence/p0-inputs.json` 참조. 구형 소스/SDK는 공개 Git에 포함하지 않는다.

P0 실제 실행은 git status/fetch, PR5 metadata 조회, sample SHA, 소스 파일 존재/hash 확인이다. 신규 decoder 시험은 NOT TESTED. Pi 명령은 소스 목록/텍스트 및 Git 이력 조회뿐이며 기기 파일·서비스·센서에는 접근하지 않았다. RAW2 production UNTOUCHED, Phase C HARD BLOCKED.

NEXT: P1 기능 대응표와 독립 오프라인 호출 adapter 설계.
