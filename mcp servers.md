Utilize the MCP server tools listed below to full effect.

### Gnosis MCP
Gnosis MCP Server Tools: AI Agent Usage Guide
1. Metrics & Monitoring
Endpoints: Query available API endpoints and their usage.
Hot Endpoints: Discover most accessed endpoints for optimization.
Recent Requests: Review recent API calls for debugging or analytics.
Slow Endpoints: Identify endpoints with high latency.
Summary: Get an overall metrics summary for health checks.

2. Notes & Summarization
Append Notes: Store structured notes with tags (e.g., decisions, questions).
List Notes: Retrieve all notes and their revisions.
Rollback Notes: Restore notes to previous versions.
Summarize Notes: Generate summaries for individual or batch notes.

3. Task & Priority Management
Create Tasks: Add new tasks with status, owner, and due date.
List Tasks: Retrieve all tasks, filter by status or due date.
Update Tasks: Change status, owner, or details of tasks.
Priorities: Add items to a priority queue and get top items by urgency or recency.

4. Memory Management
Put Memory: Store key-value pairs with TTL for session or project context.
Query Memory: Search stored memories by namespace and query string.

5. File Processing
Read/Replace: Read specific lines or ranges, replace text (literal/regex), preview content.
Search: Search files by glob or regex patterns.
Diff/Sync: Compute and apply unified diffs for version control.

### Nova-16 MCP
Nova-16 MCP Server Tools: AI Agent Usage Guide

1. Assembly & Disassembly
Assemble Nova-16 assembly code (.asm) to binary (.bin)
Disassemble binaries to readable assembly
Load programs into emulator memory
Export symbol tables for debugging

2. Execution & Debugging
Run, step, or halt CPU execution
Set, list, and clear breakpoints
Inspect current instruction, registers, and flags
Print CPU state and memory

3. Memory Management
Read/write memory bytes directly
Create memory dumps for debugging
Search memory for hex patterns
Assert memory values at addresses

4. Graphics & Sound
Export screen as PNG or raw buffer
Set/get pixel colors in graphics buffer
Control sound playback (address, frequency, volume, waveform)

5. Keyboard & Input
Access keyboard buffer
Inject keypresses or ASCII strings
Simulate user input for testing

6. System Control
Reset CPU, memory, or complete system
Configure timer registers
Manage stack and interrupt vectors

Utilize the gnosis MCP server tools while developing this codebase. Utilize the Nova-16 MCP server tools for all emulator, assembly, debugging, and memory operations. Only use other tools if these fail or are unavailable.