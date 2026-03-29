"""
Multi-agent framework for OmniCare Clinical Copilot.

Provides 5 specialised clinical agents + an orchestrator:
  - ConsultationAgent:  Audio → Transcript → SOAP note
  - HeARAgent:          Audio → Respiratory event detection → Suggestions
  - VitalsMonitorAgent: FHIR vitals → Anomaly detection → Alerts
  - RadiologyAgent:     Medical image → Radiology report
  - DischargeAgent:     Aggregate all stages → Discharge summary + ICD-10

All agents share state through Firestore (via firestore_db module).
The ClinicalOrchestrator coordinates the pipeline and can run agents
in parallel where their inputs are independent.
"""

from datetime import datetime
from typing import Optional

try:
    import torch  # type: ignore
except ImportError:
    pass


# ===================================================================
# Base class
# ===================================================================

class ClinicalAgent:
    """Base class for all clinical agents."""

    name: str = "base"
    role: str = "Generic clinical agent"

    def __init__(self, models: dict = None):
        """
        Args:
            models: Dict of loaded models, e.g.
                    {"medgemma_model": ..., "medgemma_processor": ...,
                     "asr_pipeline": ..., "hear_model": ..., "hear_preprocess": ...}
        """
        self.models = models or {}

    def process(self, encounter_id: str, context: dict) -> dict:
        """
        Run the agent's task.

        Args:
            encounter_id: Current encounter ID.
            context: Dict of inputs specific to this agent.

        Returns:
            Dict of results to merge into the encounter.
        """
        raise NotImplementedError

    def _log(self, encounter_id: str, action: str, details: str = ""):
        """Log agent activity to Firestore."""
        try:
            from .firestore_db import log_agent_action
            log_agent_action(encounter_id, self.name, action, details)
        except Exception:
            print(f"[{self.name}] {action}: {details}")

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name!r}>"


# ===================================================================
# ConsultationAgent
# ===================================================================

class ConsultationAgent(ClinicalAgent):
    """
    Handles the consultation phase:
      Audio file → Whisper ASR → Transcript → MedGemma → SOAP note

    Context keys:
      - audio_path (str): Path to WAV/MP3 file, OR
      - transcript (str): Pre-existing transcript (skips ASR)
      - use_dynamic (bool): If True, generate transcript from scenario via MedGemma
      - scenario (dict): Patient scenario for dynamic generation

    Returns:
      {"transcript": str, "soap_note": dict, "soap_raw": str}
    """

    name = "consultation_agent"
    role = "Audio transcription and SOAP note generation"

    def process(self, encounter_id: str, context: dict) -> dict:
        from .mcp_tools import transcribe_audio, generate_soap_note, parse_soap_sections
        from .prompts import WHISPER_MEDICAL_PROMPT

        self._log(encounter_id, "started", "Beginning consultation processing")

        # Step 1: Get transcript
        transcript = context.get("transcript")

        if not transcript and context.get("use_dynamic") and context.get("scenario"):
            from .patient_simulator import generate_dynamic_transcript
            self._log(encounter_id, "generating_transcript",
                      "Using MedGemma to generate dynamic transcript")
            transcript = generate_dynamic_transcript(
                context["scenario"],
                model=self.models.get("medgemma_model"),
                processor=self.models.get("medgemma_processor"),
            )

        if not transcript and context.get("audio_path"):
            self._log(encounter_id, "transcribing",
                      f"ASR on {context['audio_path']}")
            transcript = transcribe_audio(
                audio_path=context["audio_path"],
                asr_pipeline=self.models["asr_pipeline"],
                medical_prompt=WHISPER_MEDICAL_PROMPT,
            )

        if not transcript:
            raise ValueError("ConsultationAgent: No audio_path, transcript, or scenario provided.")

        # Step 2: Generate SOAP note
        self._log(encounter_id, "generating_soap",
                  f"Transcript length: {len(transcript)} chars")
        soap_raw = generate_soap_note(
            transcript=transcript,
            model=self.models["medgemma_model"],
            processor=self.models["medgemma_processor"],
        )

        # Step 3: Parse SOAP sections
        soap_sections = parse_soap_sections(soap_raw)

        # Step 4: Persist to Firestore
        try:
            from .firestore_db import update_stage
            update_stage(encounter_id, "consultation", {
                "audio_file": context.get("audio_path"),
                "transcript": transcript,
                "soap_note": soap_sections,
            })
        except Exception as e:
            print(f"[ConsultationAgent] Firestore save warning: {e}")

        self._log(encounter_id, "completed",
                  f"SOAP generated ({sum(len(v) for v in soap_sections.values())} chars)")

        return {
            "transcript": transcript,
            "soap_note": soap_sections,
            "soap_raw": soap_raw,
        }


