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
