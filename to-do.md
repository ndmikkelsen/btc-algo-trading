---
id: to-do-list
aliases:
  - to-do
tags:
  - to-do
  - kanban
kanban-plugin: board
---

## Low Priority - #p2

- [ ] Optimize BTCMomentumScalper strategy parameters #p2

## Medium Priority - #p1

## High Priority - #p0

## In Progress

## Done

- [x] Configure Cognee knowledge base for btc-algo-trading #p1
  > Set up isolated Cognee stack with unique ports, update all scripts and documentation to use btc-specific datasets and configuration.

%% kanban:settings

```json
{
  "kanban-plugin": "board",
  "list-collapse": [false, false, false, false, true],
  "show-checkboxes": true,
  "show-card-footer": true,
  "tag-sort-order": ["p0", "p1", "p2"],
  "date-format": "YYYY-MM-DD"
}
```

%%
