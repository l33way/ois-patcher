# Security Policy

## Scope & Applicability

This policy applies **exclusively to the patcher tooling and scripts** contained in this repository (`ois_patcher.py`, `apply_data_fixes.py`, and related tools).

### In Scope
- Vulnerabilities within `ois_patcher.py` (e.g., path traversal, unsafe execution, arbitrary file writes).
- Patcher update-checking and execution routines.

### Out of Scope
- **The base game (*Objects in Space*):** This project is an unofficial community fix patch. We are not Flat Earth Games and do not own, maintain, or provide security guarantees for the commercial game binaries or base network protocol.
- Security vulnerabilities inherent to the original, unpatched 1.0.8 game engine.

## Reporting a Vulnerability

If you discover a security issue in the patcher script itself:
1. Please **do not** open a public GitHub issue.
2. Report the issue privately using **GitHub Private Vulnerability Reporting** on this repository (or email the maintainers directly).
3. Provide details of the environment, proof of concept, and potential impact. We will review and patch verified security flaws promptly.