# ===================================================================
# HeARAgent
# ===================================================================

class HeARAgent(ClinicalAgent):
    """
    Monitors audio for respiratory events using Google's HeAR model.

    Context keys:
      - audio_path (str): Path to audio file
      - transcript (str): Consultation transcript (for clinical context)

    Returns:
      {"hear_events": list, "hear_summary": str, "clinical_suggestion": str}
    """

    name = "hear_agent"
    role = "Respiratory sound analysis and cough detection"

    def process(self, encounter_id: str, context: dict) -> dict:
        from .hear_helpers import (
            analyze_audio_for_respiratory_events,
            generate_clinical_suggestion,
        )

        audio_path = context.get("audio_path")
        if not audio_path:
            self._log(encounter_id, "skipped", "No audio_path provided")
            return {"hear_events": [], "hear_summary": "No audio for HeAR analysis.",
                    "clinical_suggestion": ""}

        self._log(encounter_id, "analyzing", f"HeAR analysis on {audio_path}")

        # Run HeAR pipeline
        result = analyze_audio_for_respiratory_events(
            audio_path=audio_path,
            model=self.models["hear_model"],
            preprocess_fn=self.models["hear_preprocess"],
            device=str(self.models.get("device", "cuda")),
        )

        events = result["events"]
        summary = result["summary"]

        # Generate clinical suggestion if events detected
        suggestion = ""
        if events:
            self._log(encounter_id, "events_detected",
                      f"{len(events)} respiratory events found")
            transcript = context.get("transcript", "")
            suggestion = generate_clinical_suggestion(
                events=events,
                transcript=transcript,
                model=self.models["medgemma_model"],
                processor=self.models["medgemma_processor"],
            )

        # Persist HeAR findings
        try:
            from .firestore_db import load_encounter, update_stage
            enc = load_encounter(encounter_id)
            existing_findings = enc["stages"]["consultation"].get("hear_findings", [])
            existing_findings.extend(events)
            update_stage(encounter_id, "consultation", {
                "hear_findings": existing_findings,
            })
        except Exception as e:
            print(f"[HeARAgent] Firestore save warning: {e}")

        self._log(encounter_id, "completed", summary)

        return {
            "hear_events": events,
            "hear_summary": summary,
            "clinical_suggestion": suggestion,
        }


# ===================================================================
# VitalsMonitorAgent
# ===================================================================

