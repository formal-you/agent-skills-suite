# Domain Note: Agent Platform Architecture (optional)

> Read this only when the product being specified is itself an agent platform or agent
> runtime. It is a domain reference, not a requirement for the PRD workflow.

## Three planes

1. **Data plane** - high-throughput interaction gateway (streaming/WebSocket), a console,
   and observability of model/tool traces. The goal is visibility into latency, cost and
   failed tool calls.
2. **Control plane** - authorization (RBAC/ABAC), secret and key management, lifecycle
   hooks (pre-action safety checks, human approval for risky actions, redaction), service
   governance (idempotent retries, checkpoint recovery, priority queues), worker registry
   and health probing.
3. **Scheduling plane** - session-affinity routing for stateful model sessions, a durable
   workflow engine for long-running tasks, and failover targets expressed as measurable
   recovery objectives.

## Runtime vs evaluation

- **Runtime plane**: event-driven execution, fault recovery, hook interception, capacity.
- **Evaluation and evolution**: sampled, redacted traces become golden evaluation sets;
  track prompt adherence, tool accuracy and cost per outcome; version prompts and workflow
  graphs; use shadow traffic and canary rollout for changes.

## When to record requirements

- If the user asks for an agent platform, these concerns are legitimate interview topics.
- Do not import them into non-agent products. They are examples of the domain, not defaults.
