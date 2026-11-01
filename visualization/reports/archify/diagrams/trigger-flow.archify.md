# archify 스킬을 부르면 HTML이 나오기까지 무슨 일이 일어나나 {#archify-flow}

LLM이 `SKILL.md` 지침에 따라 초안을 쓰고, `finalize` 명령이 그 초안을 검증·렌더링·검사해 HTML 한 파일로 전달한다. 코드가 LLM을 호출하는 부분은 없고, 무엇을 그릴지는 LLM이 정한다.

- 산출물 종류와 타입은 `SKILL.md`의 지시문을 읽은 LLM이 고른다.[](source:skill-choose)
- `finalize`는 `deliver`, `check`, `browser-check`를 차례로 실행하고 첫 실패에서 멈춘다.[](source:finalize-loop)
- 검증은 모양, 치수, 근거 파일의 존재까지만 본다. 인용한 줄의 내용이 주장과 맞는지는 보지 않는다.[](source:evidence)
- 결과 HTML에는 원본 JSON이 들어 있지 않다.[](source:apply-template)

@answer scope="archify 3.2.0, 커밋 a406594, 일반 다이어그램 경로 중심. 코드를 읽어 확인했고 직접 실행은 하지 않았다"
@meta locale=ko
@source skill-choose title="SKILL.md: Choose the artifact" path=archify/SKILL.md lines=18:24
@source guide-score title="recommendScenario: 키워드 점수 추천" path=archify/recipes/scenarios.mjs lines=387:392
@source finalize-loop title="runFinalize: 단계 반복" path=archify/bin/finalize.mjs lines=835:840
@source showcase-fail title="runFinalize: showcase 경고 실패" path=archify/bin/finalize.mjs lines=926:931
@source no-browser title="runFinalize: explainer는 브라우저 생략" path=archify/bin/finalize.mjs lines=746:746
@source deliver-run title="commandDeliver: 렌더 후 검사" path=archify/bin/archify.mjs lines=4870:4910
@source load-diagram title="loadDiagram: 검증 순서" path=archify/renderers/shared/cli.mjs lines=81:87
@source evidence title="verifyRepositoryEvidence: 파일과 줄 대조" path=archify/renderers/shared/repository-evidence.mjs lines=328:350
@source apply-template title="applyTemplate: 슬롯 채움" path=archify/renderers/shared/utils.mjs lines=184:200
@source output-order title="resolveOutputPath: 출력 우선순위" path=archify/renderers/shared/output-path.mjs lines=385:391
@source viewports title="VISUAL_CHECK_VIEWPORTS: 측정 해상도" path=archify/bin/visual-check.mjs lines=37:42

## 요청은 어떻게 산출물 종류와 타입이 되나? {#choose}

@workflow id=choose-flow title="산출물 선택"
| ask | 사용자 요청 | external |
| page | 한 페이지 요청? | backend |
| draw | 그림 요청? | backend |
| explainer | explainer 작성 | backend |
| native | 타입 선택 | backend |
| text | 텍스트 답 | backend |
| ask > page | |
| page > explainer | 예 | emphasis |
| page > draw | 아니오 |
| draw > native | 예 | emphasis |
| draw > text | 아니오 |

한 페이지로 달라는 요청이면 explainer를 만들고, 그림을 달라고 하면 10개 타입 중 하나를 고른다. 어느 쪽도 아니면 텍스트로 답한다.[](source:skill-choose)

규칙 줄 `[archify explainer: proactive]`가 컨텍스트에 있으면 요청이 없어도 페이지를 함께 만든다.

타입이 애매할 때만 `guide` 명령을 쓴다. 이 명령은 시나리오 키워드의 가중치를 더해 추천하며, LLM 판단이 아니고 강제도 아니다.[](source:guide-score)

## 초안에서 HTML까지 어떤 순서로 실행되나? {#pipeline}

@sequence id=pipeline-flow title="finalize 실행 순서"
| actor llm | 사용자+LLM | external |
| actor fin | finalize | backend |
| actor dlv | deliver | backend |
| actor rnd | 렌더러 | backend |
| actor chk | check | security |
| actor brw | browser-check | security |
| llm | fin | 초안과 출력 경로 | emphasis |
| phase | 1단계 deliver |
| fin | dlv | deliver 실행 |
| dlv | rnd | staging에 렌더 |
| rnd | dlv | HTML | return |
| dlv | fin | 검사 통과 후 교체 | return |
| phase | 2단계 check |
| fin | chk | 해시와 SVG 검사 |
| chk | fin | 통과 | return |
| phase | 3단계 browser-check |
| fin | brw | Chrome 측정 |
| brw | fin | 통과 | return |
| fin | llm | 영수증 JSON | return |

@steps id=pipeline-steps
| st-fin | finalize | 초안과 출력 경로를 받아 단계를 자식 프로세스로 차례로 실행한다. 첫 실패에서 멈추고 영수증을 쓴다. | pipeline-flow | fin |
| st-dlv | deliver | 임시(staging) 폴더에서 렌더하고 정적 검사를 돌린다. 통과하면 HTML과 provenance 파일을 한 쌍으로 교체한다. | pipeline-flow | dlv |
| st-rnd | 렌더러 | 입력을 검증하고, 타입별 코드가 SVG를 만들어 템플릿 빈칸에 채운다. | pipeline-flow | rnd |
| st-chk | check | 산출물이 deliver가 만든 그대로인지 확인하고 SVG를 정적으로 검사한다. | pipeline-flow | chk |
| st-brw | browser-check | Chrome으로 4개 해상도에서 넘침과 글자 크기를 잰다. | pipeline-flow | brw |