class VitalsMonitorAgent(ClinicalAgent):
    """
    Monitors patient vitals from FHIR data, detects anomalies,
    and generates an admission note.

    Context keys:
      - patient_id (str): FHIR Patient ID
      - fhir_bundle_path (str): Local FHIR bundle file, OR
      - use_fhir_server (bool): Query from Healthcare API
      - soap_note (dict): SOAP from consultation (for admission note)
      - scenario (dict): Patient scenario (for allergies etc.)

    Returns:
      {"vitals": list, "conditions": list, "medications": list,
       "anomalies": list, "admission_note": str}
    """

    name = "vitals_monitor_agent"
    role = "Vitals monitoring, anomaly detection, and admission note generation"

    # Normal vital ranges
    NORMAL_RANGES = {
        "Body temperature": (97.0, 99.5, "degF"),
        "Heart rate": (60, 100, "bpm"),
        "Respiratory rate": (12, 20, "breaths/min"),
        "Oxygen saturation (SpO2)": (95, 100, "%"),
        "Blood pressure panel - Systolic": (90, 140, "mmHg"),
        "Blood pressure panel - Diastolic": (60, 90, "mmHg"),
    }

    def process(self, encounter_id: str, context: dict) -> dict:
        from .fhir_helpers import (
            parse_fhir_bundle, extract_vitals, extract_conditions,
            extract_medications, extract_patient_demographics,
            format_vitals_summary,
        )
        from .mcp_tools import generate_admission_note

        self._log(encounter_id, "started", "Beginning vitals monitoring")

        # Step 1: Get FHIR data
        if context.get("use_fhir_server"):
            self._log(encounter_id, "querying_fhir", "Fetching from Healthcare API")
            from .healthcare_api import query_vitals, query_conditions, query_medications
            patient_id = context["patient_id"]
            raw_vitals = query_vitals(patient_id)
            raw_conditions = query_conditions(patient_id)
            raw_medications = query_medications(patient_id)
            vitals = extract_vitals(raw_vitals)
            conditions = extract_conditions(raw_conditions)
            medications = extract_medications(raw_medications)
            demographics = context.get("demographics", {})
        else:
            bundle_path = context.get("fhir_bundle_path")
            if bundle_path:
                resources = parse_fhir_bundle(bundle_path)
            else:
                # Generate from scenario
                from .patient_simulator import generate_fhir_bundle
                import json, tempfile, os
                bundle = generate_fhir_bundle(context["scenario"])
                bundle_path = os.path.join(tempfile.gettempdir(), "scenario_bundle.json")
                with open(bundle_path, "w") as f:
                    json.dump(bundle, f)
                resources = parse_fhir_bundle(bundle_path)

            demographics = (extract_patient_demographics(resources["patients"][0])
                            if resources["patients"] else {})
            vitals = extract_vitals(resources["observations"])
            conditions = extract_conditions(resources["conditions"])
            medications = extract_medications(resources["medications"])

        # Step 2: Detect anomalies
        anomalies = self._detect_anomalies(vitals)
        if anomalies:
            self._log(encounter_id, "anomalies_detected",
                      f"{len(anomalies)} vital sign anomalies")

        # Step 3: Generate admission note
        soap_note = context.get("soap_note", {})
        soap_text = "\n".join(f"{k.upper()}: {v}" for k, v in soap_note.items() if v)
        if not soap_text:
            soap_text = "No consultation SOAP note available."

        vitals_summary = format_vitals_summary(vitals)
        demographics_str = (f"Name: {demographics.get('name', 'N/A')}, "
                            f"DOB: {demographics.get('dob', 'N/A')}, "
                            f"Gender: {demographics.get('gender', 'N/A')}")
        conditions_str = "\n".join(f"- {c['display']}" for c in conditions) or "None"
        medications_str = "\n".join(f"- {m['display']}" for m in medications) or "None"
        allergies = context.get("scenario", {}).get("allergies", "NKDA")

        self._log(encounter_id, "generating_admission_note",
                  f"Vitals: {len(vitals)}, Conditions: {len(conditions)}")

        admission_note = generate_admission_note(
            demographics=demographics_str,
            soap_note=soap_text,
            vitals=vitals_summary,
            conditions=conditions_str,
            medications=medications_str,
            allergies=allergies,
            model=self.models["medgemma_model"],
            processor=self.models["medgemma_processor"],
        )

        # Step 4: Persist to Firestore
        try:
            from .firestore_db import update_stage, add_vital, add_medication, add_condition
            update_stage(encounter_id, "admission", {
                "fhir_patient_id": context.get("patient_id", demographics.get("mrn", "")),
                "vitals_history": vitals,
                "conditions": conditions,
                "medications": medications,
                "admission_note": admission_note,
                "anomalies": anomalies,
            })
            # Also store in subcollections for querying
            for v in vitals:
                add_vital(encounter_id, v.get("code", ""), v["display"],
                          v["value"], v["unit"], v.get("timestamp", ""))
            for m in medications:
                add_medication(encounter_id, m["display"], m.get("status", "active"))
            for c in conditions:
                add_condition(encounter_id, c["display"], c.get("code", ""),
                              c.get("onset", ""), c.get("status", "active"))
        except Exception as e:
            print(f"[VitalsMonitorAgent] Firestore save warning: {e}")

        self._log(encounter_id, "completed",
                  f"Admission note generated, {len(anomalies)} anomalies detected")

        return {
            "vitals": vitals,
            "conditions": conditions,
            "medications": medications,
            "demographics": demographics,
            "anomalies": anomalies,
            "admission_note": admission_note,
            "vitals_summary": vitals_summary,
        }

    def _detect_anomalies(self, vitals: list) -> list:
        """Check vitals against normal ranges."""
        anomalies = []
        for v in vitals:
            display = v["display"]
            value = v["value"]
            for name, (low, high, unit) in self.NORMAL_RANGES.items():
                if name.lower() in display.lower():
                    if value < low:
                        anomalies.append({
                            "vital": display, "value": value, "unit": v["unit"],
                            "status": "LOW",
                            "message": f"{display} is {value} {v['unit']} (normal: {low}-{high})",
                        })
                    elif value > high:
                        anomalies.append({
                            "vital": display, "value": value, "unit": v["unit"],
                            "status": "HIGH",
                            "message": f"{display} is {value} {v['unit']} (normal: {low}-{high})",
                        })
                    break
        return anomalies


