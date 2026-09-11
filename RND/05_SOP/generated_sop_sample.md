# Standard Operating Procedure (SOP) Sample Deliverable

**Document ID:** `SOP-MIL-2026-001`  
**Title (EN):** Precision Vertical Milling Machine - Standard Operating Procedure  
**Title (JA):** 精密立型フライス盤 - 標準作業手順書  
**Version:** 1.0.0 (Dual-Grounded Prototype Export)  
**Governance Status:** `DRAFT — Pending Expert Review`  
**Approval Hash:** `NOT GENERATED — no human approval event has occurred`  
**Generation Engine:** `groq:openai/gpt-oss-120b` (EN-first + Translation Pipeline)  

---

## Step 1: Spindle Speed Setting & Engagement Verification

* **Instruction (EN):** Ensure the spindle is rotating clockwise at maximum 1800 RPM before engaging the workpiece.
* **Instruction (JA):** ワークピースを切削する前に、主軸が時計回りに最大1800 RPMで回転していることを確認してください。
* **Video Timestamp:** `00:00:00 - 00:00:10`
* **Selected Frame:** `OpenCV_ts_0.0s.jpg`
* **Evidence Grounding:**
  - *Video Source:* `test_instructional_normal.mp4` @ `00:00:00`
  - *Document Citation:* `milling_machine_operating_manual.pdf` (Section 3.2, p1)
* **Safety Warning:** Operating the spindle at speeds exceeding 1800 RPM is strictly prohibited.
* **Traceability Status:** `DUAL_GROUNDED_VERIFIED`

---

## Step 2: Workpiece Clamping & Table Securing

* **Instruction (EN):** Securely clamp the workpiece to the machine table before starting the cut.
* **Instruction (JA):** 切削を開始する前に、ワークピースを作業台に確実に固定してください。
* **Video Timestamp:** `00:01:15`
* **Selected Frame:** `estimated_ts_75.0s`
* **Evidence Grounding:**
  - *Video Source:* `test_instructional_normal.mp4` @ `00:01:15`
  - *Document Citation:* `milling_machine_operating_manual.pdf` (Section 4.2, p3)
* **Safety Warning:** Lock vise clamp securely before starting the spindle.
* **Traceability Status:** `PARTIAL_TEXT_ONLY`
