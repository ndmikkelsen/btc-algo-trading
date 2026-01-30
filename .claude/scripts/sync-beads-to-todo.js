#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const TODO_FILE = path.join(__dirname, '../../to-do.md');

function getBeadsIssues() {
  try {
    const output = execSync('bd list --all --json', { encoding: 'utf-8' });
    return JSON.parse(output);
  } catch (error) {
    console.error('Error fetching beads issues:', error.message);
    console.error('Aborting sync to prevent data loss');
    process.exit(1);
  }
}

function mapPriorityToTag(priority) {
  const map = {
    0: '#p0',
    1: '#p1',
    2: '#p2',
  };
  return map[priority] || '#p2';
}

function mapEffortToMetadata(estimatedMinutes) {
  if (!estimatedMinutes) return null;
  if (estimatedMinutes < 60) return 'low';
  if (estimatedMinutes <= 240) return 'medium';
  return 'high';
}

function formatTask(issue) {
  const checkbox = issue.status === 'done' || issue.status === 'closed' ? '[x]' : '[ ]';
  const priorityTag = issue.priority !== undefined ? mapPriorityToTag(issue.priority) : '';
  const effort = mapEffortToMetadata(issue.estimated_minutes);
  const effortMeta = effort ? `[effort:: ${effort}]` : '';
  
  let taskLine = `- ${checkbox} ${issue.title}`;
  
  if (priorityTag) taskLine += ` ${priorityTag}`;
  if (effortMeta) taskLine += ` ${effortMeta}`;
  
  if (issue.description && issue.description.trim()) {
    const descLines = issue.description.trim().split('\n');
    const blockQuote = descLines.map(line => `  > ${line}`).join('\n');
    taskLine += `\n${blockQuote}`;
  }
  
  return taskLine;
}

function generateTodoMd(issues) {
  const sections = {
    p2: [],
    p1: [],
    p0: [],
    inProgress: [],
    done: [],
  };

  issues.forEach(issue => {
    const formattedTask = formatTask(issue);
    
    if (issue.status === 'done' || issue.status === 'closed') {
      sections.done.push(formattedTask);
    } else if (issue.status === 'in_progress') {
      sections.inProgress.push(formattedTask);
    } else {
      const priority = issue.priority !== undefined ? issue.priority : 2;
      if (priority === 0) {
        sections.p0.push(formattedTask);
      } else if (priority === 1) {
        sections.p1.push(formattedTask);
      } else {
        sections.p2.push(formattedTask);
      }
    }
  });

  const content = `---
id: to-do-list
aliases:
  - to-do
tags:
  - to-do
  - kanban
kanban-plugin: board
---

## Low Priority - #p2

${sections.p2.join('\n') || ''}

## Medium Priority - #p1

${sections.p1.join('\n') || ''}

## High Priority - #p0

${sections.p0.join('\n') || ''}

## In Progress

${sections.inProgress.join('\n') || ''}

## Done

${sections.done.join('\n') || ''}

%% kanban:settings

\`\`\`json
{
  "kanban-plugin": "board",
  "list-collapse": [false, false, false, false, true],
  "show-checkboxes": true,
  "show-card-footer": true,
  "tag-sort-order": ["p0", "p1", "p2"],
  "date-format": "YYYY-MM-DD"
}
\`\`\`

%%
`;

  return content;
}

function main() {
  console.log('Syncing beads issues to to-do.md...');
  
  const issues = getBeadsIssues();
  console.log(`Found ${issues.length} issues in beads`);
  
  const todoContent = generateTodoMd(issues);
  
  fs.writeFileSync(TODO_FILE, todoContent, 'utf-8');
  console.log(`✓ Updated ${TODO_FILE}`);
}

main();
