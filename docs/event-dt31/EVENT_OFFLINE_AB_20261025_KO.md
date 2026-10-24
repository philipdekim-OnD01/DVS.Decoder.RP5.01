# Issue11 Event 오프라인 A/B — 진행 보고

## P0 환경·출처 고정

main AGENTS f7f9492 및 Issue11/최신 댓글, 개발 PROGRESS를 확인했다. main의 과거 PhaseA 미확인 표는 PR5의 실제 native17/evidence보다 오래된 기록이다. 기존 성공 suite는 재실행하지 않았다. RAW2 Issue1은 b1729b7/PR10 UNKNOWN/STOP으로 보존한다.

새 브랜치 `codex/event-unsynced-offline-20261025`는 PR5 head53b6cf9에서 분기했다. PR5 base18b78b6, 원본 PR5/PR10 변경 없음. main의 최신 AGENTS만 새 브랜치에 반영했다.

승인된 sample8,388,608B SHA256 `962925dfaf87fcd1a16d04cd6e122d32558527b543f39acc2803926f2fc897b3` 실물 일치. 원본은 비공개 /tmp에만 둔다. 기존 frame1557/events1469217/ON706157/OFF763060/unsynced830은 baseline이며 신규 PASS가 아니다.

구형 `/home/philip/dvs_encoder/s5krc1s_decoder.{cpp,hpp}`, `dvs_types.hpp`를 비공개 temp로 읽기 복사했다. source에 reference_b3_only 및 dual 분기가 존재한다. 해당 폴더는 Git repository가 아니므로 구형 historical commit은 **NOT AVAILABLE**; 정확한 파일 SHA로 분석 대상을 고정하며 과거 실행 binary와 동일하다고 주장하지 않는다. SDK 원본과 prepare_core patcher도 SHA 고정했다. `experiments/event-ab/evidence/p0-inputs.json` 참조. 구형 소스/SDK는 공개 Git에 포함하지 않는다.

P0 실제 실행은 git status/fetch, PR5 metadata 조회, sample SHA, 소스 파일 존재/hash 확인이다. 신규 decoder 시험은 NOT TESTED. Pi 명령은 소스 목록/텍스트 및 Git 이력 조회뿐이며 기기 파일·서비스·센서에는 접근하지 않았다. RAW2 production UNTOUCHED, Phase C HARD BLOCKED.

NEXT: P1 기능 대응표와 독립 오프라인 호출 adapter 설계.

## P1 파서 의미 대응표 — source inspection

파일 경로는 P0에 고정한 private source 기준이다. 아래는 의미 요약이며 원문 복제가 아니다. 신규 `src/decoder.cpp`, 구형 `s5krc1s_decoder.cpp`의 원본 행 번호다. historical legacy binary 동일성은 UNKNOWN. 어느 파서도 센서 물리 정답으로 취급하지 않는다.

| 항목 | 구형 reference-b3 / dual | 신규 native C++ | 비교 경계 |
|---|---|---|---|
| word/class/order | 421–452 BE32, b0&FC; zero 제외, group bit7 | 77–85 b0&7C, CID bit1, zero 제외 | bit0의 유효성 검사 다름; GROUP의 group1 bit6와 class 구분 |
| TIMESTAMP | 454–519 ref22/sub10 보관, ts_current는 마지막 단위 값 | 120–153 ref/sub 유효성 및 sub<=999, ref*1000+sub | 구형 DVSEvent time은 호출자가 주는 host ns(339/740), sensor time과 비교 불가 |
| COLUMN/X | 556–620 x11/frame8, x<960; valid column만 요구 | 154–168 x11/frame8/mo와 epoch bit5; ref/sub 조건과 결합 | mo/epoch gate 구형 없음 |
| group1/group2 | 626–688 group1; dual=offset>0이면 group1+offset; offset0은 같은 그룹 | 87–112 mo면 group1-delta, 아니면+delta | mo=1에서 차이 가능; delta0 mask overlap/극성 검사 신규만 |
| B3/B2 | 681–691 reference=B3 only ON. dual=B3/B2, delta0 ON/OFF 강제 | 104–107 B3/B2 두 mask, b1 polarity bits | reference는 의도적으로 비교 subset. dual도 delta0 의미 주의 |
| Y bit expansion | 722–739 bit0..7 -> group*8+bit | EventGroup base y/mask 출력, header 정의 y+bit | 논리 좌표만 비교; 물리좌표 인증 아님 |
| FRAME_END | 522–552 frame match 검사/옵션, column validity 유지; end count | 169–212 frame 검증/last_end, x/frame reset; 시작부터 본 CID0 frame만 출력 | 구형 end_packets와 신규complete frames 동일 counter 아님 |
| CID | 447–453 sensor_id 추출하나 단일 current_column/timestamp 상태 | 81–83 context[2], CID1 stats만/CID0 출력 | 다중CID cross-context는 동치 주장 불가 |
| EOF / split | 339–419 carry 지속, 명시 EOF finalize 없음 | 원본45–60 wordtail 미보관; 기존prepare_core copy에 carry/EOF 추가 | Issue11은 기존carry수정 적용copy와 비교. EOF1 incomplete 유지 |
| 동기/오류 | 698–714 column 및 group bounds; TS/epoch gate 없음 | 90–100 delta0 invalid 우선, 이후 x/ref/sub/epoch 없으면 unsynced++ | unsynced는 group word 수이며 픽셀/손실프레임 수 아님 |

