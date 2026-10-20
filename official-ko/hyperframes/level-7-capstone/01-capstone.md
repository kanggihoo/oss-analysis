> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져올 수 있습니다.
> 더 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾아보세요.

# 캡스톤 — 하나의 여정에 담은 모든 기법

> 프롬프트 하나, 끊김 없는 카메라 이동 하나, 그리고 이 가이드의 모든 기법을 하나로 묶은 62초짜리 영화.

<video controls muted loop playsinline preload="metadata" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-timeline-default-v2.mp4#t=0.1" style={{ borderRadius: "0.5rem", marginTop: "0.75rem" }} />

*"The Timeline" — 1920x1080, \~62초, 프롬프트 하나, 끊김 없는 카메라 이동 하나, 편집 없음.*

이 영상은 프롬프트 하나로 만들었습니다. 이후에 아무것도 잘라내거나 이어 붙이지 않았습니다. 프롬프트는 약 60초를 요청했고, 렌더 결과는 1:02가 나왔습니다. 마지막 로고 락업이 2초 동안 숨을 고르기 때문입니다.

이 가이드를 순서대로 읽었다면 이 영상의 모든 부분을 이미 보신 것입니다. 각 영역은 그것을 가르치는 장에 따로 떼어 삽입되어 있습니다. 아래 표는 각 부분이 어느 장에서 왔는지 알려 줍니다. 이 페이지는 그 조각들이 하나의 컴포지션이 되는 곳입니다.

## 아이디어

컨셉이 곧 제품입니다. 시청자는 HyperFrames가 기반을 두고 있는 바로 그 타임라인(one literal timeline)을 따라, 처음 타이핑된 한 글자에서 완성된 MP4까지 이동합니다.

영상의 모든 내용은 사실입니다. 실제 카탈로그 수치, 실제 클라우드 리전, 실제 제품 화면입니다. 푸티지는 추천사가 아니라 도구가 처리하고 있는 재료로 등장합니다.

그리고 이 영상에는 장면(scene)이 없습니다. 넓은 세계 하나와 그 안을 움직이는 카메라 하나가 있을 뿐입니다. 이 페이지에서 가장 중요한 교훈입니다.

## 처음 두 번의 빌드가 실패한 이유

이 캡스톤의 처음 두 빌드는 모든 검사를 통과했지만, 리뷰에서는 실패했습니다.

첫 번째는 허공에 떠 있는 듬성듬성한 프레임처럼 보였습니다. 두 번째는 잘 꾸며진 슬라이드쇼였습니다. 장면이 따로 있고, 하드 컷이 있었으며, 움직임이 각 프레임 안에 갇혀 있었습니다.

애니메이션을 더 넣는 것은 해결책이 아니었습니다. 문제를 해결한 것은 프롬프트에 적은 **촬영 계약(cinematography contract)** 이었습니다. 규칙은 세 가지입니다.

**카메라 하나, 머무름과 쓸기(dwell and sweep).** 카메라는 넓은 세계 하나를 끊김 없는 단일 움직임으로 달려갑니다. 리듬은 연속성만큼 중요합니다. 카메라는 영역 사이를 쓸고 지나간 뒤, 진짜 완전한 정지까지 감속합니다. 그 영역의 핵심 메시지가 자리 잡는 동안(숫자가 다 올라가고, 킥커가 찍히고, 말한 키워드가 나오는 동안) 몇 초 동안 머뭅니다. 그다음 가속해서 떠납니다. 머무름이 쓸기에 의미를 줍니다. 쉼이 없으면 강조는 움직임 한가운데서 사라집니다. 머무르는 동안에도 세계는 계속 해결되므로, 카메라는 쉬어도 영상이 멈추지는 않습니다.

**영역은 자르기가 아니라 도착으로 바뀝니다.** 다음 영역은 카메라가 도착하기 전에 이미 화면 가장자리에 보입니다. 이전 영역은 페이드아웃이 아니라 패럴랙스로 빠져나갑니다.

**슬라이드쇼 흔적 없음.** 가운데에 페이드인되어 머물다가 페이드아웃되는 요소는 없습니다. 카메라가 지나가며 보여 주는 정적인 슬라이드처럼 읽히는 영역도 없습니다. 제자리에서 그냥 흔들리는 움직임도 없습니다.

