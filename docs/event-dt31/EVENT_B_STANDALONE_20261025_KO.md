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

## B3 실제Browser / 표시와물리검증분리

로컬비공개파생결과를127.0.0.1:8767로만제공해in-app browser에서확인했다. 최초sandboxbind가EPERM으로중단되어첫브라우저접속은refused였으며허용된loopback전용실행후정상로드했다. 완성1557frame, 첫frame305033µs/ON548/OFF668, 재생후frame5이상진행/일시정지, slider End로마지막1557/1093826µs/507µs주기/ON447/OFF384, OFF만·ON만선택을확인했다. canvas속성960×720/스크린샷시각검토완료. Browser API의canvas pixel조회는지원되지않아pixel검증은B2 Node/nativePPM근거로만보고한다.

화면은프레임당희소logicalevents이고실제손가락촬영identity/원센서물리좌표·시각정확성은file/mock으로인증불가다. 축이동/보간/Group2추측보정없음. 표시결함은입증되지않아B3 코드변경은없다. 이미지/원본frame은공개Git에올리지않았다. `b3-browser-review.json`은집계관찰만보존한다. NEXT=B4 config/exit/격리/fail-closed/재현문서.

## B4 config/exit/격리/재현

`event-b/README.md`에독립build/run/loopbackViewer/선택SSHforward/config범위/실패exit·status/SDK·sample접근요구/기밀·ABI·크기제한과재현명령을명시했다. 복귀/Switcher/대형복구프로그램은추가하지않았다.

신규launcher시험에서config가FIFO일때기존read_text가대기함을0.5s bounded fixture로실제재현했다. 소유한시험프로세스만종료했고운영접근은없다. package/config내부의최대16KiB일반non-symlink inode를O_PATH로pin한뒤읽도록수정했다. JSON dict/exactkeys/int/range/duplicate검사, emptyinput거부도추가했다. 수정은private실험package의launcher에만반영, nativeengine/SDKbinary는B1그대로다. 이전buildmanifest pins를보존하고현재runtime revision과해시를`b4-final-package-manifest.json`에추가했다.

Pi신규runtime17건PASS(`b4-runtime.json`): malformed JSON/shape/bool/duplicate/range/extra, FIFO/symlink/outsideconfig, --device즉시거부, pathescape명칭/없는·빈입력, checkout밖cwd에서합성1frame/2events완료상태, 기존run불변거부, 소유한child에SIGTERM전달(exit130/completefalse), info manifest. 이는**새패키지17건**이며기존native decoder17건과다른시험이다. raw8MiB E2E나decoder분석은재실행하지않고launcher변경에관련된tiny합성만사용했다.

Browser검증용자체tab와loopbackserver는종료했다(명령/PID확인후시험소유프로세스만종료). package는/tmp에만존재하며production파일/설치/서비스/센서/DT/media/watchdog/실기0회. NEXT=B5 최종artifact검사와별도DraftPR/Issue인수인계.

## B5 최종 결과와 다음 작업

독립 Event B의 **파일 기반 소프트웨어 완성**을 검토 요청한다. 운영 설치 없이 `/tmp/dvs-event-b-package-20261025-v2/bin/event-b`에서 실행되며, 재현 절차는 [event-b/README.md](../../event-b/README.md)에 있다. 승인 SDK와 sample이 없으면 공개 저장소만으로 빌드·재생할 수 없다. 이 제한은 기밀 자료를 공개하지 않기 위한 입력 의존성이다.

| 검증 범위 | 결과와 근거 |
|---|---|
| 독립 native 빌드 | Pi GCC14.2, EVENT_FILE_ONLY, 별도 bin/config/share/runs, manifest 일치 |
| 신규 패키지 저장 파일 E2E | 단회 PASS, 1557 완성 프레임 / SDK1469217 이벤트, 출력 SHA 기준 일치 |
| bounded queue / EOF / 종료 | cap8/high8/drop0/final0, EOF partial0/incomplete1, exit0 |
| 960×720 파일 Viewer | Node native-PPM 동치, 실제 browser play/pause/seek/polarity/timestamp 확인 |
| 새 런처 안전·실패 시험 | 17 PASS, config FIFO 대기 결함 수정, SIGTERM130/complete=false |
| 기존 검증 재사용 | decoder/queue/파일 가드/렌더와 PR13 해석 재사용. 과거 suite와 분석 재실행 없음 |
| 실기 센서·물리 좌표·손가락 정확성 | **NOT TESTED / UNKNOWN**. 실제 센서 모드 전환 없음 |
| 복귀 프로그램 / Switcher | **범위 제외**, 개발하거나 실행하지 않음 |
| RAW2 A / Phase C | **UNTOUCHED / HARD BLOCKED**, --device 거부 유지 |

최종 manifest의 source hashes가 현재 소스와 일치하고 native binary는 B1 이후 그대로임을 확인했다(`b5-final-checks.json`). 파생 영상·SDK·sample·frame binary는 공개 Git에 없다. 임시 browser/server도 종료했다.

2026-10-25 07:44:02 KST 읽기 전용 종료 점검: RAW2 PID683775, NRestarts0, active/enabled. 보고된 V4L2 dequeue/buffer/sequence-gap0, web57.999/HDMI59.999fps. 이는 계속 가동 상태의 한 시점 확인이며 복구 시험이나 물리 영상 검증은 아니다(`b5-raw2-continuity.json`).

**유일한 NEXT:** 이 독립 file-only 패키지의 Draft PR 검토. 후속 기능은 새 작업 카드로 정하며, 완료된 B0~B5나 기존 분석을 반복하지 않는다. 실기 전환은 이 결과로 승인되지 않는다.

제출: [Draft PR17](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/17), B0~B5 코드/증거 checkpoint f91bd97. 단계별 실행 기록은 [Issue15](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/issues/15)와 PROGRESS에 남긴다. 자동 merge/Issue close 없음.
