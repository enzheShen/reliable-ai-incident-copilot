# Error budget policy

For the 99.5% monthly success target, the error budget is **0.5% of valid requests**. For example, 100,000 valid requests permit 500 failed requests in the measurement window. Time-based shorthand is about 3 hours 36 minutes in a 30-day month, but the service indicator is request-based.

Burn rate is the observed error rate divided by the allowed 0.5% error rate. A 1% error rate burns budget at 2×; a 5% error rate burns it at 10×.

## Response policy

- At 2× burn over 24 hours, prioritise reliability work and review recent changes.
- At 6× burn over 6 hours, pause risky feature releases and assign an incident owner.
- At 14× burn over 1 hour, stop feature releases, mitigate immediately, and run the incident process.
- Resume feature releases only after the fast burn has stopped, the cause is understood, and remaining budget supports the change.

Client validation errors are excluded. Fallback responses count as successful availability responses, while fallback rate remains a separate quality and dependency-health signal.
