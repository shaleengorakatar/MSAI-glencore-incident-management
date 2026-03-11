"""
Seed 25 realistic mining H&S incidents so the triage dashboard looks real.
All AI fields are pre-filled (as if AI already processed them).
"""
from __future__ import annotations

import json
import uuid
import random

from app.database import insert_incident, count_incidents
from app.data.sites import GLENCORE_SITES


def seed_demo_data():
    """Insert realistic demo incidents if database is empty."""
    if count_incidents() > 0:
        return  # Already seeded
    
    # Sample incident templates with realistic mining scenarios
    incident_templates = [
        {
            "short_description": "Loader slipped near wet ramp. One worker twisted ankle. Oil leak visible.",
            "detailed_description": "At approximately 09:35, a CAT 994K loader was travelling down North Pit Ramp 3 when the operator noticed loss of traction on the wet surface. A maintenance worker inspecting nearby twisted his ankle while moving out of the way. Hydraulic oil leak visible near left rear wheel assembly. Area was not cordoned.",
            "people_impacted": 1,
            "injury_reported": 1,
            "immediate_danger": 1,
            "ai_title": "Slip injury near loader with hydraulic oil leak on wet ramp",
            "ai_summary": "A maintenance worker sustained an ankle injury after a loader lost traction on a wet ramp. Hydraulic oil leak from the loader is creating an active slip hazard. The area remains uncordoned.",
            "ai_categories": ["Slip/Fall", "Equipment Hazard", "Environmental Hazard"],
            "ai_severity": "High",
            "ai_priority": "P1",
            "ai_confidence": 0.92,
        },
        {
            "short_description": "Conveyor belt guard missing. Worker's glove caught in roller.",
            "detailed_description": "During routine coal transfer operation, operator noticed the safety guard on Conveyor B12 was missing. While attempting to clear a blockage, the operator's right glove was caught in the tail roller. Glove was pulled off but no skin contact with roller. Emergency stop activated. Belt was running at full speed.",
            "people_impacted": 1,
            "injury_reported": 0,
            "immediate_danger": 1,
            "ai_title": "Near-miss: glove entanglement at unguarded conveyor roller",
            "ai_summary": "An operator's glove was caught in the tail roller of Conveyor B12 after the safety guard was found missing. The glove was pulled off without injury. This is a serious near-miss with potential for amputation.",
            "ai_categories": ["Equipment Hazard", "PPE Violation", "Near-Miss"],
            "ai_severity": "High",
            "ai_priority": "P1",
            "ai_confidence": 0.95,
        },
        {
            "short_description": "Rock fall from unsupported roof in stope area. Two workers evacuated.",
            "detailed_description": "At 14:15 a section of the roof in Stope 7 on Level 4 collapsed without warning. Approximately 2 tonnes of rock fell. Two drill operators were working approximately 15m from the fall zone and were evacuated. No injuries but significant dust cloud reduced visibility. Ground support bolts in the area were last inspected 3 weeks ago.",
            "people_impacted": 2,
            "injury_reported": 0,
            "immediate_danger": 1,
            "ai_title": "Roof collapse in underground stope — two workers evacuated safely",
            "ai_summary": "Approximately 2 tonnes of rock fell from an unsupported roof section in Stope 7, Level 4. Two drill operators were evacuated without injury. Ground support was last inspected 3 weeks prior. The area remains unstable.",
            "ai_categories": ["Structural", "Near-Miss"],
            "ai_severity": "Critical",
            "ai_priority": "P1",
            "ai_confidence": 0.97,
        },
        {
            "short_description": "Chemical spill in processing plant. Worker experiencing dizziness.",
            "detailed_description": "During copper refining process, a pipe burst in the acid leaching area releasing approximately 200L of sulfuric acid solution. One worker in the vicinity reported dizziness and was evacuated for medical assessment. Spill containment barriers were activated but some acid reached floor drains.",
            "people_impacted": 1,
            "injury_reported": 1,
            "immediate_danger": 1,
            "ai_title": "Sulfuric acid spill with worker exposure in processing plant",
            "ai_summary": "Pipe burst in acid leaching area released 200L of sulfuric acid. One worker experienced dizziness and required medical evacuation. Partial containment failure with acid reaching floor drains.",
            "ai_categories": ["Chemical", "Environmental", "Medical"],
            "ai_severity": "High",
            "ai_priority": "P1",
            "ai_confidence": 0.89,
        },
        {
            "short_description": "Electrical fault in smelter control room. Power outage affected operations.",
            "detailed_description": "Short circuit in main control panel of smelter caused electrical arc flash and complete power outage to operations. Three control room operators present but none injured. Backup generators failed to engage. Operations suspended pending electrical inspection.",
            "people_impacted": 3,
            "injury_reported": 0,
            "immediate_danger": 0,
            "ai_title": "Control room electrical fault causes smelter shutdown",
            "ai_summary": "Electrical arc flash in main control panel caused complete power outage. Three operators present but uninjured. Backup generators failed to engage, suspending all smelter operations.",
            "ai_categories": ["Electrical", "Equipment Failure"],
            "ai_severity": "Medium",
            "ai_priority": "P2",
            "ai_confidence": 0.85,
        },
    ]
    
    # Generate 25 incidents using templates and random sites
    reporter_names = [
        "James Barton", "Sarah Mitchell", "David Kowalski", "Maria Rodriguez",
        "John Smith", "Emma Wilson", "Michael Chen", "Lisa Anderson",
        "Robert Taylor", "Jennifer Brown", "William Davis", "Patricia Miller",
        "Christopher Garcia", "Linda Martinez", "Joseph Robinson", "Barbara Clark"
    ]
    
    locations = [
        "North Pit Ramp 3", "Conveyor Belt B12", "Underground Level 4 - Stope 7",
        "Processing Plant - Acid Leaching", "Smelter Control Room", "Workshop Bay 2",
        "Tailings Storage Facility", "Crusher Station A", "Maintenance Workshop",
        "Ore Processing Unit", "Warehouse Building C", "Drilling Platform D",
        "Loading Dock Area", "Power Substation", "Laboratory Building"
    ]
    
    for i in range(25):
        template = random.choice(incident_templates)
        reporter = random.choice(reporter_names)
        site = random.choice(GLENCORE_SITES)
        location = random.choice(locations)
        
        # Generate random timestamp in last 7 days
        days_ago = random.randint(0, 7)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        timestamp = f"2025-03-{8-days_ago:02d}T{hours_ago:02d}:{minutes_ago:02d}:00Z"
        
        incident = {
            "id": str(uuid.uuid4()),
            "reporter_name": reporter,
            "site_name": site,
            "location": location,
            "reported_at": timestamp,
            "short_description": template["short_description"],
            "detailed_description": template["detailed_description"],
            "people_impacted": template["people_impacted"],
            "injury_reported": template["injury_reported"],
            "immediate_danger": template["immediate_danger"],
            "status": "open",
            "ai_title": template["ai_title"],
            "ai_summary": template["ai_summary"],
            "ai_categories": json.dumps(template["ai_categories"]),
            "ai_severity": template["ai_severity"],
            "ai_priority": template["ai_priority"],
            "ai_confidence": template["ai_confidence"],
            "ai_severity_rationale": f"Priority based on {template['ai_severity'].lower()} severity indicators including injury report and immediate danger factors.",
            "ai_recommended_actions": json.dumps([
                "Secure the area immediately",
                "Report to shift supervisor", 
                "Document incident details",
                "Review safety procedures"
            ]),
            "ai_root_causes": json.dumps([
                "Equipment failure",
                "Procedural deviation",
                "Environmental factors"
            ]),
            "ai_extracted_entities": json.dumps({
                "equipment": ["Processing equipment"],
                "substances": ["Chemicals"],
                "body_parts_injured": ["Various"],
                "personnel_roles": ["Operators", "Maintenance"],
                "environmental_factors": ["Weather", "Conditions"]
            }),
            "ai_themes": json.dumps(["Safety", "Maintenance", "Operations"]),
        }
        
        insert_incident(incident)
