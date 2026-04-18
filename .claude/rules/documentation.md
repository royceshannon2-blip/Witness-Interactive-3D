# Documentation & Architecture Standards

You are required to maintain a real-time map of the system architecture and a detailed change log.

## Mandatory Actions
1. **Update `ARCHITECTURE.md`**: After any change that introduces a new service, database schema, or API contract, you must update the Mermaid diagrams and component descriptions in `ARCHITECTURE.md`.
2. **Atomic Change Logs**: Every time you successfully complete a task, append a technical summary to `docs/decisions/CHANGELOG_DETAILED.md`.
3. **Traceability**: Ensure every new function or class is documented with docstrings that explain its role in the larger architecture.

## Architecture Map Format
Always use Mermaid.js for diagrams to ensure they remain version-controlled and readable.
