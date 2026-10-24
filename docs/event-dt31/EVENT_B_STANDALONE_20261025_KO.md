# Issue15 독립 Event B 완성 — file-only

## B0 출발점 / 재사용과 남은 일

최신 main87219ad AGENTS, Issue15 본문/댓글, Blue-Green §5, 실제PR5 head53b6cf9와PR13 head50f465f 및개발PROGRESS를확인했다. 전용브랜치 `codex/event-b-standalone-20261025`는 두코드가존재하는PR13 head50f465f에서분기했다. 원본PR5/13 수정·merge없음. main AGENTS/설계문서의현재우선순위만반영한다.

| 구성 | 이미 검증됨 / 재사용 | 독립 B에 남은 일 |
|---|---|---|
| C++ SDK decoder | private SDK + prepare_core carry/EOF; native17, deterministic sample, PR13 A/B | 외부SDK의격리빌드/독립bin/manifest |
| 입력/queue | PR5 RegularInput, bounded Queue, 파일backpressure/종료 | file-only패키지CLI와config/출력경로격리 |
| 960×720 render | PR5 PPM greenON/redOFF 및frame binary | 파일기반재생/seek/polarity/timestamp/frame/stats UI |
| 계측 | PR5 queue/CPU/EOF/ON/OFF, PR13 unsynced830해석 | 패키지E2E계측및타임스탬프/출력정합성 |
| 안전 | --device PHASE_C_BLOCKED, Linux regular-file guard | 패키지진입점/설정/실패에대한좁은회귀 |
| 현재비범위 | RAW2 Issue1 UNKNOWN/STOP, 복귀/Watchdog/switcher | 재분석·복귀프로그램·실센서시험안함 |

기존suite는실행하지않았다. 시작시actualgit tree clean과source/evidence검토만수행. 이작업은Linux RP5 file-only배포패키지로구현하며비공개SDK/sample은기존승인/tmp경로에만둔다. RAW2 A UNTOUCHED, Phase C HARD BLOCKED. NEXT=B1 독립빌드/실행패키지.