# ===================================================================
# RadiologyAgent
# ===================================================================

class RadiologyAgent(ClinicalAgent):
    """
    Analyses medical images using MedGemma multimodal.

    Context keys:
      - image_path (str): Path to DICOM/PNG/JPG image
      - image (PIL.Image): Pre-loaded image (alternative to image_path)
      - clinical_context (str): Clinical context for the radiologist
      - modality (str): Imaging modality (X-ray, CT, MRI)
      - body_part (str): Body part imaged
      - upload_to_dicom (bool): Upload to Healthcare API DICOM store

    Returns:
      {"radiology_report": str, "dicom_id": str or None}
    """

    name = "radiology_agent"
    role = "Medical image analysis and radiology report generation"

    def process(self, encounter_id: str, context: dict) -> dict:
        from .mcp_tools import analyze_medical_image

        self._log(encounter_id, "started", "Beginning radiology analysis")

        # Step 1: Load image
        image = context.get("image")
        image_path = context.get("image_path")
        metadata = {}

        if image is None and image_path:
            from .dicom_helpers import load_medical_image
            image, metadata = load_medical_image(image_path)

        if image is None:
            raise ValueError("RadiologyAgent: No image or image_path provided.")

        modality = context.get("modality", metadata.get("modality", "X-ray"))
        body_part = context.get("body_part", metadata.get("body_part", "Chest"))
        clinical_context = context.get("clinical_context", "")

        # Step 2: Upload to DICOM store (optional)
        dicom_id = None
        if context.get("upload_to_dicom") and image_path:
            try:
                from .healthcare_api import upload_dicom_instance
                result = upload_dicom_instance(image_path)
                dicom_id = result.get("ID", "uploaded")
                self._log(encounter_id, "dicom_uploaded", f"ID: {dicom_id}")
            except Exception as e:
                print(f"[RadiologyAgent] DICOM upload warning: {e}")

        # Step 3: MedGemma analysis
        self._log(encounter_id, "analyzing_image",
                  f"Modality: {modality}, Body part: {body_part}")
        report = analyze_medical_image(
            image=image,
            clinical_context=clinical_context,
            modality=modality,
            body_part=body_part,
            model=self.models["medgemma_model"],
            processor=self.models["medgemma_processor"],
        )

        # Step 4: Persist
        try:
            from .firestore_db import update_stage, load_encounter
            enc = load_encounter(encounter_id)
            images = enc["stages"]["radiology"].get("images", [])
            reports = enc["stages"]["radiology"].get("reports", [])
            images.append({
                "path": image_path,
                "modality": modality,
                "body_part": body_part,
                "dicom_id": dicom_id,
            })
            reports.append({"findings": report})
            update_stage(encounter_id, "radiology", {
                "images": images, "reports": reports,
            })
        except Exception as e:
            print(f"[RadiologyAgent] Firestore save warning: {e}")

        self._log(encounter_id, "completed",
                  f"Report generated ({len(report)} chars)")

        return {
            "radiology_report": report,
            "dicom_id": dicom_id,
            "modality": modality,
            "body_part": body_part,
        }


# ===================================================================
# DischargeAgent
# ===================================================================

