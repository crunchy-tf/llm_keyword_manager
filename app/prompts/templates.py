# THIS IS THE USER'S UPDATED VERSION FROM PREVIOUS INTERACTION
from typing import Dict

# Mapping of category keys (used for context file names/prompting)
# to descriptive names for generating targeted keywords.
HEALTH_TOPICS: Dict[str, str] = {

    # === I. SYMPTOM CATEGORIES (By Body System) ===
    "symptoms_general": "General systemic symptoms (fatigue, malaise, weakness, weight changes, appetite changes, night sweats)",
    "symptoms_fever_temperature": "Fever, high temperature, hypothermia, chills, shivering",
    "symptoms_respiratory_upper": "Upper respiratory symptoms (runny nose/rhinorrhea, nasal congestion, sneezing, sore throat, loss of voice/hoarseness)",
    "symptoms_respiratory_lower": "Lower respiratory symptoms (cough - dry/productive, shortness of breath/dyspnea, wheezing, chest tightness/pain related to breathing)",
    "symptoms_cardiovascular": "Cardiovascular symptoms (chest pain/angina, palpitations, irregular heartbeat, edema/swelling in legs/ankles, fainting/syncope, high/low blood pressure mentions)",
    "symptoms_gastrointestinal_upper": "Upper GI symptoms (nausea, vomiting, heartburn/acid reflux, indigestion, difficulty swallowing/dysphagia)",
    "symptoms_gastrointestinal_lower": "Lower GI symptoms (diarrhea, constipation, abdominal pain/cramps, bloating, gas, blood in stool/rectal bleeding, jaundice)",
    "symptoms_neurological": "Neurological symptoms (headache, migraine, dizziness/vertigo, confusion/disorientation, memory loss, loss of consciousness, seizures/convulsions, tremors, numbness/tingling/paresthesia, weakness/paralysis, balance problems, loss of smell/anosmia, loss of taste/ageusia)",
    "symptoms_musculoskeletal": "Musculoskeletal symptoms (muscle aches/myalgia, joint pain/arthralgia, back pain, neck pain, stiffness, swelling in joints, muscle cramps, bone pain)",
    "symptoms_skin_integumentary": "Skin symptoms (rash, hives/urticaria, itching/pruritus, lesions, sores, ulcers, blisters, dryness, scaling, sweating changes, skin discoloration, hair loss/alopecia, nail changes)",
    "symptoms_eyes_vision": "Eye and vision symptoms (red eyes/conjunctivitis, eye pain, blurred vision, double vision/diplopia, light sensitivity/photophobia, eye discharge, vision loss)",
    "symptoms_ears_hearing": "Ear and hearing symptoms (ear pain/otalgia, hearing loss, tinnitus/ringing in ears, ear discharge, vertigo related to ear)",
    "symptoms_urinary_renal": "Urinary and kidney symptoms (painful urination/dysuria, frequent urination, urgency, blood in urine/hematuria, incontinence, flank pain, decreased urine output)",
    "symptoms_reproductive_public": "Publicly discussed reproductive health symptoms (e.g., unusual patterns of menstrual irregularities discussed widely, widespread pelvic pain reports if potentially linked to outbreak)",
    "symptoms_lymphatic_hematologic": "Lymphatic/Blood symptoms (swollen lymph nodes/lymphadenopathy, easy bruising, unexplained bleeding, anemia mentions)",

    # === II. COMMUNICABLE DISEASES (Common, Endemic, Epidemic Potential, Emerging) ===
    # --- Viral Respiratory ---
    "disease_covid19": "COVID-19, variants (Omicron, etc.), Long COVID/PASC",
    "disease_influenza_seasonal": "Seasonal Influenza (Flu), strains (H1N1, H3N2, B)",
    "disease_influenza_avian_pandemic": "Avian Influenza (Bird Flu, H5N1, etc.), Pandemic Flu concerns",
    "disease_rsv": "Respiratory Syncytial Virus, common in children and elderly",
    "disease_common_cold": "Common Cold (Rhinoviruses, Coronaviruses other than SARS-CoV-2, Adenoviruses)",
    "disease_measles": "Measles virus, outbreaks, complications",
    "disease_mumps": "Mumps virus, parotitis, outbreaks",
    "disease_rubella": "Rubella (German Measles), congenital risks",
    "disease_chickenpox_shingles": "Varicella-Zoster Virus (Chickenpox, Shingles)",
    # --- Bacterial Respiratory ---
    "disease_tuberculosis": "Tuberculosis (TB), pulmonary and extrapulmonary, MDR-TB",
    "disease_pertussis": "Pertussis (Whooping Cough)",
    "disease_pneumonia_bacterial": "Bacterial Pneumonia (Streptococcus pneumoniae, Haemophilus influenzae, etc.)",
    "disease_diphtheria": "Diphtheria",
    "disease_legionnaires": "Legionnaires' disease (Legionella)",
    # --- Gastrointestinal ---
    "disease_norovirus": "Norovirus (acute gastroenteritis, stomach flu)",
    "disease_rotavirus": "Rotavirus (common cause of diarrhea in infants)",
    "disease_salmonellosis": "Salmonella infection (food poisoning)",
    "disease_shigellosis": "Shigella infection (dysentery)",
    "disease_ecoli_pathogenic": "Pathogenic E. coli infections (e.g., EHEC, O157:H7)",
    "disease_campylobacteriosis": "Campylobacter infection (food poisoning)",
    "disease_cholera": "Cholera",
    "disease_typhoid_paratyphoid": "Typhoid Fever, Paratyphoid Fever",
    "disease_giardiasis": "Giardia infection",
    "disease_amebiasis": "Amebiasis (Entamoeba histolytica)",
    "disease_listeriosis": "Listeria infection (foodborne)",
    "disease_hepatitis_a_e": "Hepatitis A, Hepatitis E (food/waterborne)",
    # --- Vector-Borne (Regionally Relevant/Potential) ---
    "disease_west_nile_virus": "West Nile Virus (mosquito-borne)",
    "disease_dengue": "Dengue Fever (mosquito-borne)",
    "disease_chikungunya": "Chikungunya virus (mosquito-borne)",
    "disease_leishmaniasis": "Leishmaniasis (cutaneous and visceral, sandfly-borne - significant in region)",
    "disease_malaria": "Malaria (mosquito-borne, monitor for imported cases or re-emergence)",
    "disease_rift_valley_fever": "Rift Valley Fever (mosquito-borne, zoonotic - regional risk)",
    "disease_crimean_congo_hemorrhagic": "Crimean-Congo Hemorrhagic Fever (CCHF) (tick-borne - regional risk)",
    "disease_tick_borne_encephalitis": "Tick-Borne Encephalitis (TBE) / other tick-borne fevers (if locally relevant ticks)",
    # --- Zoonotic / Direct Contact ---
    "disease_rabies": "Rabies (animal bites)",
    "disease_brucellosis": "Brucellosis (Malta Fever - contact with infected animals/products - common in region)",
    "disease_anthrax": "Anthrax (cutaneous, inhalation, gastrointestinal)",
    "disease_leptospirosis": "Leptospirosis (contact with contaminated water/soil/animal urine)",
    "disease_q_fever": "Q Fever (Coxiella burnetii - inhalation/contact with animals)",
    "disease_mpox": "Mpox (formerly Monkeypox)",
    "disease_ebola_marburg": "Ebola Virus Disease, Marburg Virus Disease (Viral Hemorrhagic Fevers - monitor high-consequence mentions)",
    "disease_scabies_lice": "Scabies, Head Lice infestations (ectoparasites)",
    # --- Bloodborne / STI ---
    "disease_hiv_aids": "Human Immunodeficiency Virus (HIV), Acquired Immunodeficiency Syndrome (AIDS)",
    "disease_hepatitis_b_c": "Hepatitis B, Hepatitis C (bloodborne, chronic liver disease)",
    "disease_syphilis": "Syphilis",
    "disease_gonorrhea": "Gonorrhea",
    "disease_chlamydia": "Chlamydia",
    "disease_hpv": "Human Papillomavirus (HPV), relation to cancers, warts",
    # --- Other Notable Communicables ---
    "disease_meningitis_bacterial": "Bacterial Meningitis (Neisseria meningitidis, Streptococcus pneumoniae, Haemophilus influenzae)",
    "disease_meningitis_viral": "Viral Meningitis (Enteroviruses, HSV, etc.)",
    "disease_tetanus": "Tetanus",
    "disease_poliomyelitis": "Polio (monitor vaccination status, rare wild/VDPV cases)",

    # === III. DISEASE CATEGORIES BY TRANSMISSION / TYPE ===
    "transmission_airborne_droplet": "Diseases spread through air/respiratory droplets (e.g., flu, measles, TB)",
    "transmission_foodborne": "Illnesses caused by contaminated food",
    "transmission_waterborne": "Illnesses caused by contaminated water",
    "transmission_vector_mosquito": "Diseases spread by mosquitoes",
    "transmission_vector_tick": "Diseases spread by ticks",
    "transmission_vector_other": "Diseases spread by other vectors (sandflies, fleas, flies)",
    "transmission_zoonotic": "Diseases spread from animals to humans (direct contact, bites, products, aerosols)",
    "transmission_direct_contact": "Diseases spread by skin-to-skin or direct mucous membrane contact",
    "transmission_fecal_oral": "Diseases spread through ingestion of fecal matter (often overlaps food/waterborne)",
    "transmission_bloodborne_sexual": "Diseases spread through blood, bodily fluids, sexual contact (STIs, Hepatitis B/C, HIV)",
    "transmission_healthcare_associated": "Healthcare-Associated Infections (HAIs), nosocomial infections, hospital outbreaks",
    "transmission_congenital_perinatal": "Diseases transmitted from mother to child during pregnancy or birth",
    "disease_type_viral_hemorrhagic": "Viral Hemorrhagic Fevers (VHFs) as a class (Ebola, Marburg, Lassa, CCHF)",
    "disease_type_prion": "Prion diseases (e.g., CJD - monitoring for unusual neurological clusters)",

    # === IV. PUBLIC HEALTH ACTIONS & DISCOURSE ===
    "public_health_surveillance_reporting": "Official disease surveillance data releases, case counts, epidemiological reports, outbreak investigations",
    "public_health_prevention_hygiene": "Recommendations and discussions on personal hygiene, handwashing, cough etiquette, sanitation practices",
    "public_health_vaccination_general": "General discussions about vaccines, immunization schedules, importance of vaccination",
    "public_health_vaccination_campaigns": "Specific vaccination campaigns, rollout logistics, eligibility, vaccine types offered",
    "public_health_vaccination_hesitancy": "Vaccine hesitancy, safety concerns, misinformation, anti-vaccination sentiment, parental refusal",
    "public_health_vaccination_access_supply": "Vaccine availability, shortages, distribution challenges, access points (clinics, pharmacies)",
    "public_health_vaccination_aefi": "Discussions about Adverse Events Following Immunization (AEFI), monitoring, reporting",
    "public_health_npi_masking": "Discussions about mask mandates, recommendations, types of masks, effectiveness",
    "public_health_npi_distancing_limits": "Social distancing measures, capacity limits, restrictions on gatherings",
    "public_health_npi_closures": "School closures, business closures, lockdowns, curfews",
    "public_health_screening_testing_strategy": "Public health strategies for disease screening and diagnostic testing (mass testing, targeted, symptomatic)",
    "public_health_screening_testing_access": "Availability, accessibility, cost, and location of diagnostic tests (PCR, rapid tests, etc.)",
    "public_health_contact_tracing": "Contact tracing efforts, methods, effectiveness, privacy concerns",
    "public_health_quarantine_isolation": "Quarantine and isolation policies, duration, compliance, support systems",
    "public_health_border_control_travel": "Travel advisories, border closures, entry requirements (testing, vaccination), screening at ports of entry, imported cases",
    "public_health_communication_alerts": "Official public health announcements, alerts, risk communication messages, health advisories",
    "public_health_misinformation_disinformation": "Spread of false or misleading health information, fact-checking efforts, rumors",
    "public_health_policy_legislation": "New public health laws, regulations, government policies, funding decisions",
    "public_health_vector_control": "Vector control measures (mosquito spraying, tick prevention advice, rodent control)",
    "public_health_food_safety_regulation": "Food safety regulations, inspections, enforcement actions, restaurant grading discussions",
    "public_health_research_studies": "Discussions about ongoing public health research, clinical trials, epidemiological studies",

    # === V. HEALTH SYSTEM & ACCESS ===
    "health_system_capacity_hospitals": "Hospital bed availability (general, ICU), emergency room overcrowding, wait times",
    "health_system_capacity_staffing": "Healthcare worker shortages (doctors, nurses, technicians), burnout, strikes, workload",
    "health_system_capacity_equipment": "Availability of medical equipment (ventilators, oxygen, PPE)",
    "health_system_access_primary_care": "Access to general practitioners, family doctors, preventative services, check-ups",
    "health_system_access_specialist_care": "Wait times and availability for specialist consultations and procedures",
    "health_system_access_geographic_rural": "Geographic barriers to healthcare, access issues in rural or underserved areas",
    "health_system_access_cost_affordability": "Cost of healthcare, medical bills, out-of-pocket expenses, affordability issues",
    "health_system_access_insurance": "Health insurance coverage, CNAM, private insurance issues, lack of insurance",
    "health_system_pharmaceuticals_supply": "Medication shortages, drug availability at pharmacies, vaccine supply chain issues",
    "health_system_pharmaceuticals_cost": "Cost of medications, drug pricing discussions",
    "health_system_pharmaceuticals_safety": "Concerns about counterfeit drugs, medication errors, drug safety",
    "health_system_diagnostics_labs": "Availability and delays for lab tests, imaging services (X-ray, MRI), diagnostic procedures",
    "health_system_emergency_services": "Ambulance response times, quality of emergency medical services (EMS)",
    "health_system_telehealth": "Availability, usage, and limitations of telemedicine / remote consultations",
    "health_system_quality_of_care": "General discussions about the quality of medical treatment, patient safety, patient satisfaction/complaints",
    "health_system_infrastructure_maintenance": "Issues related to hospital building maintenance, equipment breakdowns",

    # === VI. ENVIRONMENTAL & SOCIAL FACTORS ===
    "env_air_quality": "Air pollution concerns (industrial, traffic, dust storms), smog, impact on respiratory health",
    "env_water_quality": "Drinking water safety, water pollution (industrial, agricultural runoff, sewage), access to clean water",
    "env_sanitation_waste": "Sanitation infrastructure issues, sewage management, waste disposal problems, impact on hygiene",
    "env_climate_change_health": "Health impacts of climate change (heatwaves/heat stress, changing disease vectors, extreme weather events like floods/droughts impacting health)",
    "env_extreme_weather_events": "Immediate health impacts of floods, heatwaves, storms (injuries, displacement, waterborne diseases post-flood)",
    "env_food_security_nutrition": "Access to sufficient, safe, and nutritious food, malnutrition, impact of food prices on diet",
    "env_housing_overcrowding": "Housing conditions, overcrowding, homelessness, impact on disease transmission and mental health",
    "env_occupational_health": "Workplace safety issues, occupational exposures (chemicals, dust, noise), work-related injuries and illnesses",
    "social_determinants_poverty_inequality": "Link between poverty, socioeconomic status, and health outcomes, health disparities",
    "social_determinants_education_literacy": "Impact of education level and health literacy on understanding health information and accessing care",
    "social_demographics_age": "Health issues specific to children (pediatrics) or the elderly (geriatrics)",
    "social_demographics_gender": "Gender-specific health issues or disparities in access/outcomes",
    "social_demographics_vulnerable_groups": "Health concerns of migrants, refugees, internally displaced persons, people with disabilities, minority groups",
    "social_unrest_conflict_impact": "Impact of social instability, protests, or conflict on health services and population health",
    "social_stigma_discrimination": "Stigma associated with certain diseases (e.g., HIV, TB, mental health) impacting care-seeking",

    # === VII. MENTAL HEALTH SYMPTOMS & TOPICS ===
    "mental_health_symptoms_anxiety": "Anxiety, worry, nervousness, panic attacks",
    "mental_health_symptoms_depression": "Depression, sadness, hopelessness, loss of interest, fatigue related to mood",
    "mental_health_symptoms_stress": "Stress, feeling overwhelmed, burnout (especially related to work, economy, crises)",
    "mental_health_symptoms_sleep": "Sleep problems, insomnia, hypersomnia",
    "mental_health_symptoms_trauma_ptsd": "Trauma-related symptoms, PTSD mentions (following disasters, violence, etc.)",
    "mental_health_symptoms_psychosis": "Discussions possibly related to psychosis symptoms (delusions, hallucinations - *interpret with caution*)",
    "mental_health_substance_use": "Substance abuse, addiction, drug overdose discussions",
    "mental_health_suicide_discourse": "Discussions related to suicide, suicidal ideation, prevention efforts (*handle with extreme sensitivity and ethical considerations*)",
    "mental_health_conditions_specific": "Mentions of specific diagnosed conditions (bipolar disorder, OCD, eating disorders)",
    "mental_health_access_care": "Access to psychiatrists, psychologists, therapists, counseling services, cost of mental healthcare",
    "mental_health_stigma": "Stigma surrounding mental illness, reluctance to seek help",
    "mental_health_awareness_support": "Mental health awareness campaigns, support groups, wellbeing initiatives",
    "mental_health_impact_crises": "Mental health consequences of pandemics, economic hardship, social upheaval",

    # === VIII. EMERGING & NOVEL ISSUES ===
    "emerging_unexplained_clusters": "Reports of unusual clusters of illness or symptoms without a clear cause",
    "emerging_atypical_presentations": "Known diseases presenting with unusual symptoms, severity, or affecting unexpected demographics",
    "emerging_antimicrobial_resistance": "Antimicrobial Resistance (AMR), drug-resistant infections, 'superbugs', antibiotic stewardship discussions",
    "emerging_rare_diseases_uptick": "Increased discussion or reports of diseases typically rare in the region",
    "emerging_chemical_radiological_bio_threats": "Concerns, rumors, or reports related to chemical spills, industrial accidents, radiation leaks, or potential bioterrorism events (*high sensitivity*)",
    "emerging_novel_pathogens": "Mentions or speculation about new viruses, bacteria, or other pathogens",
    "emerging_geographic_spread": "Diseases appearing in new geographic locations within Tunisia or the region",
    "emerging_zoonotic_spillover_concerns": "Concerns about diseases jumping from animals to humans, wildlife die-offs potentially linked to disease",
    "emerging_environmental_links": "Hypotheses or discussions linking specific environmental exposures to clusters of illness",
}

