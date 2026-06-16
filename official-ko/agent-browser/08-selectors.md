---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/08-selectors.md
order: 8
title: "Selectors"
---

# Selectors

## Refs(권장)

Refs는 snapshot에서 결정적인 요소 선택을 제공합니다. AI 에이전트에 가장 적합합니다.

```bash
# 1. Get snapshot with refs
agent-browser snapshot
# Output:
# - heading "Example Domain" [ref=e1] [level=1]
# - button "Submit" [ref=e2]
# - textbox "Email" [ref=e3]
# - link "Learn more" [ref=e4]

# 2. Use refs to interact
agent-browser click @e2                   # Click the button
agent-browser fill @e3 "test@example.com" # Fill the textbox
agent-browser get text @e1                # Get heading text
agent-browser hover @e4                   # Hover the link
```

### 왜 refs인가요?

- **결정적** - Ref는 snapshot의 정확한 요소를 가리킵니다
- **빠름** - DOM을 다시 쿼리할 필요가 없습니다
- **AI 친화적** - LLM이 refs를 안정적으로 파싱하고 사용할 수 있습니다

## CSS selectors

```bash
agent-browser click "#id"
agent-browser click ".class"
agent-browser click "div > button"
agent-browser click "[data-testid='submit']"
```

## Text & XPath

```bash
agent-browser click "text=Submit"
agent-browser click "xpath=//button[@type='submit']"
```

## Semantic locators

role, label 또는 기타 semantic 속성으로 요소를 찾습니다.

```bash
agent-browser find role button click --name "Submit"
agent-browser find label "Email" fill "test@test.com"
agent-browser find placeholder "Search..." fill "query"
agent-browser find testid "submit-btn" click
```
