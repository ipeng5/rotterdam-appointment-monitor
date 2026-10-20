# Prins Alexander cloud test

This is a **one-time, manually triggered test**, not a scheduled monitor. It does not send Telegram messages or book appointments.

1. Create a **private** GitHub repository.
2. Upload `check.py` to the repository root.
3. Upload `.github/workflows/check.yml` with exactly this directory structure (GitHub web upload supports dragging the entire folder, or use Git locally).
4. Open **Actions** > **Test Prins Alexander availability** > **Run workflow**.
5. Open the run's **check** job and read the result. `RESULT: EMPTY` means the card was found but no times were shown; `RESULT: POSSIBLY AVAILABLE` means the page displayed a `vanaf` time; `UNKNOWN` or failure means the test did not verify availability.

The job uploads a screenshot as an artifact to aid debugging. Do not share screenshots if they contain personal information or session identifiers.

Note: The municipal site may change, block headless browsers, or require a session. A passing test does not guarantee reliable continuous operation. Respect website rate limits and terms.