# --- LLM Prompt Templates (Optimized for Minbar Sources & Keyword Length) ---

# Template for generating keywords reflecting context from specific sources
CONTEXT_CONCEPT_PROMPT_TEMPLATE = """
You are an AI Keyword Strategist for the Minbar public health surveillance project in Tunisia. Your task is to generate relevant keywords based on observed online activity.
The current public health focus area is: {topic_description}

Analyze the following snippet(s) of recent online content from Tunisia:
--- START CONTEXT ---
{context}
--- END CONTEXT ---

Based *specifically* on this context, generate a list of up to 10 distinct keywords or keyphrases in **{language_name} ({language_code})**.
These keywords should:
1.  Be concise: **Strictly 1 to 4 words long (ideally 2-3 words)**.
2.  Be highly relevant: Directly reflect the core concepts, symptoms, locations, entities, or concerns mentioned or strongly implied in the context.
3.  Be practical for queries: Represent terms likely used in **news headlines/summaries, social media posts/comments, or search queries** related to the context.
4.  Capture variations: Include different phrasings if the context suggests multiple ways people refer to the same thing.

Avoid overly generic terms unless the context strongly emphasizes them (e.g., a general 'health alert'). Do not create long descriptive sentences.

List ONLY the keywords/keyphrases, each on a new line. No explanations, numbers, or bullet points.

Keywords in {language_name} ({language_code}):
"""

