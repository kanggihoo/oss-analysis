<!-- ppt-master-schema: spec-lock/v1 -->
# Execution Lock

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## communication
- primary_language: ko-KR
- audience: 백엔드 채용 담당자와 면접관
- objective: 4년차 백엔드 개발자의 문제 해결 방식을 프로젝트 근거와 함께 소개해, 면접관이 두 프로젝트의 문제·조치·수치 결과를 이해하고 면접 기회를 주게 한다
- core_message: 측정으로 병목을 찾아 수치로 개선하는 백엔드 개발자

## mode
- mode: custom
- mode_references: pyramid
- mode_behavior: Use pyramid as the only basis. Every page title states a finding in a full sentence, for example 'p95 latency fell from 1.8 s to 0.4 s'. Each project gets a problem and cause page, then an action and result page, so the interviewer reads the answer before the process. Keep the closing page to one sentence of direction and contact lines.

## visual_style
- visual_style: custom
- visual_style_references: swiss-minimal
- visual_style_behavior: Use swiss-minimal as the only basis: a modular grid, square corners, single-weight rules, near-white field, and one oversized numeral or color column per page that zones the layout. The accent color marks only the 'after' number. No gradients, no shadows, no decorative badges.

## colors
- bg: #FFFFFF
- secondary_bg: #F3F5F8
- primary: #17305A
- accent: #E58A00
- secondary_accent: #5A7FB0
- text: #1B2330
- secondary_text: #566176
- divider: #D3D9E2

## typography
- font_family: Malgun Gothic, Arial, sans-serif
- title_family: Malgun Gothic, Arial, sans-serif
- body_family: Malgun Gothic, Arial, sans-serif
- body: 24
- title: 42
- subtitle: 32
- annotation: 18
- footnote: 16
- cover_title: 72
- display: 96

## icons
- library: tabler-outline
- stroke_width: 2
- inventory: tabler-outline/gauge, tabler-outline/database, tabler-outline/rocket, tabler-outline/server, tabler-outline/mail, tabler-outline/user, tabler-outline/code, tabler-outline/chart-line, tabler-outline/git-branch, tabler-outline/check

## page_rhythm
- P01: anchor
- P02: breathing
- P03: dense
- P04: dense
- P05: dense
- P06: dense
- P07: anchor

## pptx_structure
- mode: flat

## page_visualizations
- P06: table/record_table

## forbidden
- `mask`, `<style>`, `class`, external CSS, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<set>`, `<script>` / event attributes, `<iframe>`
- HTML named entities in text; write typography as raw Unicode and escape XML reserved characters
