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

## B1 구현 체크포인트

`event-b/build.py`는 기존prepare_core로private SDK copy를만들고 기존engine.cpp에`EVENT_FILE_ONLY`를지정해별도`bin/event-b-engine`을빌드한다. V4L2/service-check코드는이산출물에컴파일하지않는다. 공통Packet정의만헤더로분리해queue/decoder/RegularInput/renderer는재사용한다. 원본PR5/13브랜치는수정하지않는다.

독립private package는bin/config/share/runs/build와source/SDK/binary hash manifest를가진다. `bin/event-b replay --file ... --name ...`, `info`, loopback전용`serve`를제공하며output은package/runs에만생성한다. 기존run덮어쓰기거부, --device즉시PHASE_C_BLOCKED, 별도config범위검사, exit/status/log보존. 서비스/자동설치/부팅파일은만들지않는다.

Viewer는기존PPM렌더의greenON/redOFF규칙을재사용해완성frame binary를index하고play/pause/seek/fps/polarity/timestamp/stats를표시한다. 물리좌표검증이아닌file-only UI임을표기한다. B2에서실제패키지재생과검증을수행한다.

B1 실제결과: Pi GCC14.2 -Werror nativebuild PASS, manifest `b1-native-build.json` source/binary SHA 기록. 첫build는live-only locals미사용경고로FAIL했으며같은ifdef로이동한후새v2경로에서PASS했다. runtimeE2E/Viewer검증은다음단계이며아직성공으로보고하지않는다.

## B2 신규패키지 단일 file E2E

`check_package.py --package /tmp/dvs-event-b-package-20261025-v2 --sample <approved8MiB> ...`를Pi에서1회실행했다. packageCLI→RegularInput→기존boundedbyteQueue→SDKdecoder/outputWaitPipe→framebinary/PPM→파일Viewer 경로다. 이전native17/adapter22/restore24/readiness33/Issue11분석을반복한것이아니다.

sample SHA962925df…97b3, outputframe SHAe15a8a…1798 일치. 완성1557frames, SDK1469217events(ON706157/OFF763060), unsynced830, invalid/unknown/framegap0. queuecap8/high8/drop0/final0, EOFpartial0/incomplete1, exit0/complete=true. timestamp305033→1093826µs monotonic. file run0.971242s/8.63699MBps/CPU105.156%, child maxRSS27504KiB 관측. 이는해당파일재생/출력비용을포함한단회측정이며센서성능·누수없음의장기보장이아니다. CSIFS/FE/CRC/ECC는null이다.

완성frame에실린event는1468615개로SDK통계와602개차이가난다. SDK누적events와시작·끝완성출력만의event count는다른범위이며EOF incomplete1이존재한다. 이차이를전송손실로보고하지않는다. binary에서V4L2Capture symbol없음과CLI --device즉시거부확인. source/binary pins `b1-native-build.json`, 수치 `b2-native-e2e.json`.

Node파일Viewer에서1557개index/마지막frameRGB를native PPM과byte동치검증, 합성ON/OFF/좌표bounds거부확인(`b2-render-equivalence.json`). 파생frame/PPM은비공개temp에만복사했으며Git에없다. 실제브라우저play/seek/display확인은B3에서수행한다.
