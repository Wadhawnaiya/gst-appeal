# Autopilot Context Snapshot — GST appeal setup guide

Task: Create a full setup/run guide and a first-run demo for the three local GST appeal components.

Desired outcome:
- Explain how to set up and run: GST appeal drafting skill, caselaws-cli, and NotebookLM/notebooklm-py knowledge-bank integration.
- Include a first-run demo that works even before NotebookLM login, while showing the credential-gated NotebookLM step.

Known facts/evidence:
- Local root: /home/wadhawaniya/gst-appeal
- Skill path: .agents/skills/gst-appeal-drafting
- CLI path: caselaws-cli
- NotebookLM CLI present in caselaws-cli/.venv/bin/notebooklm, version 0.5.0.
- NotebookLM auth currently missing storage_state.json; login requires human browser sign-in.
- caselaws-cli tests recently passed.

Constraints:
- No destructive actions.
- Do not require user interaction for local safe steps.
- NotebookLM auth cannot be completed by agent without Google browser login.

Assumptions:
- “all these 3 things” means the GST appeal skill, the caselaws case-law CLI, and NotebookLM/notebooklm-py integration.

Likely touchpoints:
- Root guide markdown.
- demo/ shell script and sample facts.
