# Automotive engineering workflow

The automotive element is an original, unbranded SUV body and fixture illustration linked to actual read-only synthetic MES records. It is not CAD, a digital twin, an observed process sequence or a production vehicle design. No real automaker, supplier, vehicle, logo or person was added.

## What to show

Select the illustrated body or the blue Station 40 control. The Engineering workflow opens at the selected chart scope. Yield points use a production day and shift; tool means use the selected tool over all shifts on that production day.

The default Tuesday second-shift view shows 200 units built, 16 first-pass rejects across all causes, and 8 distinct units with recorded joint-limit exceptions. Five of those exception units are marked shipped and three held. These counts come from SELECTs over the seeded MES, with DISTINCT unit IDs so four failed bolt records do not become four vehicles. The query text is inspectable. The eight exception units are not the complete calibration-exposure or containment population.

Select P7-20261110-32-0041 to open its Unit passport. It shows the unit serial, tool, supplier lot, first-pass and shipping records, each of its four bolt results, nine recorded station events and the pending defect disposition. Select a bolt with a pointer or keyboard to see its precise torque and angle against the recorded limits. Shipping status is not Quality release and a recorded limit violation is not a measured joint preload.

Under Verify process, the displayed sequence is extracted from the controlled WI step 6. The walkthrough follows 1, 3, 2, 4 as an instruction reference. It does not portray an operator observation. Original WI and PFMEA text remain available alongside the maintenance CSV records. Missing confirmation paperwork is described as missing paperwork, not proof that verification never happened.

## Relevance by role

| Audience | Useful workflow connection |
| --- | --- |
| Manufacturing engineering | Locate the demo workcell, compare tool means, inspect individual bolt results, and check the instruction and PFMEA reaction plan. |
| Quality | Trace recorded exceptions to serials and shipping state, inspect the actual disposition record, and define the additional evidence needed for a containment decision. |
| Maintenance | Cross check recalibration and reference-verification records against the process signal without inventing a last known good check. |
| Plant leadership | See the scope of an investigation and the decisions still open, with no invented savings, ROI or completed containment. |
| AI and IT | Inspect the SELECT boundary and the handoffs between structured records, controlled documents, local video reasoning and an evidence-linked proposed 8D. |

## Deployment pattern

Connect the workflow maps four production source categories to the demonstrated local tools: MES and fastening controllers to a read-only query adapter, document repositories to retrieval and full-context review, camera archives to MP4 ingestion and the local vision endpoint, and Quality review to a proposed 8D with evidence links.

This is a design mapping. The demo uses DuckDB and local documents/files. No production MES, tool controller, camera archive or QMS connector is configured. It does not place holds, alter tool programs, approve release or write to a production system. Those integrations and authority boundaries would require a plant-specific implementation and validation.

The engineering views perform direct queries; they do not impersonate an AI investigation or populate an accepted golden trace. Existing Cosmos, answer-validation, report and concurrency gates remain unchanged.

## Implementation and verification

plant7/automotive.py owns the validated scope, distinct-unit aggregates, exception list and individual passport. FastAPI exposes /api/automotive/context and /api/automotive/unit/UNIT_ID. static/automotive.js binds chart selection to those endpoints and renders the views. static/automotive.css and the original static/vehicle-body.svg provide the visual layer with no third-party runtime or image dependency.

The behavioral suite checks 200 versus 16 versus 8 units, five shipped and three held, four bolt records per exception, correct tool scope, nine station records, the pending disposition, and rejection of invalid serials. scripts/check_automotive_ui.py exercises actual local data, the clickable body, nested passport, bolt keyboard interaction, normative sequence, source records, deployment labeling, scope changes and mobile overflow. It substitutes no model inference.
