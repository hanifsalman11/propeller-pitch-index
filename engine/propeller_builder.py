import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/propeller-pitch-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0").strip()
CUSTOM_PROP = os.environ.get("CUSTOM_PROP", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_propellers.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Outboard / Boat Scenario, Target WOT RPM, Gear Ratio, Rec Pitch In, Prop Diameter In, Est Slip Pct, Spline Spec)
SEED_PROPELLERS = [
    ("Yamaha F150 (150 HP FourStroke) Reliance 14.25\" × 17\" Pitch", 5800, 2.00, 17, 14.25, 10.0, "15-Spline 4.25\" Gearcase"),
    ("Yamaha F115 (115 HP FourStroke) Talon 13.5\" × 15\" Pitch", 6000, 2.15, 15, 13.50, 11.0, "15-Spline 4.25\" Gearcase"),
    ("Yamaha F90 (90 HP FourStroke) Pontoon & Bay Boat Pitch", 5800, 2.15, 13, 13.75, 14.0, "15-Spline 4.25\" Gearcase"),
    ("Yamaha F200 (200 HP Inline-4) 14.25\" × 18\" Pitch", 5800, 1.86, 18, 14.25, 9.5, "15-Spline SDS Hub"),
    ("Yamaha F250 / F300 V6 (4.2L) Saltwater Series II 15.25\" × 19\"", 5800, 1.75, 19, 15.25, 8.5, "15-Spline 4.75\" V6 Case"),
    ("Yamaha F60 / F70 (60-70 HP) Aluminum & Skiff Pitch", 6000, 2.33, 13, 13.25, 12.0, "13-Spline 3.5\" Gearcase"),
    ("Mercury 115 Pro XS FourStroke (2.07 Ratio) vs Command Thrust", 6000, 2.07, 17, 13.25, 10.5, "15-Spline Flo-Torq II"),
    ("Mercury 115 Command Thrust (2.38 Ratio) Pontoon 14\" Pitch", 5800, 2.38, 14, 14.50, 15.0, "15-Spline 4.75\" BigFoot"),
    ("Mercury 150 FourStroke / Pro XS (3.0L) Enertia 15\" × 17\" Pitch", 5800, 1.92, 17, 15.00, 9.5, "15-Spline Flo-Torq II"),
    ("Mercury 200 / 225 / 250 Pro XS V8 (4.6L) Fury 23\" Pitch", 6000, 1.75, 23, 14.00, 8.0, "1.25\" / 15-Spline Hub"),
    ("Mercury 90 HP FourStroke (2.1L) Black Max & Spitfire 4-Blade", 5800, 2.07, 15, 13.50, 12.0, "15-Spline Flo-Torq II"),
    ("Mercury 60 HP FourStroke BigFoot / Command Thrust Pontoon", 5800, 2.33, 11, 14.00, 16.0, "15-Spline 4.25\" Case"),
    ("Suzuki DF140A / DF140B (2.59 Gear Ratio) 14\" × 21\" Pitch", 6000, 2.59, 21, 14.00, 10.0, "15-Spline Suzuki Hub"),
    ("Suzuki DF115A / DF115B (2.59 Gear Ratio) 14\" × 19\" Pitch", 5800, 2.59, 19, 14.00, 11.0, "15-Spline Suzuki Hub"),
    ("Suzuki DF150 / DF175 / DF200 (2.50 Big-Block Ratio) 21\" Pitch", 5900, 2.50, 21, 15.00, 9.5, "15-Spline 4.75\" Case"),
    ("Suzuki DF300AP (2.08 Gear Ratio) Watergrip 3-Blade & 4-Blade", 6000, 2.08, 20, 16.00, 9.0, "15-Spline V6 Hub"),
    ("Honda BF90 / BF100 & BF115 / BF150 VTEC Propeller Sizing", 5800, 2.14, 17, 14.25, 10.5, "15-Spline Honda Hub"),
    ("Tohatsu MFS60 / MFS90 / MFS115 High-Thrust Propeller Sizing", 5800, 2.08, 15, 13.50, 11.5, "15-Spline Tohatsu Hub"),
    ("MerCruiser Alpha One Gen 2 (4.3L V6 — 1.81 Ratio) 19\" Pitch", 4800, 1.81, 19, 14.25, 11.0, "15-Spline Flo-Torq II"),
    ("MerCruiser Alpha One Gen 2 (5.0L / 5.7L V8 — 1.47 Ratio) 19\" Pitch", 4800, 1.47, 19, 14.25, 10.5, "15-Spline Flo-Torq II"),
    ("MerCruiser Alpha One (3.0L 4-Cylinder — 1.98 Ratio) 17\" Pitch", 4600, 1.98, 17, 14.50, 12.0, "15-Spline Flo-Torq II"),
    ("MerCruiser Bravo One & Bravo Three (6.2L / 7.4L) Prop Sizing", 5000, 1.50, 21, 14.75, 9.5, "15-Spline / Dual-Prop"),
    ("Volvo Penta SX & DPS Sterndrive (4.3L / 5.0L / 5.7L) Pitch", 4800, 1.60, 19, 14.50, 10.5, "19-Spline Volvo SX Hub"),
    ("Solas Amita 3 vs Amita 4 Aluminum Propeller Pitch Conversion", 5800, 2.00, 15, 14.00, 12.0, "Rubex / Pressed Hub"),
    ("Solas Rubex L3 vs Rubex HR4 Stainless Propeller Pitch Sizing", 5800, 2.00, 17, 14.25, 9.5, "Rubex Interchangeable Hub"),
    ("Turning Point Hustler 3-Blade vs 4-Blade Aluminum Prop Sizing", 5800, 2.07, 17, 13.75, 11.0, "MasterGuard 500 Series"),
    ("20-to-24 Ft Pontoon Boat (90 HP – 150 HP) High-Thrust Prop", 5800, 2.15, 13, 14.25, 16.0, "4-Blade High-Cup Pontoon"),
    ("18-to-21 Ft Bass Boat (150 HP – 250 HP) Jack Plate & Pitch", 5900, 1.86, 23, 14.50, 8.0, "3-Blade High-Rake Bow-Lift"),
    ("21-to-24 Ft Deep-V Center Console Offshore 4-Blade Stern-Lift", 5800, 1.86, 17, 14.75, 10.5, "4-Blade Stainless Stern-Lift"),
    ("17-Pitch vs 19-Pitch vs 21-Pitch Boat Propeller RPM & MPH", 5800, 2.00, 19, 14.25, 10.0, "15-Spline Universal Hub")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=17.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_prop_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Outboard × Pitch × Hull Permutator.
    """
    discovered = []
    seeds = [
        "boat propeller calculator ",
        "what size prop for ",
        "mercury outboard prop ",
        "yamaha outboard prop "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "calculator" in pref or "what size" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        p_m = re.search(r"\b(11|13|15|17|19|21|23)\b", cleaned)
                        p_in = int(p_m.group(1)) if p_m else 17
                        discovered.append((cleaned.title(), 5800, 2.00, p_in, 14.25, 10.5, "15-Spline Universal Hub"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    engines = [
        ("60 HP 4-Stroke Outboard (2.33 Ratio)", 5800, 2.33, 13.25),
        ("90 HP 4-Stroke Outboard (2.07 Ratio)", 5800, 2.07, 13.50),
        ("115 HP 4-Stroke Outboard (2.15 Ratio)", 6000, 2.15, 13.75),
        ("150 HP 4-Stroke Outboard (2.00 Ratio)", 5800, 2.00, 14.25),
        ("200 HP V6 Outboard (1.86 Ratio)", 5800, 1.86, 14.50),
        ("250 HP V8 Outboard (1.75 Ratio)", 6000, 1.75, 14.75)
    ]
    hulls = [
        ("Pontoon / Tritoon Boat", 13, 15.0),
        ("Deep-V Center Console", 17, 10.5),
        ("Aluminum Bay / Flats Skiff", 19, 9.5),
        ("High-Speed Bass Boat", 21, 8.0)
    ]
    for eng_name, wot_r, g_rat, dia_v in engines:
        for h_name, base_p, slp_v in hulls:
            combo_title = f"{eng_name} on {h_name}"
            test_slug = slugify(f"{combo_title}-propeller-pitch-slip-calculator")
            if test_slug not in published_slugs:
                discovered.append((combo_title, wot_r, g_rat, base_p, dia_v, slp_v, "15-Spline Hub Kit"))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_prop_data(prop_tuple):
    """
    LAPIS 3: Mesin Fisika Hidrodinamika Baling-Baling Kapal, Prop Slip % & WOT RPM (100% Bebas Gagal).
    """
    model_name, wot_rpm, gear_ratio, pitch_in, dia_in, slip_pct, spline_spec = prop_tuple

    # Rumus Kecepatan Teoritis (Theoretical Speed MPH tanpa slip):
    # Theoretical MPH = (WOT_RPM * Pitch_Inches) / (Gear_Ratio * 1056)
    # Catatan: 1 mile = 63,360 inches; 60 minutes/hr -> 63,360 / 60 = 1,056
    prop_shaft_rpm = int(round(wot_rpm / max(1.0, float(gear_ratio))))
    theo_mph = round((wot_rpm * pitch_in) / (gear_ratio * 1056.0), 1)

    # Kecepatan Aktual GPS (Actual GPS Speed MPH setelah dikurangi Hydrodynamic Slip %):
    actual_gps_mph = round(theo_mph * (1.0 - (slip_pct / 100.0)), 1)

    # Pitch 4-Blade Setara (1" - 2" lebih rendah dari 3-blade agar WOT RPM tidak drop di bawah batas pabrik)
    four_blade_pitch = max(9, pitch_in - 2 if pitch_in >= 17 else pitch_in - 1)
    # Kecepatan jika naik +2" Pitch (RPM turun ~350 RPM) vs turun -2" Pitch (RPM naik ~350 RPM)
    rpm_minus_2p = wot_rpm + 350
    rpm_plus_2p = wot_rpm - 350

    return {
        "prop_name": model_name,
        "spline_spec": spline_spec,
        "seo_title": f"{model_name} Propeller Pitch, Slip % & WOT RPM Calculator (2026)",
        "meta_description": f"Calculate exact boat propeller pitch ({dia_in}\" × {pitch_in}\" 3-blade / {four_blade_pitch}\" 4-blade), GPS speed ({actual_gps_mph} MPH @ {wot_rpm:,} RPM), {gear_ratio:.2f}:1 gear ratio, and {slip_pct}% prop slip for {model_name}.",
        "specs": {
            "target_wot_rpm": wot_rpm,
            "gear_ratio": gear_ratio,
            "prop_shaft_rpm": prop_shaft_rpm,
            "recommended_pitch_in": pitch_in,
            "four_blade_pitch_in": four_blade_pitch,
            "prop_diameter_in": dia_in,
            "theoretical_mph": theo_mph,
            "estimated_slip_pct": slip_pct,
            "actual_gps_mph": actual_gps_mph,
            "spline_spec": spline_spec
        },
        "hydro_verdict": f"Running a {gear_ratio:.2f}:1 lower-unit gear ratio at {wot_rpm:,} WOT RPM ({prop_shaft_rpm:,} prop-shaft RPM), {model_name} paired with a {dia_in}\" × {pitch_in}\"-pitch 3-blade propeller achieves a theoretical zero-slip speed of {theo_mph} MPH and an actual GPS top speed of ~{actual_gps_mph} MPH at {slip_pct}% hydrodynamic slip. Every 1 inch of pitch changes WOT engine speed by ~175 RPM (2 inches = ~350 RPM: a {pitch_in - 2}\" pitch raises WOT to ~{rpm_minus_2p:,} RPM for heavy hole-shot loads, while a {pitch_in + 2}\" pitch drops WOT to ~{rpm_plus_2p:,} RPM). If switching to a 4-blade stern-lift propeller, drop pitch to {four_blade_pitch}\" to maintain target WOT RPM.",
        "hardware_bundle": [
            {
                "badge": f"{dia_in}\" × {pitch_in}\" 3-Blade Prop",
                "title": f"{dia_in}\" × {pitch_in}\" Pitch Stainless Steel / High-Strength Aluminum 3-Blade Boat Propeller ({spline_spec})",
                "price_range": "$139 - $589",
                "amazon_query": f"{pitch_in} Pitch Boat Propeller 15 Spline Solas Mercury Yamaha",
                "prop_note": f"Cupped trailing-edge blades minimize cavitation and hold {slip_pct}% slip at {actual_gps_mph} MPH top speed."
            },
            {
                "badge": f"{four_blade_pitch}\" 4-Blade Hole-Shot Prop",
                "title": f"{dia_in}\" × {four_blade_pitch}\" Pitch 4-Blade Stern-Lift Propeller (Solas Rubex HR4 / Amita 4 / Spitfire)",
                "price_range": "$149 - $629",
                "amazon_query": f"{four_blade_pitch} Pitch 4 Blade Boat Propeller Solas Amita 4 Rubex Mercury Spitfire",
                "prop_note": "Delivers 30% faster hole-shot planing, eliminates pontoon/wake ventilation in sharp turns, and lowers minimum planing speed."
            },
            {
                "badge": "Flo-Torq II / Rubex Hub Kit",
                "title": f"Complete Shock-Absorbing Propeller Hub Kit ({spline_spec}) + Thrust Washer, Prop Nut & Wrench",
                "price_range": "$48 - $109",
                "amazon_query": "Flo Torq II Rubex Propeller Hub Kit 15 Spline Prop Wrench",
                "prop_note": "Sacrificial Delrin/rubber drive sleeve absorbs underwater stump strikes to save your $3,500 lower-unit prop shaft."
            },
            {
                "badge": "Jack Plate & Hydrofoil",
                "title": "4\"–6\" Adjustable Aluminum Outboard Transom Jack Plate + SE Sport 300/400 Hydrofoil Stabilizer",
                "price_range": "$79 - $649",
                "amazon_query": "Outboard Transom Jack Plate JPL4400 SE Sport 400 Hydrofoil",
                "prop_note": "Raises anti-ventilation plate height in clean water to reduce lower-unit drag and gain +150 RPM and +3 MPH."
            }
        ],
        "captain_checklist": [
            f"Always prop your outboard or sterndrive to reach the upper half of the manufacturer's WOT RPM range ({wot_rpm:,} RPM) with a normal fishing/passenger load: over-propping (too high pitch) lugs the engine below 5,000 RPM, causing carbon buildup, detonation, and ”making oil” (fuel dilution in 4-stroke crankcases).",
            f"Apply the 175-RPM-per-Inch Rule: if your current propeller only reaches {wot_rpm - 350:,} RPM at full throttle, drop down 2 inches in pitch (e.g., from {pitch_in + 2}\" to {pitch_in}\") to gain back +350 RPM.",
            f"Account for Blade Count & Material: switching from a 3-blade to a 4-blade propeller adds blade surface drag that drops WOT by ~150 RPM, so choose a {four_blade_pitch}\"-pitch 4-blade to match a {pitch_in}\"-pitch 3-blade.",
            "Inspect your forward Thrust Washer and torque the propeller nut to exact specification (typically 55 ft-lbs for Flo-Torq II, or snug for Rubex rubber hubs) with a new stainless cotter pin bent securely."
        ],
        "faqs": [
            {
                "q": f"How do I calculate Theoretical MPH and Propeller Slip % for {model_name}?",
                "a": f"First divide engine WOT RPM ({wot_rpm:,}) by the lower-unit gear ratio ({gear_ratio:.2f}) to get {prop_shaft_rpm:,} prop-shaft RPM. Multiply by {pitch_in}\" pitch and divide by 1,056 (inches per statute mile × 60 min/hr) to get {theo_mph} Theoretical MPH. At {actual_gps_mph} GPS MPH, slip is $(1 - [{actual_gps_mph} \\div {theo_mph}]) \\times 100 = {slip_pct}\\%$."
            },
            {
                "q": f"What happens if I change from a {pitch_in}-pitch to a {pitch_in + 2}-pitch or {pitch_in - 2}-pitch prop?",
                "a": f"Every 1 inch of pitch alters Wide-Open-Throttle RPM by 150 to 200 RPM. Dropping to a {pitch_in - 2}\"-pitch prop increases WOT by ~350 RPM (to ~{rpm_minus_2p:,} RPM) and boosts hole-shot acceleration for heavy loads or watersports. Stepping up to a {pitch_in + 2}\"-pitch prop lowers WOT by ~350 RPM (to ~{rpm_plus_2p:,} RPM)."
            },
            {
                "q": f"Should I run a 3-blade ({pitch_in}p) or 4-blade ({four_blade_pitch}p) propeller on {model_name}?",
                "a": f"Choose a 3-blade ({dia_in}\" × {pitch_in}\") stainless steel propeller for maximum top-end GPS speed on light-to-medium hulls. Choose a 4-blade ({dia_in}\" × {four_blade_pitch}\") propeller if you run a heavy pontoon, offshore center console, or tow wakeboarders/tubers where hole-shot stern lift and rough-water grip matter most."
            }
        ]
    }


def generate_prop_data(prop_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_prop_data(prop_tuple)

    model_name, wot_rpm, gear_ratio, pitch_in, dia_in, slip_pct, spline_spec = prop_tuple
    det_fallback = build_deterministic_prop_data(prop_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are an ABYC Certified Master Marine Technician & Naval Hydrodynamic Propeller Engineer. Create an accurate 2026 boat propeller pitch (inches), prop slip %, WOT RPM, and gear ratio guide for: "{model_name}".
Baseline specs: Target WOT={wot_rpm} RPM, Gear Ratio={gear_ratio}:1 ({sp['prop_shaft_rpm']} shaft RPM), Recommended 3-Blade={dia_in}" x {pitch_in}" Pitch (4-Blade={sp['four_blade_pitch_in']}" Pitch), Theoretical Speed={sp['theoretical_mph']} MPH, Slip={slip_pct}%, Actual GPS Speed={sp['actual_gps_mph']} MPH, Hub={spline_spec}.
Return ONLY a valid JSON object matching this exact schema:
{{
  "prop_name": "{model_name}",
  "spline_spec": "{spline_spec}",
  "seo_title": "{model_name} Propeller Pitch, Slip % & WOT RPM Calculator (2026)",
  "meta_description": "Calculate exact boat propeller pitch, hydrodynamic prop slip %, WOT RPM change per inch of pitch, and GPS speed for {model_name}.",
  "specs": {{
    "target_wot_rpm": {wot_rpm},
    "gear_ratio": {gear_ratio},
    "prop_shaft_rpm": {sp['prop_shaft_rpm']},
    "recommended_pitch_in": {pitch_in},
    "four_blade_pitch_in": {sp['four_blade_pitch_in']},
    "prop_diameter_in": {dia_in},
    "theoretical_mph": {sp['theoretical_mph']},
    "estimated_slip_pct": {slip_pct},
    "actual_gps_mph": {sp['actual_gps_mph']},
    "spline_spec": "{spline_spec}"
  }},
  "hydro_verdict": "3-sentence technical summary stating gear ratio, WOT RPM, 3-blade vs 4-blade pitch, theoretical vs actual GPS MPH at {slip_pct}% slip, and the 175-RPM-per-inch pitch rule.",
  "hardware_bundle": [
    {{
      "badge": "{dia_in}\" × {pitch_in}\" 3-Blade Prop",
      "title": "{dia_in}\" × {pitch_in}\" Pitch Stainless / Aluminum 3-Blade Boat Propeller ({spline_spec})",
      "price_range": "$139 - $589",
      "amazon_query": "{pitch_in} Pitch Boat Propeller 15 Spline Solas Mercury Yamaha",
      "prop_note": "1-sentence top-end MPH and blade cupping note"
    }},
    {{
      "badge": "{sp['four_blade_pitch_in']}\" 4-Blade Stern-Lift Prop",
      "title": "{dia_in}\" × {sp['four_blade_pitch_in']}\" Pitch 4-Blade High-Thrust Boat Propeller (Solas / Spitfire)",
      "price_range": "$149 - $629",
      "amazon_query": "{sp['four_blade_pitch_in']} Pitch 4 Blade Boat Propeller Solas Amita 4 Rubex",
      "prop_note": "1-sentence hole-shot planing and cornering grip note"
    }},
    {{
      "badge": "Flo-Torq II / Rubex Hub",
      "title": "Complete Shock-Absorbing Propeller Hub Kit ({spline_spec}) + Thrust Washer & Wrench",
      "price_range": "$48 - $109",
      "amazon_query": "Flo Torq II Rubex Propeller Hub Kit 15 Spline Prop Wrench",
      "prop_note": "1-sentence lower-unit impact protection note"
    }},
    {{
      "badge": "Jack Plate & Hydrofoil",
      "title": "Adjustable Aluminum Outboard Transom Jack Plate + Hydrofoil Planing Stabilizer",
      "price_range": "$79 - $649",
      "amazon_query": "Outboard Transom Jack Plate SE Sport 400 Hydrofoil",
      "prop_note": "1-sentence ventilation plate height and drag reduction note"
    }}
  ],
  "captain_checklist": [
    "Step 1 regarding propping to reach upper WOT RPM range ({wot_rpm} RPM) to prevent 4-stroke 'making oil'",
    "Step 2 regarding the 150-to-200 RPM change per 1 inch of propeller pitch",
    "Step 3 regarding dropping 1 to 2 inches of pitch when moving from 3-blade to 4-blade",
    "Step 4 regarding forward thrust washer orientation and 55 ft-lb prop nut torque"
  ],
  "faqs": [
    {{"q": "How do I calculate prop slip and top speed for {model_name}?", "a": "Exact RPM, gear ratio, 1056 constant, theoretical MPH, and GPS MPH."}},
    {{"q": "How much does 2 inches of pitch change RPM on {model_name}?", "a": "Exact RPM gain/loss for {pitch_in - 2}p vs {pitch_in}p vs {pitch_in + 2}p."}},
    {{"q": "What is normal propeller slip % for a bass boat vs center console vs pontoon?", "a": "Exact slip percentage ranges (6%-10% bass boat, 9%-13% deep-V, 14%-20% pontoon)."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_prop_html_page(data, slug, mon_cfg):
    prop_name = data.get("prop_name", "Outboard Boat Propeller")
    sp = data.get("specs", {})
    wot_rpm = int(safe_float(sp.get("target_wot_rpm", 5800), 5800))
    g_ratio = round(safe_float(sp.get("gear_ratio", 2.00), 2.00), 2)
    pitch_in = int(safe_float(sp.get("recommended_pitch_in", 17), 17))
    p4_in = int(safe_float(sp.get("four_blade_pitch_in", 15), 15))
    dia_in = round(safe_float(sp.get("prop_diameter_in", 14.25), 14.25), 2)
    theo_mph = round(safe_float(sp.get("theoretical_mph", 46.7), 46.7), 1)
    slip_pct = round(safe_float(sp.get("estimated_slip_pct", 10.0), 10.0), 1)
    gps_mph = round(safe_float(sp.get("actual_gps_mph", 42.0), 42.0), 1)
    spline_s = sp.get("spline_spec", "15-Spline Universal Hub")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Stainless+Steel+Boat+Propeller+Solas+Mercury+Yamaha"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{prop_name} Pitch, Slip % & WOT RPM Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Boat Propeller 15 Spline")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-blue-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Marine Hardware')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$59+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">⚓ {item.get('prop_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-blue-500 hover:bg-blue-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Pitch vs Theoretical MPH, Actual GPS MPH & WOT RPM Shift Matrix Table
    matrix_rows_html = ""
    for p_step in [pitch_in - 4, pitch_in - 2, pitch_in, pitch_in + 2, pitch_in + 4]:
        if p_step < 9:
            continue
        est_rpm = wot_rpm + int((pitch_in - p_step) * 175)
        t_spd = round((est_rpm * p_step) / (g_ratio * 1056.0), 1)
        g_spd = round(t_spd * (1.0 - (slip_pct / 100.0)), 1)
        role_note = "✅ Baseline Sweet Spot" if p_step == pitch_in else ("Hole-Shot / Heavy Load" if p_step < pitch_in else "Light Hull / Top Speed")
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{dia_in}" × {p_step}" Pitch</td>
          <td class="py-3 px-4 font-bold text-blue-400">~{est_rpm:,} WOT RPM</td>
          <td class="py-3 px-4 text-slate-300">{t_spd} MPH (0% Slip)</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{g_spd} MPH (@{slip_pct:.0f}% Slip)</td>
          <td class="py-3 px-4 text-xs text-slate-300">{role_note}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("captain_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-blue-500 rounded cursor-pointer prop-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>Marine Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', prop_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', prop_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-blue-500 text-slate-950 px-2 py-0.5 rounded font-black">PROP</span>PitchIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-blue-500 hover:bg-blue-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Propellers & Hub Kits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-blue-500 text-slate-950 px-3 py-1 rounded-full">{dia_in}" × {pitch_in}" 3-Blade ({p4_in}" 4-Blade)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">{gps_mph} MPH GPS ({slip_pct}% Slip)</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">{wot_rpm:,} WOT RPM | {g_ratio:.2f}:1 Ratio | {spline_s}</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', prop_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-blue-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>ABYC Hydrodynamic & WOT RPM Verdict:</strong> {data.get('hydro_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE PROPELLER PITCH, SLIP %, WOT RPM & GPS SPEED CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {prop_name} Pitch, Slip % & Speed Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your Wide-Open-Throttle (WOT) RPM, lower-unit gear ratio, propeller pitch, and hull slip % to compute exact theoretical MPH, actual GPS MPH, and 4-blade equivalent pitch.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="rpmSlider" class="text-slate-300">Wide-Open-Throttle Engine Speed (WOT RPM)</label>
              <span class="text-blue-400 font-bold"><span id="rpmVal">{wot_rpm:,}</span> RPM</span>
            </div>
            <input id="rpmSlider" type="range" min="4200" max="6400" step="100" value="{wot_rpm}" class="w-full accent-blue-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="ratioSelect" class="block text-xs font-medium text-slate-400 mb-1">Lower-Unit Gear Ratio</label>
              <select id="ratioSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500">
                <option value="1.47" {"selected" if g_ratio <= 1.55 else ""}>1.47:1 (MerCruiser V8 Alpha)</option>
                <option value="1.75" {"selected" if 1.55 < g_ratio <= 1.80 else ""}>1.75:1 (Merc V8 / Yam V6)</option>
                <option value="1.86" {"selected" if 1.80 < g_ratio <= 1.95 else ""}>1.86:1 / 1.92:1 (150–200 HP)</option>
                <option value="2.00" {"selected" if 1.95 < g_ratio <= 2.04 else ""}>2.00:1 (Yamaha F150 Std)</option>
                <option value="2.07" {"selected" if 2.04 < g_ratio <= 2.12 else ""}>2.07:1 (Mercury 90–115 HP)</option>
                <option value="2.15" {"selected" if 2.12 < g_ratio <= 2.25 else ""}>2.15:1 (Yamaha F90–F115)</option>
                <option value="2.38" {"selected" if 2.25 < g_ratio <= 2.45 else ""}>2.38:1 (Command Thrust / Pontoon)</option>
                <option value="2.59" {"selected" if g_ratio > 2.45 else ""}>2.50:1 / 2.59:1 (Suzuki High-Ratio)</option>
              </select>
            </div>
            <div>
              <label for="slipSelect" class="block text-xs font-medium text-slate-400 mb-1">Boat Hull Type (Prop Slip %)</label>
              <select id="slipSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500">
                <option value="8.0" {"selected" if slip_pct <= 8.8 else ""}>Bass Boat / High-Perf (8% Slip)</option>
                <option value="10.5" {"selected" if 8.8 < slip_pct <= 11.5 else ""}>Center Console / Runabout (10.5%)</option>
                <option value="13.0" {"selected" if 11.5 < slip_pct <= 14.2 else ""}>Heavy Deep-V / Walkaround (13%)</option>
                <option value="16.0" {"selected" if slip_pct > 14.2 else ""}>Pontoon / Tritoon Boat (16% Slip)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="pitchSlider" class="text-slate-300">3-Blade Propeller Pitch (Inches)</label>
              <span class="text-blue-400 font-bold"><span id="pitchVal">{pitch_in}</span>" Pitch</span>
            </div>
            <input id="pitchSlider" type="range" min="9" max="27" step="1" value="{pitch_in}" class="w-full accent-blue-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-blue-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-blue-400 font-bold">Actual GPS Top Speed</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="gpsMphOut">{gps_mph}</span> <span class="text-xs font-normal text-slate-400">MPH</span></div>
            <p id="theoNoteOut" class="text-xs text-blue-400 font-semibold mt-1">Zero-Slip Theo: {theo_mph} MPH</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Matched 4-Blade Pitch</span>
            <div id="fourBladeOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{p4_in}" Pitch 4-Blade</div>
            <p id="shaftRpmOut" class="text-xs text-slate-300 font-semibold mt-1">Prop Shaft: {int(wot_rpm / g_ratio):,} RPM</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-blue-950/40 border border-blue-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="propAdviceBanner" class="text-sm text-blue-100 font-medium"></div>
        <a id="dynamicPropBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-blue-500 hover:bg-blue-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Propeller & Hub Kit on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {prop_name} 3-Blade, 4-Blade & Hub Kit Bundle</h2>
        <span class="text-xs text-slate-400">OEM Spline Fitment & Shock-Hub Protected</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">{prop_name} Pitch vs. WOT RPM & GPS Speed Comparison Table</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Propeller Size</th>
              <th class="py-3.5 px-4 text-blue-400">Est. WOT RPM</th>
              <th class="py-3.5 px-4">Theoretical MPH</th>
              <th class="py-3.5 px-4 text-emerald-400">Actual GPS MPH</th>
              <th class="py-3.5 px-4">Performance Profile</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">ABYC Marine WOT Propping, 4-Blade Conversion & Hub Torque Checklist</h2>
        <span id="propBadge" class="text-xs font-bold bg-slate-800 text-blue-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({prop_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} PropPitchIndex. Independent Marine Hydrodynamic Propeller Pitch & Slip Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const rpmSlider = document.getElementById('rpmSlider');
    const ratioSelect = document.getElementById('ratioSelect');
    const slipSelect = document.getElementById('slipSelect');
    const pitchSlider = document.getElementById('pitchSlider');
    const rpmVal = document.getElementById('rpmVal');
    const pitchVal = document.getElementById('pitchVal');
    const gpsMphOut = document.getElementById('gpsMphOut');
    const theoNoteOut = document.getElementById('theoNoteOut');
    const fourBladeOut = document.getElementById('fourBladeOut');
    const shaftRpmOut = document.getElementById('shaftRpmOut');
    const propAdviceBanner = document.getElementById('propAdviceBanner');
    const dynamicPropBtn = document.getElementById('dynamicPropBtn');

    function recalculateProp() {{
      const rpm = parseInt(rpmSlider.value, 10);
      const ratio = parseFloat(ratioSelect.value);
      const slipPct = parseFloat(slipSelect.value);
      const pitch = parseInt(pitchSlider.value, 10);

      rpmVal.textContent = rpm.toLocaleString();
      pitchVal.textContent = pitch;

      const shaftRpm = Math.round(rpm / ratio);
      const theoMph = (rpm * pitch) / (ratio * 1056.0);
      const gpsMph = theoMph * (1.0 - (slipPct / 100.0));
      const p4Pitch = Math.max(9, pitch >= 17 ? pitch - 2 : pitch - 1);

      gpsMphOut.textContent = gpsMph.toFixed(1);
      theoNoteOut.textContent = `Zero-Slip Theo: ${{theoMph.toFixed(1)}} MPH`;
      fourBladeOut.textContent = `${{p4Pitch}}" Pitch 4-Blade`;
      shaftRpmOut.textContent = `Prop Shaft: ${{shaftRpm.toLocaleString()}} RPM`;

      propAdviceBanner.innerHTML = `⚓ <strong>Marine Prop Spec:</strong> At ${{rpm.toLocaleString()}} RPM (${{ratio.toFixed(2)}}:1 ratio), run a <strong>${{pitch}}"-Pitch 3-Blade Stainless Propeller</strong> for <strong>${{gpsMph.toFixed(1)}} MPH top speed</strong>, or a <strong>${{p4Pitch}}"-Pitch 4-Blade Propeller</strong> + <strong>Flo-Torq II / Rubex Hub Kit</strong> for maximum hole-shot stern lift.`;
      dynamicPropBtn.href = `https://${{amzDomain}}/s?k=${{pitch}}+Pitch+Boat+Propeller+15+Spline+Solas+Mercury+Yamaha+Hub+Kit&tag=${{amzTag}}`;
    }}

    rpmSlider.addEventListener('input', recalculateProp);
    ratioSelect.addEventListener('change', recalculateProp);
    slipSelect.addEventListener('change', recalculateProp);
    pitchSlider.addEventListener('input', recalculateProp);
    recalculateProp();

    const checks = document.querySelectorAll('.prop-check');
    const badge = document.getElementById('propBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Stainless+Steel+Boat+Propeller+Solas+Mercury+Yamaha"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-blue-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-blue-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('pitch', 17)}" Pitch ({item.get('mph', 42.0)} MPH)</span>
            <span class="text-xs text-slate-400">{item.get('ratio', 2.0):.2f}:1 | {item.get('slip', 10.0)}% Slip</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-blue-400 transition">{item['prop_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-blue-400">Calculate Pitch, Slip % & WOT RPM →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PropPitchIndex — Boat Propeller Pitch, Slip %, WOT RPM & Gear Ratio Calculator (2026)</title>
  <meta name="description" content="Calculate exact outboard and sterndrive boat propeller pitch, hydrodynamic prop slip %, WOT RPM change per inch of pitch, and 3-blade vs 4-blade sizing for Yamaha, Mercury, Suzuki, Honda, Tohatsu, and MerCruiser engines.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="PropPitchIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-blue-500 text-slate-950 px-2 py-0.5 rounded font-black">PROP</span>PitchIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-blue-500 hover:bg-blue-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Propellers & Hub Kits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Boat Propeller Pitch, Slip %, WOT RPM & Gear Ratio Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your outboard/sterndrive engine or boat hull below to calculate theoretical vs. GPS speed, propeller slip %, 3-blade to 4-blade pitch conversion, and WOT RPM tuning.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search engine or hull (e.g. Yamaha F150, Mercury 115 Pro XS, Suzuki DF140, MerCruiser Alpha One, Pontoon, 19 Pitch...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-blue-500">
      </div>
    </div>

    <div id="propGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} PropPitchIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('propGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>PropPitchIndex Boat Propeller Pitch & Slip Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Outboard & Sterndrive Boat Propeller Pitch, Slip % & WOT RPM Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_PROP:
        candidates.append((CUSTOM_PROP.strip(), 5800, 2.00, 17, 14.25, 10.0, "15-Spline Universal Hub"))
    candidates.extend(SEED_PROPELLERS)
    candidates.extend(discover_google_prop_queries(published_slugs))

    new_urls = []
    count = 0

    for prop_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        p_name = prop_tuple[0]
        slug = slugify(f"{p_name}-propeller-pitch-slip-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating boat propeller pitch & slip calculator for: {p_name}...")
        try:
            data = generate_prop_data(prop_tuple)
            build_prop_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "prop_name": data.get("prop_name", p_name),
                "slug": slug,
                "title": data.get("seo_title", f"{p_name} Propeller Calculator"),
                "description": data.get("meta_description", ""),
                "pitch": int(safe_float(sp.get("recommended_pitch_in", prop_tuple[3]), prop_tuple[3])),
                "ratio": round(safe_float(sp.get("gear_ratio", prop_tuple[2]), prop_tuple[2]), 2),
                "mph": round(safe_float(sp.get("actual_gps_mph", 42.0), 42.0), 1),
                "slip": round(safe_float(sp.get("estimated_slip_pct", prop_tuple[5]), prop_tuple[5]), 1),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {p_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new boat propeller pitch & slip calculator pages.")


if __name__ == "__main__":
    main()