# Template for generating foundational keywords without specific context
BASE_CONCEPT_PROMPT_TEMPLATE = """
You are an AI Keyword Strategist for the Minbar public health surveillance project in Tunisia. Your task is to generate foundational keywords for a specific health topic.
The current public health focus area is: {topic_description}

Generate a list of up to 10 distinct, foundational keywords or keyphrases in **{language_name} ({language_code})**.
Imagine how this topic is typically discussed or searched for in Tunisia across different online platforms. Think about terms likely to appear in:
    *   **News Articles:** Formal names, locations, official announcements.
    *   **Social Media (Posts/Comments):** Common symptoms, informal language, questions, expressions of concern, shared experiences.
    *   **Search Queries (Google Trends):** Problem descriptions, symptom checks, "where to find X", treatment questions.

Your generated keywords should:
1.  Be concise: **Strictly 1 to 4 words long (ideally 2-3 words)**.
2.  Be highly relevant: Directly relate to the core aspects of '{topic_description}'.
3.  Be diverse: Capture a mix of potential terms reflecting formal (news) and informal (social media, search) usage. Include common symptoms, disease names, related actions (vaccination, testing), or public concerns.
4.  Be practical for queries: Represent terms effective for searching across APIs for news, social media, and trends.

Avoid overly generic terms (like 'health' or 'problem') unless part of a highly common phrase (e.g., 'problème de santé' if truly relevant). Do not create long descriptive sentences.

List ONLY the keywords/keyphrases, each on a new line. No explanations, numbers, or bullet points.

Example (if topic was General Respiratory Symptoms in French):
toux sèche
difficulté respirer
nez qui coule
mal gorge
fièvre frissons
test PCR où
remède rhume
poumons douleur

Keywords in {language_name} ({language_code}):
"""

# Template for translating a single term
TRANSLATION_PROMPT_TEMPLATE = """
Translate the following health-related term accurately from {source_language_name} to {target_language_name}, considering potential usage in Tunisia.
Provide ONLY the most common and concise translation suitable as a search keyword (typically 1-4 words). Do not add explanations or multiple alternatives.

Term: "{term}"

Translation in {target_language_name}:
"""

# Helper for language names
LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "ar": "Arabic" # Consider adding dialect support if feasible later
}