프레임 밖으로 절대 나가지 않는 요소가 세 가지 있습니다. **와이어(wire)** 는 끊기지 않는 하나의 선이며, 그 자체가 타임라인입니다. 차트의 기준선이 되고, 그다음 지도의 호가 되고, 그다음 파형이 되고, 마지막에는 3D 코일이 됩니다. **룰러(ruler)** 는 상단의 크롬 띠입니다. 재생헤드(playhead)는 영상의 실제 재생 시간을 따라갑니다. **주인공(protagonist)** 은 오프닝에서 타이핑된 `<div class="clip">`입니다. 와이어를 타고 모든 영역을 지나며, 마침내 렌더링되는 바로 그것입니다.

이것은 저절로 일어나지 않습니다. 린터는 타임라인이 유효한지 검사할 수 있습니다. 촬영 기법을 요구할 수 있는 것은 프롬프트뿐입니다.

## 프롬프트 전문

아래는 프롬프트 전체이며, 한 글자도 바꾸거나 줄이지 않았습니다. 일부러 길게 썼습니다. 이것이 모든 절이 제 역할을 하는 영화 규모 요청의 모습입니다. 이 프롬프트는 [고충실도 룩](/prompting/visual-specs)의 상세도로 작성되었습니다. 정확한 hex 값, 정확한 타이밍, 이름 붙은 이징, 그리고 단어 그대로 인용된 문구가 들어 있습니다.

세 개의 절은 나중에 추가했습니다. 프레임 리뷰에서 빌더가 어긋나는 것을 잡아냈기 때문입니다. 그래서 프롬프트를 더 조이고, 영상을 거기에 맞게 수정했습니다.

* 칩은 와이어의 실제 경로 기하에 묶여야 합니다. 선 근처에 그냥 떠 있으면 안 됩니다.
* 벽화는 제자리에 고정되어 있어야 하고, 아이리스로 드러나며, 페이드아웃으로 빠져나가야 합니다.
* Depth 영역에서는 코일이 와이어에서 감겨 나왔다가 다시 와이어로 돌아가야 합니다. 칩은 3D 형태 뒤를 지나며 실제 깊이 가림(depth occlusion)을 받아야 하고, 형태 위에 떠 있는 오버레이처럼 보이면 안 됩니다.

이것은 [반복 개선](/prompting/iterating)에서 가르치는 것과 같은 잡아내고 조이는 루프입니다. 이번에는 프롬프트 자체에 적용해서, 다음 실행에서 후퇴하지 않도록 했습니다.