A/B 실행은 구형 init(960,720,1), gen4 CID=true, hold_cycles=0(변화 억제 제거), reference_b3_only를 명시적으로 true/false, same_group=false, strict frame_end로 고정할 계획이다. 이것은 구형 알고리즘 비교용 조건이며 운영 설정의 재현이라고 주장하지 않는다. 필터/Viewer 없이 raw logical event를 비교한다. 신규는 기존 prepare_core.py를 private copy에만 적용하며 trace hook 추가는 비교용 관찰만 한다. compile/run은 다음 P2에서 기록한다.

NEXT=P2 실제 두 파서 호출 및 offset 기반 최초 divergence.

## P2 실제 동일 입력 A/B — macOS arm64

`build.py --sdk <private-sdk> --legacy <private-source> --work <private-build>`로 Apple clang21.0 C++20 빌드 성공. `run_ab.py --work ... --sample <approved8MiB> --results ...`가 실제 구형 C++ reference/dual과 기존carry수정 SDK C++를 독립 호출했다. 구현 재작성 Python 모델을 정답으로 사용하지 않았다. command/compiler는 `p2-build.json`, 통계는 `p2-comparison.json`. trace hook은 private SDK copy에만 추가하며 생산/원본 소스는 변경하지 않는다. per-event traces/완성frame bytes는 private temp에만 쓴다.

| parser / counter | reference-b3 | dual | 신규SDK |
|---|---:|---:|---:|
| logical events | 718585 | 1470290 | 1469217 |
| ON / OFF | 718585 / 0 | 706596 / 763694 | 706157 / 763060 |
| COLUMN / GROUP words | 919067 / 1173411 | 919067 / 1173411 | P3 독립word분류와 교차검증 예정 |
| end_packets / complete frames | end1558 | end1558 | complete1557 |
| invalid_x/y, unknown | 0/0,0 | 0/0,0 | invalid0/unknown0 |

최초 divergence는 file byte offset4(word1), GROUP이다. offset0 COLUMN에서 x79가 설정되어 구형reference는 (79,272,ON), dual은 (79,272,ON)와 (79,496,ON)을 emit한다. 신규SDK는 그때 ref/sub/epoch가 없어 group을 건너뛴다. sensor timestamp는 아직 없으며 구형event의 timestamp_ns는 이번 호출자가 준0이므로 센서 시각과 비교 불가다.

Offset 단위 `(x,y,polarity,CID)` ordered event tuple 비교: dual-vs-SDK는1172581개 event-producing word 동치,830개 word 불일치. reference-vs-SDK는423400개 동치,749667개 불일치로 B3-only/극성 정책 차이를 포함한다. padding/무event word는 이 동치 수에 포함하지 않는다. 신규 frame output SHA `e15a8a75899f6352725e0a4fbcd73f537acd1496fda6ae8ac25cd17903be1798` 및 모든 baseline 카운터가 기존 기록과 일치해 trace가 이 입력의 결과를 바꾸지 않았음을 확인했다. 기존 native17 전체 suite를 재실행한 것은 아니다.

전제: 구형은 host hold_cycles=0, per-word decode_batch로 suppression 없이 raw events 비교. legacy frame end와 신규 complete frame의 의미가 다르다. logical tuple 동치는 센서 물리좌표/시간 정답 인증이 아니다. NEXT=P3 830개 발생 위치·동기상태·경계 원인 분류.

## P3 830건 계층 분류 — 소프트웨어 조건 규명

`classify_unsynced.py`는 실제 SDK 관찰trace와 독립4B class/column/frame-end 분석을 교차검사했다. 결과 `p3-unsynced.json`. 모든830건은 offset4..5732의 파일prefix에 있으며 COLUMN은 이미 offset0에서 x79로 유효하다. 최초 FRAME_END5736, REF5740, SUB5744, 그 뒤 epoch COLUMN5748이다. prefix 동안 COLUMN은604회 변경되지만 ref_ok/sub_ok/epoch_ready는830건 전부 false다. 유효X 없음0건/CID1 0건, 이후unsynced0이다.

**증가 조건:** delta0 invalid 검사에 걸리지 않은 GROUP에서 `x<0 || !ref_ok || !sub_ok || !epoch_ready`이면 word당1 증가하고 mask의 pixel 확장은 하지 않는다. 이번830건은 COLUMN 이전이 아니라 **timestamp/epoch 동기 이전**이다. delta=0 invalid가 있으면 unsynced보다 먼저invalid로 분류되므로 모든 미동기GROUP의 포괄적 카운터라고 일반화하지 않는다.