`deliver` 안에서 렌더러가 실행되고 곧바로 검사가 이어진다.[](source:deliver-run) 문서가 말하는 `validate` 단계는 별도 프로세스가 아니라 `deliver`에 들어 있다.

기본 품질인 `showcase`에서는 경고가 하나라도 있으면 `deliver`가 실패한다.[](source:showcase-fail) explainer는 기본으로 `browser-check`를 건너뛴다.[](source:no-browser)

## deliver 안에서 입력은 어떤 순서로 검증되나? {#validate}

@workflow id=validate-flow title="렌더러의 입력 검증과 렌더"
| lane input | 입력 확인 |
| lane render | 렌더 |
| parse | 형식 확인 | backend | input |
| schema | 스키마 | backend | input |
| ids | ID 관계 | backend | input |
| prof | 프로파일 | backend | input |
| evid | 근거 대조 | security | input |
| svg | SVG 생성 | backend | render |
| tpl | 템플릿 채움 | backend | render |
| out | 파일 쓰기 | database | render |
| parse > schema | |
| schema > ids | |
| ids > prof | |
| prof > evid | |
| evid > svg | 통과 | emphasis |
| svg > tpl | |
| tpl > out | |

순서는 JSON 문법과 출력 경로 형식, 스키마, 로케일, ID 관계, 프로파일, 저장소 근거다.[](source:load-diagram) 근거 단계는 `--repo-root`의 Git 커밋에 파일이 있는지, 줄 번호가 파일 줄 수 안인지를 `git show`로 확인한다.[](source:evidence)

@callout level=warning title="의미는 검증하지 않는다"
| 인용한 줄의 내용이 노드 설명과 맞는지는 코드가 확인하지 않는다. 읽은 범위에서 그런 비교 코드를 찾지 못했다. |

## 검증은 몇 겹이고 무엇을 못 잡나? {#gates}

| 단계 | 확인하는 것 | 확인하지 못하는 것 |
| --- | --- | --- |
| 입력 검증 | 스키마, ID 관계, 근거 파일과 줄의 존재 | 줄 내용이 주장과 맞는지 {bad:의미} |
| 렌더러 배치 규칙 | 노드 겹침, 캔버스 밖, 라벨 간격 | 일부 타입의 세부 규칙(미확인) |
| 정적 SVG 검사 | 화살표 직각(허용 0.01), 회랑 겹침 8px, 라벨 여유, 글자 하한 6px | 노드 겹침은 보지 않는다 {bad:겹침} |
| provenance | 산출물이 deliver 결과 그대로인지 | 직접 고친 HTML은 Chrome 실행 전에 막힌다 |
| 브라우저 측정 | 4개 해상도의 넘침, 글자 크기, 테마 | 사람 눈의 품질 {caution:기본은 생략} |

브라우저 측정은 1440×900, 1600×1000, 1920×1080, 2048×1320에서 한다.[](source:viewports) 스크린샷은 만들지 않고 영수증 JSON만 남긴다. 시각 검토는 사용자가 요청할 때만 하는 선택 절차다.

## 무엇을 바꿀 수 있나? {#custom}

@facts id=output-facts
| 출력 위치 우선순위 | CLI 인자, `meta.output`, `<type>.html` 순 |
| 기본 폴더 | `.archify/<타입>-<slug>-<시각>/`, 스킬 지시이며 코드가 강제하지 않는다 |
| 템플릿 | 고정. 고르는 옵션을 찾지 못했다 |

출력 위치는 CLI 인자가 가장 앞선다.[](source:output-order)

| 바꾸려는 것 | 가능 여부 | 방법 |
| --- | --- | --- |
| 텍스트, 구조, 카드 | 가능 | JSON 수정 |
| 언어 | 가능 | `meta.locale`, 6개 번들 |
| 분위기 | 4종 중 선택 | `meta.visual_preset` |
| 노드 색 | {bad:불가} | 의미 타입으로만 정해진다 |
| 레이아웃 수치 | 가능 | 타입별 `layout` |

## feature map의 어느 행이 어디에 해당하나? {#featuremap}

| 행 | 기능 | 구분 | 이 페이지 |
| --- | --- | --- | --- |
| 1 | 산출물 선택 | 핵심 | 첫 번째 패널 |
| 2 | 타입 선택과 `guide` | 핵심 | 첫 번째 패널 |
| 3 | 근거 수집과 초안 작성 규칙 | 핵심 | 이 페이지 밖(authoring-contract 스펙) |
| 4 | `finalize` 오케스트레이션 | 핵심 | 두 번째 패널 |
| 5 | 입력 로드와 검증 | 핵심 | 세 번째 패널 |
| 6 | 렌더링 | 핵심 | 세 번째 패널 |
| 7 | 전달 | 핵심 | 두 번째 패널 |
| 8 | 자동 검증 게이트 | 핵심 | 네 번째 패널 |
| 9 | 실패 진단과 수리 루프 | 핵심 | 이 페이지 밖(repair-loop 스펙) |
| 10 | explainer 경로 | 핵심 | 이 페이지 자체가 예 |
| 11 | 결과 뷰어 | 부속 | 다루지 않음(viewer 스펙) |
| 12 | 보조 명령 | 부속 | 다루지 않음(auxiliary-commands 스펙) |

## 직접 확인할 것은 무엇인가? {#todo}

- [x] 실패 사례와 변조, 임계값은 기능 스펙 조사에서 확인했다(verification-gates, repair-loop).
- [ ] workflow·dataflow·lifecycle·erd·class 렌더러의 세부 배치 알고리즘을 읽는다.
- [ ] 프리셋 4종을 렌더링해 차이를 본다.
- [ ] `check`는 통과하는데 `browser-check`가 실패하는 사례(workflow 예제)를 직접 본다.