> /general-video Make a \~60-second 1920x1080 promo film for HyperFrames — the open-source framework that turns hand-authored HTML and GSAP animation into deterministic, frame-accurate video. The film's concept IS the product: the viewer travels along one literal timeline — the thing HyperFrames is built on — from the first typed character to the finished MP4. Everything true, nothing invented: real catalog counts, real cloud regions, real product surfaces.
>
> **Design system: the provided `frame.md` is the single source of brand truth — read it first and obey it exactly.** It is the real HyperFrames brand (by HeyGen), dark-first: flat near-black ground (`--page-bg` `#0a0a0a`), greyscale text hierarchy (`#fafafa` / `#a1a1aa` / `#71717a`), and **mint `#3CE6AC` used sparingly as the single accent — mint means go / primary / active**. The mint→cyan gradient (`#3CE6AC → #00E3FF`) appears in exactly one place in the whole film: the final CTA lockup. Typography from the file: **ABC Solar Display 700** for the display lockups ("WRITE HTML." / "WRITE HTML. RENDER VIDEO."), **TT Norms Pro** for everything else, **TT Norms Pro Mono** for all machine-flavored text (code, commands, timecodes, counts, region labels) with `tabular-nums`. Sentence case everywhere except small uppercase letter-spaced eyebrows. Glass surfaces use the file's `--glass-*` tokens with real backdrop blur. Radii, borders, shadows, and easing curves come from the file's tokens (`--ease-out-quint` entrances, `--ease-spring` count-bumps). Font files are provided as woff2 assets — bundle them, don't fetch from the network.
>
> **Cinematography contract (the most important section — this is what the film lives or dies on):**
>
> * ONE continuous camera journey with a dwell-and-sweep rhythm. The whole film is a single wide world (one large scene space) that the camera dollies across — left to right, with occasional push-ins and one descent — in one unbroken move with NO hard cuts anywhere except inside the two sanctioned seam moments named below. The rhythm: the camera SWEEPS between regions, then eases to a genuine REST at each region's hero moment — a full stop of roughly 1.5–2.5 seconds while the main point lands (the hero count completing, the kicker stamping, the spoken caption line, the check completing) — then accelerates away. The dwell is what gives the sweep meaning: without the rest, emphasis dies mid-motion. During a dwell the WORLD keeps resolving (counters tick, labels stamp, secondary motion continues) — the camera rests, the film never freezes.
> * Scene changes happen by ARRIVING, not cutting. The next region is already visible at the edge of frame before the camera reaches it; the previous region exits by parallax, not by fade-out.
> * NO slideshow tells: no element cluster that fades in centered, sits, and fades out; no region that reads as a static slide while the camera happens to pass; no motion that is just shaking or idling in place. Motion = the camera's travel + elements entering along the direction of travel + elements the camera hands off between regions.
> * Three persistent elements thread the ENTIRE film and are never absent:
>   1. **The wire** — a 3px ink-colored horizontal line, the literal timeline. It is the film's spine: every region hangs off it, the camera follows it, and it visibly continues into the next region at all times. It may bend, split into tracks, become a waveform, arc across a map, spiral into 3D — but it is always the same continuous line.
>   2. **The ruler** — a thin frame-ruler chrome strip across the top: tick marks, a running timecode, and a playhead marker that advances in sync with the film's actual playback time (at t=30s the playhead is at 30s). The ruler is the product's own UI language and it never leaves.
>   3. **The clip card** — the `<div class="clip">` typed in the opening travels the whole journey: it slides onto the wire as a clip chip after being typed, rides ahead of the camera between regions (handing itself off — visible leaving one region and arriving in the next), and is the thing that finally renders at the end. It is the protagonist. **The chip sits ON the wire at every moment: bind its position to the wire's actual path geometry (sample the drawn path, seek-safe), never keyframe it independently — through every bend, arc, waveform, and dive, the chip visibly hugs the line. A chip floating off-path breaks the story.**
>
> **Message, stated once:** "Write HTML. Render video." — opening hook and closing lockup. Arc: Type → Mount → Measure → Everywhere → Material → Surface → Rhythm → Depth → Render. Audience: developers evaluating a programmable video tool. Mood: focused build-up that keeps accelerating, resolving confident and warm at the render.
>
> **Direction (every region obeys it):**
>
> * Brand restraint per `frame.md`: the world is greyscale-on-near-black; `ground` `#0a0a0a` and mint `ink` `#3CE6AC` are declared as the two composition variables. The wire, the playhead, active chips, and each region's single hero accent are mint; everything else is the greyscale text/border hierarchy. No other hue anywhere — except cyan `#00E3FF`, which exists only inside the one sanctioned mint→cyan gradient on the final CTA.
> * VO-paced reveals: each region's elements land on their spoken cues as the camera arrives; secondary elements keep resolving while the camera is present; the region is complete just as the camera accelerates away.
> * Permanent chrome: the ruler (persistent element 2) plus a faint ink grid at \~8% opacity over the ground, everywhere in the world.
> * Density: every region fills three roles — one focal element at display scale, at least two supporting elements on their own cues, and the chrome/wire. Asymmetric compositions; display type \~a tenth of frame width; three depth layers with parallax between them (foreground elements slide past faster than the wire plane, backdrop slower — the parallax is what sells the continuous travel).
> * Negative list: no purple-blue AI gradients, no bokeh, no real browser/OS chrome screenshots, no stock photography, no third hue, no unseeded randomness, no static holds mid-film (the only near-still moment is the final lockup breath).
> * SFX from the media pipeline's library on the visual hits: keystrokes at the opening, a soft whoosh at each region handoff, ticks on counters and beat cuts, one riser into the render moment, one stamp on the lockup. All under the VO.
>
> **The journey (regions along the wire, \~timings; the camera flows through these, they are NOT cuts):**
>
> **Type (0–7s).** Black-on-charcoal close-up: a cursor types real HyperFrames markup character by character — `<div class="clip" data-start="0" data-duration="4">` and a `gsap.timeline({ paused: true })` line. As the typed line completes, the text's baseline extends and becomes **the wire** — the underline literally grows into the timeline and the camera begins its dolly along it. The typed div folds into a compact clip chip (persistent element 3) that drops onto the wire. Kinetic display type states "WRITE HTML." as the travel begins.
>
> **Mount (7–14s).** Traveling along the wire: it splits into three parallel track lanes; clip chips slide in along the direction of travel and seat onto the lanes on their spoken cues (audio track chip, video track chip, our protagonist chip among them). Small mono labels (`data-start`, `data-track-index`) tag themselves onto chips as the camera passes. The lanes merge back to one wire as the camera accelerates out.
>
> **Measure (14–21s).** The wire becomes a chart baseline (same line, same thickness — no cut): adapt the **`data-chart` registry block** — six labeled bars rise from the wire itself on spoken cues while a hero numeral counts up beside them in huge tabular mono: **50+ CATALOG BLOCKS** (the real registry count; supporting chips: 19 AGENT SKILLS · 7 RUNTIME ADAPTERS — also real). The bars recede by parallax as the camera moves on; the tallest bar's top edge hands off into the next region's horizon.
>
> **Everywhere (21–28s).** The wire arcs and the ground falls away: adapt the **`world-map` registry block** — the dotted world map scrolls beneath while the wire becomes a great-circle route arcing across it. Real render infrastructure, truthfully labeled: pulses light up at AWS and Google Cloud regions (US-EAST-1 · EU-WEST-1 · AP-SOUTH-1) with a "CLOUD RENDER · LAMBDA + CLOUD RUN" kicker — HyperFrames' actual deploy targets. The map fades away as the wire descends into the next region — the pulses hold their size until the fade; nothing on the map ever shrinks.
>
> **Material (28–39s).** The wire threads into a working canvas where footage is the material on the timeline: a real talking-head clip (generate a short clip of a person speaking one neutral line via the media pipeline's avatar video generation — it is material being processed, not a testimonial; **transcode it to HEVC `hvc1`** so the automatic proxy subsystem carries preview) sits as a clip on the wire. The order of operations IS the story: as the camera arrives and BEFORE the person speaks, the framework mattes the footage — **the background peels away via background removal**, sliding off along the travel direction and leaving the cutout standing alone on the brand ground. THEN they speak, and the main **keywords of their own line — derived from the clip's transcription — land word-synced as huge display text BEHIND the cutout**, each keyword slamming in on its spoken moment with the subject's silhouette occluding it (the two-layer text-behind-subject plate); style the keyword type by adapting a bold **catalog caption component** (`caption-kinetic-slam` or similar) at display scale. A designed lower-third chip renders behind the subject. The clip's own audio ducks the BGM briefly; the VO resumes as the camera pulls away and the worked footage recedes by parallax.
>
> **Surface (39–45s).** SANCTIONED SEAM #1: the camera pushes through an **`sdf-iris` shader transition** — the iris opens ONTO the continuation of the same wire (the wire is visible through the iris throughout; this is a lens the journey passes through, not a cut). Inside: frosted-glass inspector panels (real translucency — blur over what's behind; the product's Studio design language) hover above the wire carrying live values (`ease: power3.out`, a color token, an fps readout), over a **generated-artwork backdrop** — a flat abstract mural evoking motion trails, generated **palette-neutral (grayscale) and duotoned live by CSS** from the two variables so it re-skins with everything else. **The mural is a full-frame, screen-fixed backdrop: it never moves on screen — the widening iris circle alone reveals it already in place at full frame, it holds dead still while the wire, glass, and chip travel in front of it, and it exits by fading out. It must never slide, and the iris lens itself must render only its glowing ring — fully transparent outside the circle, no visible container.** Drifting `data-*` tags ride between mural and glass, clear of all text.
>
> **Rhythm (45–52s).** The wire becomes a waveform: **resolve the BGM first, run `hyperframes beats` on it, and drive this region on the detected grid** — the waveform pulses and compact media cards (a lyric line, a photo card, a chart flash) snap onto the wire on real analyzed beats while the camera keeps traveling; each snap gets a tick SFX. At least six beat-hits. SANCTIONED SEAM #2: the beat-hits may hard-cut card content ON the beat — the sanctioned exception, because the camera itself never stops moving through them.
>
> **Depth (52–56s).** The wire spirals off the flat plane into real 3D — a **Three.js scene via the frame adapter** (never CSS fake-3D): the camera descends following the wire as it coils around a rim-lit faceted form (ink material on charcoal), mono axis readouts landing on cue, then rises back to the plane with the wire leading the way out. The coil winds up out of the wire and collapses back onto it — its ends never float cut off in mid-air — and the protagonist chip joins the 3D scene for the crossing: it rides the wire straight through the coil's loops and passes behind the form with true depth occlusion, never floating over the geometry as a flat overlay.
>
> **Render (56–60s).** The wire's end plugs into a render chip; the protagonist clip card from the opening arrives (callback — same chip, having traveled the whole film) and snaps into it. A **seeded confetti burst** fires — mulberry32, **seed 42, each piece holding position for exactly two frames before stepping** (stop-motion feel) — and the VO lands the honest punchline: identical on every render, because determinism is the whole point. "WRITE HTML. RENDER VIDEO." locks up with the install line `npx skills add heygen-com/hyperframes`. The camera finally eases to rest — the film's only true stillness, one breath before the end.
>
> **Copy, quoted exactly:** opening "WRITE HTML." · stats "50+ CATALOG BLOCKS", "19 AGENT SKILLS", "7 RUNTIME ADAPTERS" · map kicker "CLOUD RENDER · LAMBDA + CLOUD RUN" · closing "WRITE HTML. RENDER VIDEO." + `npx skills add heygen-com/hyperframes`. The Material region's spoken line and typed code are yours to make real and legible — no lorem ipsum, no invented product claims anywhere.
>
> **Technique, pinned:** continuous world-camera via GSAP transforms (the dolly is the film); parallax layers in every region; `data-chart`, `world-map`, `sdf-iris`, and a caption component adapted from the registry; per-character typing at the open; matched-motion handoffs at every region boundary (the wire IS the match); full footage pipeline (generated clip → HEVC → auto-proxy → background removal → lower-third → word-synced captions); real beat grid from `hyperframes beats`; real Three.js via the frame adapter; seeded two-frame-hold confetti; SFX on hits; VO-paced reveals throughout.
>
> **Variables:** expose `ground` (default `#0a0a0a`) and `ink` (default `#3CE6AC`) as composition variables on the single root file, bound via CSS custom properties everywhere (including the duotoned mural), so one `--variables` call re-skins the entire journey. It will be rendered twice: the default brand palette, and a second full render with `{"ground":"#0d1420","ink":"#c8ff3d"}`.
>
> **Architecture constraint (technical):** single composition file — one `index.html`, one variable scope. The world is one wide scene space traversed by a camera transform; regions may still be timed `class="clip"` sections synchronized to the camera's arrival (so capture stays efficient), but their positions form one continuous world and the wire + ruler + protagonist chip layers persist across 100% of the film. No `data-composition-src` sub-files.
>
> **Voice & music:** confident, energetic female narration — Kokoro `af_sky`, passed explicitly via `--voice` — riding the journey's momentum (the VO never waits for the camera; the camera arrives on the VO). Driving, beat-forward electronic BGM from the catalog at the engine's default narration-bed volume; the same track feeds the Rhythm region's beat analysis.
>
> **Negatives:** no hard cuts outside the two sanctioned seams; no static regions; no shaking or idle-in-place motion passed off as energy; no hue beyond mint (cyan only inside the one CTA gradient) — and per the brand file, no purple-blue SaaS gradients ever; no stock footage or photography; no fictional stats, projects, or testimonials — every number and label must be true of HyperFrames today; no real OS/browser chrome; no unseeded randomness; none of the film is silent.

## 어느 장이 어떤 영역을 가르쳤는가

| 영역 | 보여 주는 것 | 이를 가르치는 장 |
| - | - | - |
| 타입 (0:00–0:07) | 글자 단위 코드 타이핑. 와이어가 되는 밑줄. | [코드 애니메이션](/prompting/code-blocks), [프롬프트 해부](/prompting/anatomy) |
| 마운트 (0:07–0:14) | 타임라인 고유의 어휘: 트랙, 클립, `data-*` 라벨 | [프롬프트 해부](/prompting/anatomy) |
| 측정 (0:14–0:21) | `data-chart` 블록. 일치하는 움직임으로 차트 기준선이 된 와이어. | [데이터와 지도](/prompting/data-and-maps), [전환](/prompting/transitions) |
| 어디에서나 (0:21–0:28) | `world-map` 블록. 실제 Lambda와 Cloud Run 리전. | [데이터와 지도](/prompting/data-and-maps), [렌더링과 출력](/prompting/rendering-and-output) |
| 소재 (0:28–0:39) | 푸티지 파이프라인, 순서대로. 생성된 클립, HEVC 프록시, 음성 *전에* 배경 제거, 화자 자신의 키워드가 컷아웃 뒤에서 쾅 들어옴, 피사체 뒤의 하단 자막. | [미디어와 오디오](/prompting/media-and-audio), [캡션 스타일](/prompting/captions-catalog), [오버레이와 하단 자막](/prompting/overlays-and-lower-thirds) |
| 표면 (0:39–0:45) | `sdf-iris` 셰이더 렌즈, 프로스티드 글래스, 팔레트 중립의 생성된 벽화. | [전환](/prompting/transitions), [VFX와 리퀴드 글래스](/prompting/vfx-and-liquid-glass), [생성 아트워크를 언제 쓸까](/prompting/generated-artwork) |
| 리듬 (0:45–0:52) | `hyperframes beats`의 실제 분석된 비트 그리드에 맞춘 컷. | [뮤직비디오와 슬라이드쇼](/prompting/music-and-slideshows) |
| 깊이 (0:52–0:56) | 프레임 어댑터를 통한 실제 Three.js. 루프를 감는 3D 코일이 된 와이어, 그리고 루프를 통과해 형태 뒤를 지나는 칩. | [런타임과 3D](/prompting/runtimes-and-3d) |
| 렌더 (0:56–1:02) | 시드 고정 컨페티, 2프레임 홀드. 결정론이 핵심 펀치라인. | [프리미엄처럼 읽히는 모션](/prompting/motion) (규칙 8) |

이 밖에 세 개의 장은 한 영역이 아니라 영상 전체에 걸쳐 흐릅니다.

카메라는 [프리미엄처럼 읽히는 모션](/prompting/motion)의 "배우로서의 카메라(camera as actor)" 규칙을 극한까지 밀어붙인 것입니다. 카메라는 영상 안에 있는 것이 아닙니다. 카메라가 곧 영상입니다.

와이어, 룰러, 칩은 [스토리보드](/prompting/storyboards)의 콜백 장치를, 두 프레임이 아니라 전체 러닝 타임에 걸쳐 늘린 것입니다.

그리고 룩은 프롬프트에서 전혀 묘사되지 않습니다. 프롬프트는 `frame.md` 브랜드 파일을 가리키며 "정확히 따르라"고 말합니다. 그 파일에 실제 HyperFrames 디자인 시스템이 들어 있습니다. 거의 검은 바탕, 그레이스케일 텍스트 계층, go/active를 뜻하는 단일 강조색인 민트. 락업에는 ABC Solar Display, 기계 텍스트에는 TT Norms Pro Mono. 마감 CTA에만 쓰이는 민트에서 시안으로 가는 그라데이션 하나. 어떤 형용사보다 브랜드 진실의 출처가 낫습니다. 이것이 [디자인 시스템과 브랜드](/prompting/design-systems)의 핵심 명제를 영화 규모로 보여 주는 것입니다.

### 왜 파일이 하나인가

HyperFrames는 컴포지션 파일마다 `data-composition-variables`를 읽습니다. 파일이 하나면 변수 범위도 하나이고, 변수 범위가 하나여야 `--variables` 플래그 하나로 전체 여정을 다시 입힐 수 있습니다. 그래서 이전 캡스톤들의 단일 파일 규칙이 여기에도 그대로 적용됩니다. 즉 `index.html` 하나입니다.

새로운 변수는 세계입니다. 카메라 변환이 가로질러 가는 넓은 장면 공간 하나입니다. 영역은 여전히 시간이 정해진 `class="clip"` 구간이며, 카메라가 도착하는 순간에 맞춰 동기화되고, 프레임워크가 각자의 시간 창에 따라 보이게 하고 숨깁니다. 와이어, 룰러, 칩만 62초 내내 살아 있습니다. [변수와 템플릿화](/prompting/variables-and-templating)를 참고하세요.

## 색 두 개를 바꿔 영상 전체를 다시 입히기

```bash theme={null}
hyperframes render --variables '{"ground":"#0d1420","ink":"#c8ff3d"}' --strict-variables
```

<video controls muted loop playsinline preload="metadata" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-timeline-reskin-v2.mp4#t=0.1" style={{ borderRadius: "0.5rem", marginTop: "0.75rem" }} />

*같은 컴포지션을 네이비와 산성 그린으로 렌더링한 결과입니다. 와이어, 룰러, 차트, 지도, 글래스, 그리고 생성된 벽화까지 모두 오버라이드를 따릅니다.*

이전 캡스톤의 벽화 기법이 그대로 이어집니다. 아트워크는 그레이스케일로 생성되고, `ground`와 `ink` 변수로 구동되는 CSS 레이어가 실시간으로 듀오톤을 입힙니다. 래스터 이미지조차 다시 입혀집니다. 템플릿 프레임이 재입힘에도 살아남아야 할 때는 언제나 색은 CSS에, 형태는 래스터에 두세요.

## 프롬프트가 실제로 더하는 것

가이드를 뒤에 두고 프롬프트를 다시 읽으면 거대한 요구 하나로 보이지 않습니다. 영역별로 보면 이미 가진 재료입니다. 이 절들 중 새로운 것은 없습니다. 장들을 요구 사항으로 다시 말한 것입니다.

새로운 것은 연결 조직이며, 프롬프트의 단어 대부분이 여기에 쓰입니다.

* **촬영 계약**이 아홉 개의 데모를 하나의 공간으로 융합합니다. 이것을 빼면 장 예제들의 재생 목록이 됩니다. 남기면 같은 아홉 조각이 하나의 영화가 됩니다.
* **지속 요소가 핸드오프를 합니다.** 와이어는 각 영역이 다음 영역으로 *되게* 만드는 장치입니다. 같은 선이 타이핑된 밑줄, 차트 기준선, 지도 호, 파형, 3D 코일이 됩니다. 칩은 아홉 가지 기법 전체를 관통하는 콜백입니다. 룰러는 영상의 매체 자체를 보이게 합니다.
* **하나의 브랜드 파일이 모든 영역을 지배합니다.** 여러 장에서 가져온 아홉 가지 기법이 한 명의 디자이너가 만든 것처럼 보이게 됩니다.
* **하나의 변수 범위가 전체를 다시 입힙니다.** 차트, 지도, 글래스, 벽화, 컨페티가 모두 같은 두 변수에 응답합니다.
* **하나의 사운드트랙이 전체의 박자를 맞춥니다**([미디어와 오디오](/prompting/media-and-audio)). 내레이션이 모든 영역의 등장 타이밍을 정하고, 내레이션을 깔아 주는 같은 BGM이 리듬 영역의 비트 분석에도 쓰입니다. SFX 계획 하나가 시각적 히트를 따릅니다. 오프닝의 키 입력, 핸드오프마다의 휘익 소리, 카운터와 비트의 틱, 렌더 직전의 라이저 하나입니다.

이것이 이 가이드가 쌓아 온 방법입니다. 각 기법을 따로 배우세요. 그다음 조각을 새로 발명하는 것이 아니라 묶는 것이 목적인 프롬프트를 쓰세요. 공유된 공간, 공유된 척추, 공유된 브랜드, 공유된 변수, 공유된 시계입니다.

*다음: [규칙과 안티패턴](/prompting/rules-and-anti-patterns) — 만드는 동안 이 치트 시트를 열어 두세요.*

## 관련 주제

* [잘못 렌더링된 결과 고치기](/prompting/iterating)
* [규칙과 안티패턴](/prompting/rules-and-anti-patterns)
* [프리미엄처럼 읽히는 모션](/prompting/motion)
* [디자인 시스템과 브랜드](/prompting/design-systems)
* [변수와 템플릿화](/prompting/variables-and-templating)


## 관련 주제

- [프롬프트 가이드](/prompting/overview.md)
- [변수와 템플릿화](/prompting/variables-and-templating.md)
- [전환](/prompting/transitions.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 빌드되어 호스팅됩니다.