actual dual-vs-SDK가 다른830 offsets 집합과 실제unsynced830 offsets 집합이 정확히 같다. dual이 prefix에서만 더 출력한1073pixel-events(ON439/OFF634)가 전체통계 차이를 설명한다. 이후 logical `(x,y,polarity,CID)` event 목록은 word offset별 순서까지 일치한다. 전체 분류 COLUMN919067/GROUP1173411/FE1558/REF1558/SUB1558, zero/unknown0. sample의 GROUP은 전부mo0 COLUMN context 아래이므로 mo1/signed-delta 동치를 이 샘플로 입증하지 못한다.

### Jetson 방법 참고 / 다른 counter 의미

비공개 `e850/dvs-tools/dvs_gaps.py` blob08bb04300fc876e11b4966832e4fc24ebb132636을 권한 내 읽었다. 적용한 방법은4B분류·연속file offset·COLUMN/FE 상태·고정경계 비교 가능성 검토뿐이며 원문/코드/하드웨어설정 이식은 없다. 그 도구의 column-orphan(run) 개념과 SDK의 timestamp/epoch 포함unsynced(word)는 다르다. 같은 샘플에서 column-orphan group words0, column/end 및 end+1 번호검사 실패0이지만 SDKunsynced830이다. 이를 동의어로 보고하면 원인 분류가 틀린다.

### UNKNOWN

원본 V4L2 buffer/CSI packet 경계 metadata는 이 rawword sample에 보존되지 않았다. 파일offset0 또는 시험1MiB read경계를 실제DMA/CSI경계로 간주할 수 없다. 모든830건이 파일prefix라는 관찰은 확정이나 **왜 원 녹화가 이 위치부터 시작했는지**, 이전bytes의 존재/센서물리누락은 UNKNOWN이다. 830을 event loss/frame loss 또는 CSI손상으로 부르지 않는다. 입력split 불변성은 이전baseline이 있으며 이번 관찰hook의 최소검증은 다음 P4에서 합성입력으로 수행한다.

## P4 최소 오프라인 regression — 신규 관찰 계측 검증

`test_observer.py --work <private-build> --results p4-observer-tests.json`: macOS7 PASS. 새 trace hook이 보는 offset/state와 carry를 검증하기 위해 **합성8250B** fixture를 사용했다(정확한 길이는 코드 및 input SHA 기준). 기존8MiB full split/native17 suite는 반복하지 않았다.

- 합성 prefix GROUP1개와 FE후COLUMN없는 GROUP1개: unsynced2, 정상2frames/events4(ON2/OFF2), EOF partial2B. 1B/4B/4093B/1MiB/random(seed20261021) 입력에서 frame/event/unsynced trace SHA 동일. 4093/random은 실제로 단어를 가르는 분할이며 1MiB는 작은fixture 전체가 한read에 들어간다는 한계가 있다.
- 실제sample에는없는 mo1 signed group2를 별도합성으로 확인(y/polarity17ON,8OFF). 이것이 구형dual의 mo1 정답이나 물리좌표 인증을 뜻하지 않는다.
- timestamp/column 없는 delta0 invalid mask는 invalid1/unsynced0으로 선행오류 분류됨을 확인.
- 첫 실행은 fixture의 FE후GROUP 예상offset을8232로 잘못 계산해 assertion FAIL. 실제 생성순서의8224로 수정 후7 PASS. production parser 변경은 없다.

### 비교 가능한 센서 시각 필드 보강

구형 replay adapter에 ref/sub stats 관찰만 추가해 dual을 한 번 더 호출했다(기존Decoder 본문 변경 없음). 실제 decoded ref*1000+sub1558쌍 중 완성SDK frame과 대응되는 최초1557쌍이 `SensorFrame.timestamp_us`와 모두 같다. 마지막1쌍은 EOF incomplete로 대응출력없음. 구형DVSEvent의 host ns는 비교대상에서 제외한다. Event trace SHA도 앞 P2와 동일. `compare_timestamps.py`, `p4-timestamps.json` 참조.

이 비교의 최초시도는 출력EventGroup stride를8B로 잘못 가정해 FAIL했다. SDKheader의 실제필드/이ABI상6B로 수정한 뒤 container전체소비/1557 timestamp동치 assertion PASS. SDK의 SensorFrame16B/EventGroup6B ABI에 한정하며 다른 ABI에 이 rawbinarylayout을 일반화하지 않는다.

이번 신규시험은 macOS clang21 file/synthetic뿐이며 Pi native 재검증·ASan·실기수신은 NOT TESTED. baseline17건을 이번시험으로 중복 집계하지 않는다. 신규SDK 파서 결함은 이 관측에서 증명되지 않아 parser 수정없음. RAW2 production UNTOUCHED/Phase C HARD BLOCKED.