class DischargeAgent(ClinicalAgent):
    """
    Aggregates all clinical data and generates discharge summary + ICD-10 codes.

    Context keys:
      (none required — pulls everything from Firestore)

    Returns:
      {"discharge_summary": str, "icd10_codes": list}
    """

    name = "discharge_agent"
    role = "Discharge summary generation and ICD-10 coding"

    def process(self, encounter_id: str, context: dict) -> dict:
        from .mcp_tools import generate_discharge_summary
        from .fhir_helpers import format_vitals_summary

        self._log(encounter_id, "started", "Aggregating encounter data")

        # Step 1: Load full encounter from Firestore
        try:
            from .firestore_db import load_encounter
            encounter = load_encounter(encounter_id)
        except Exception:
            encounter = context.get("encounter", {})

        stages = encounter.get("stages", {})
        consultation = stages.get("consultation", {})
        admission = stages.get("admission", {})
        radiology = stages.get("radiology", {})

        # Step 2: Format inputs
        soap = consultation.get("soap_note", {})
        if isinstance(soap, dict):
            soap_text = "\n".join(
                f"**{k.title()}:** {v}" for k, v in soap.items() if v
            )
        else:
            soap_text = str(soap)
        if not soap_text.strip():
            soap_text = "No consultation note available."

        admission_note = admission.get("admission_note", "No admission note.")
        vitals_history = admission.get("vitals_history", [])
        vitals_trend = format_vitals_summary(vitals_history)

        radiology_reports = ""
        for i, report in enumerate(radiology.get("reports", []), 1):
            findings = report.get("findings", "No findings")
            radiology_reports += f"\nReport {i}:\n{findings}\n"
        if not radiology_reports.strip():
            radiology_reports = "No radiology reports available."

        # Include HeAR findings if present
        hear_findings = consultation.get("hear_findings", [])
        hear_text = ""
        if hear_findings:
            hear_text = "\n\n=== RESPIRATORY ACOUSTIC ANALYSIS (HeAR) ===\n"
            for e in hear_findings:
                hear_text += (f"- {e['event_type']} at "
                              f"{e['start_sec']:.1f}–{e['end_sec']:.1f}s "
                              f"(confidence: {e['confidence']:.0%})\n")

        # Step 3: Generate discharge summary
        self._log(encounter_id, "generating_summary",
                  f"SOAP: {len(soap_text)}ch, Admission: {len(str(admission_note))}ch, "
                  f"Radiology: {len(radiology_reports)}ch")

        discharge_summary = generate_discharge_summary(
            soap_note=soap_text,
            admission_note=str(admission_note) + hear_text,
            vitals_trend=vitals_trend,
            radiology_reports=radiology_reports,
            model=self.models["medgemma_model"],
            processor=self.models["medgemma_processor"],
            max_new_tokens=1536,
        )

        # Step 4: Extract ICD-10 codes
        icd10_codes = self._extract_icd10(
            conditions=admission.get("conditions", []),
            soap=soap,
            discharge_summary=discharge_summary,
        )

        # Step 5: Persist
        medications = admission.get("medications", [])
        meds_at_discharge = [m.get("display", "") for m in medications if m.get("display")]

        try:
            from .firestore_db import update_stage, update_encounter_status
            update_stage(encounter_id, "discharge", {
                "summary": discharge_summary,
                "icd10_codes": icd10_codes,
                "medications_at_discharge": meds_at_discharge,
                "follow_up": "Follow-up appointment in 1 week. Return if symptoms worsen.",
            })
            update_encounter_status(encounter_id, "discharged")
        except Exception as e:
            print(f"[DischargeAgent] Firestore save warning: {e}")

        self._log(encounter_id, "completed",
                  f"Discharge summary generated, {len(icd10_codes)} ICD-10 codes")

        return {
            "discharge_summary": discharge_summary,
            "icd10_codes": icd10_codes,
            "medications_at_discharge": meds_at_discharge,
        }

    def _extract_icd10(self, conditions: list, soap: dict,
                       discharge_summary: str) -> list:
        """Map diagnoses to ICD-10 codes using keyword matching."""
        diagnosis_map = {
            "pneumonia": {"code": "J18.9", "description": "Pneumonia, unspecified organism"},
            "type 2 diabetes": {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
            "hypertension": {"code": "I10", "description": "Essential (primary) hypertension"},
            "cough": {"code": "R05.9", "description": "Cough, unspecified"},
            "fever": {"code": "R50.9", "description": "Fever, unspecified"},
            "copd": {"code": "J44.1", "description": "COPD with acute exacerbation"},
            "chronic obstructive": {"code": "J44.1", "description": "COPD with acute exacerbation"},
            "asthma": {"code": "J45.41", "description": "Moderate persistent asthma with acute exacerbation"},
            "chest pain": {"code": "R07.9", "description": "Chest pain, unspecified"},
            "coronary artery": {"code": "I25.10", "description": "Atherosclerotic heart disease"},
            "urinary tract infection": {"code": "N39.0", "description": "Urinary tract infection, site not specified"},
            "dysuria": {"code": "R30.0", "description": "Dysuria"},
            "hyperlipidemia": {"code": "E78.5", "description": "Hyperlipidemia, unspecified"},
            "allergic rhinitis": {"code": "J30.9", "description": "Allergic rhinitis, unspecified"},
            "osteoarthritis": {"code": "M17.9", "description": "Osteoarthritis of knee, unspecified"},
            "gerd": {"code": "K21.0", "description": "Gastro-esophageal reflux disease with esophagitis"},
        }

        assessment = soap.get("assessment", "") if isinstance(soap, dict) else ""
        diagnoses_text = " ".join(c.get("display", "") for c in conditions)
        combined = (diagnoses_text + " " + assessment + " " + discharge_summary).lower()

        codes = []
        seen = set()
        for keyword, code_info in diagnosis_map.items():
            if keyword in combined and code_info["code"] not in seen:
                codes.append(code_info)
                seen.add(code_info["code"])

        return codes


# ===================================================================
# ClinicalOrchestrator
# ===================================================================

class ClinicalOrchestrator:
    """
    Coordinates all clinical agents through the patient encounter pipeline.

    Usage:
        orchestrator = ClinicalOrchestrator(models={"medgemma_model": ..., ...})
        eid = orchestrator.start_encounter(scenario)
        orchestrator.run_consultation(audio_path="...", or transcript="...")
        orchestrator.run_admission()
        orchestrator.run_radiology(image_path="...")
        orchestrator.run_discharge()
    """

    def __init__(self, models: dict):
        """
        Args:
            models: Dict of loaded models shared by all agents.
        """
        self.models = models
        self.agents = {
            "consultation": ConsultationAgent(models),
            "hear": HeARAgent(models),
            "vitals": VitalsMonitorAgent(models),
            "radiology": RadiologyAgent(models),
            "discharge": DischargeAgent(models),
        }
        self.encounter_id = None
        self.scenario = None
        self._results = {}

    def start_encounter(self, scenario: dict = None,
                        patient_name: str = "", mrn: str = "",
                        dob: str = "") -> str:
        """
        Create a new encounter in Firestore.

        Args:
            scenario: Patient scenario from patient_simulator.
            patient_name/mrn/dob: Manual patient info (if no scenario).

        Returns:
            encounter_id
        """
        from .firestore_db import new_encounter_id, blank_encounter, save_encounter

        self.encounter_id = new_encounter_id()
        self.scenario = scenario

        if scenario:
            demo = scenario["demographics"]
            enc = blank_encounter(
                encounter_id=self.encounter_id,
                patient_name=demo["name"],
                mrn=demo["mrn"],
                dob=demo["dob"],
            )
        else:
            enc = blank_encounter(
                encounter_id=self.encounter_id,
                patient_name=patient_name,
                mrn=mrn,
                dob=dob,
            )

        save_encounter(enc)
        print(f"[Orchestrator] Encounter started: {self.encounter_id}")
        return self.encounter_id

    def run_consultation(self, audio_path: str = None,
                         transcript: str = None,
                         use_dynamic: bool = False) -> dict:
        """Run consultation phase (ConsultationAgent + HeARAgent in parallel)."""
        print("\n" + "=" * 60)
        print("PHASE 1: CONSULTATION")
        print("=" * 60)

        # Run ConsultationAgent
        consultation_context = {
            "audio_path": audio_path,
            "transcript": transcript,
            "use_dynamic": use_dynamic,
            "scenario": self.scenario,
        }
        result = self.agents["consultation"].process(
            self.encounter_id, consultation_context
        )
        self._results["consultation"] = result

        print(f"\nTranscript ({len(result['transcript'])} chars):")
        print(result["transcript"][:300] + "...")
        print(f"\nSOAP Note generated successfully.")

        # Run HeARAgent if audio is available
        if audio_path and "hear_model" in self.models:
            print("\n--- HeAR Respiratory Analysis ---")
            hear_result = self.agents["hear"].process(
                self.encounter_id,
                {"audio_path": audio_path, "transcript": result["transcript"]},
            )
            self._results["hear"] = hear_result
            print(f"HeAR: {hear_result['hear_summary']}")
            if hear_result["clinical_suggestion"]:
                print(f"\nClinical Suggestion:\n{hear_result['clinical_suggestion']}")

        return result

    def run_admission(self, fhir_bundle_path: str = None,
                      use_fhir_server: bool = False,
                      patient_id: str = None) -> dict:
        """Run admission phase (VitalsMonitorAgent)."""
        print("\n" + "=" * 60)
        print("PHASE 2: ADMISSION & VITALS")
        print("=" * 60)

        soap_note = self._results.get("consultation", {}).get("soap_note", {})

        context = {
            "fhir_bundle_path": fhir_bundle_path,
            "use_fhir_server": use_fhir_server,
            "patient_id": patient_id or (self.scenario["demographics"]["mrn"]
                                         if self.scenario else ""),
            "soap_note": soap_note,
            "scenario": self.scenario,
        }

        result = self.agents["vitals"].process(self.encounter_id, context)
        self._results["admission"] = result

        # Display anomalies
        if result["anomalies"]:
            print("\n⚠ VITAL SIGN ANOMALIES:")
            for a in result["anomalies"]:
                print(f"  [{a['status']}] {a['message']}")

        print(f"\nAdmission note generated ({len(result['admission_note'])} chars)")
        return result

    def run_radiology(self, image_path: str = None, image=None,
                      clinical_context: str = "",
                      modality: str = "X-ray", body_part: str = "Chest",
                      upload_to_dicom: bool = False) -> dict:
        """Run radiology phase (RadiologyAgent)."""
        print("\n" + "=" * 60)
        print("PHASE 3: RADIOLOGY")
        print("=" * 60)

        # Build clinical context from previous phases if not provided
        if not clinical_context:
            soap = self._results.get("consultation", {}).get("soap_note", {})
            admission = self._results.get("admission", {}).get("admission_note", "")
            parts = []
            if soap:
                parts.append(f"Assessment: {soap.get('assessment', 'N/A')}")
                parts.append(f"Plan: {soap.get('plan', 'N/A')}")
            if admission:
                parts.append(f"Admission: {str(admission)[:500]}")
            clinical_context = "\n".join(parts) or "No prior clinical context."

        context = {
            "image_path": image_path,
            "image": image,
            "clinical_context": clinical_context,
            "modality": modality,
            "body_part": body_part,
            "upload_to_dicom": upload_to_dicom,
        }

        result = self.agents["radiology"].process(self.encounter_id, context)
        self._results["radiology"] = result

        print(f"\nRadiology report generated ({len(result['radiology_report'])} chars)")
        return result

    def run_discharge(self) -> dict:
        """Run discharge phase (DischargeAgent)."""
        print("\n" + "=" * 60)
        print("PHASE 4: DISCHARGE")
        print("=" * 60)

        result = self.agents["discharge"].process(self.encounter_id, {})
        self._results["discharge"] = result

        print(f"\nDischarge summary generated ({len(result['discharge_summary'])} chars)")
        print(f"ICD-10 codes: {len(result['icd10_codes'])}")
        for code in result["icd10_codes"]:
            print(f"  {code['code']}: {code['description']}")

        return result

    def run_full_pipeline(self, audio_path: str = None,
                          transcript: str = None,
                          fhir_bundle_path: str = None,
                          image_path: str = None,
                          use_dynamic: bool = True,
                          use_fhir_server: bool = False) -> dict:
        """Run the complete clinical pipeline end-to-end."""
        print(f"\n{'#' * 60}")
        print(f"OMNICARE FULL PIPELINE — Encounter: {self.encounter_id}")
        print(f"{'#' * 60}")

        self.run_consultation(audio_path=audio_path, transcript=transcript,
                              use_dynamic=use_dynamic)
        self.run_admission(fhir_bundle_path=fhir_bundle_path,
                           use_fhir_server=use_fhir_server)
        if image_path:
            self.run_radiology(image_path=image_path)
        self.run_discharge()

        print(f"\n{'#' * 60}")
        print(f"PIPELINE COMPLETE — Encounter: {self.encounter_id}")
        print(f"{'#' * 60}")

        return self._results

    def get_results(self) -> dict:
        """Return all accumulated results from the pipeline."""
        return self._results

    def get_agent_logs(self) -> list:
        """Retrieve all agent logs for the current encounter."""
        try:
            from .firestore_db import get_agent_logs
            return get_agent_logs(self.encounter_id)
        except Exception:
            return []
