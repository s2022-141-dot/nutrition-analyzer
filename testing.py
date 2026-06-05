import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import requests
import base64
import os
import hashlib
from wow_features import *
from meal_history import save_meal, extract_score_from_result

load_dotenv()
st.write("Secrets available:", list(st.secrets.keys()))
api_key = st.secrets.get(
    "GROQ_API_KEY",
    os.getenv("GROQ_API_KEY")
)

if not api_key:
    st.error("GROQ_API_KEY not found")
    st.stop()

st.set_page_config(
    page_title="AI Nutrition Plate Analyzer",
    page_icon="🥗",
    layout="centered"
)

st.title("🥗 AI-Powered Nutrition Plate Analyzer")
st.write("Upload a food image and get personalized healthcare recommendations.")

if "image_hash" not in st.session_state:
    st.session_state.image_hash = None

if "nutrition_result" not in st.session_state:
    st.session_state.nutrition_result = None

if "recommendation_result" not in st.session_state:
    st.session_state.recommendation_result = None

if "last_health_condition" not in st.session_state:
    st.session_state.last_health_condition = None

if "meal_saved" not in st.session_state:
    st.session_state.meal_saved = False

if "last_nutrition_condition" not in st.session_state:
    st.session_state.last_nutrition_condition = None


def call_groq(messages):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": messages,
            "max_tokens": 1500
        },
        timeout=180
    )

    data = response.json()

    if response.status_code != 200:
        raise Exception(str(data))

    if "choices" not in data or len(data["choices"]) == 0:
        raise Exception(f"Unexpected API response: {data}")

    content = data["choices"][0]["message"].get("content")

    if not content:
        raise Exception("The AI returned an empty response. Please try again.")

    return content


tab1, tab2 = st.tabs(["🍽️ Analyze Meal", "📈 My Progress"])

with tab1:

    health_condition = st.selectbox(
        "🩺 Select Your Health Profile",
        [
            "General",
            "Prediabetes",
            "PCOS",
            "Gluten Sensitivity",
            "Fatty Liver",
            "Hypertension",
            "High Cholesterol",
            "IBS",
            "Other Medical Condition"
        ]
    )

    custom_condition = ""

    if health_condition == "Other Medical Condition":
        custom_condition = st.text_input("Enter your medical condition")
        if custom_condition.strip():
            health_condition = custom_condition

    uploaded_file = st.file_uploader(
        "📸 Upload Your Meal Image",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Meal", use_container_width=True)

        uploaded_file.seek(0)
        image_bytes = uploaded_file.read()
        current_hash = hashlib.md5(image_bytes).hexdigest()

        # Reset everything if new image uploaded
        if st.session_state.image_hash != current_hash:
            st.session_state.image_hash = current_hash
            st.session_state.nutrition_result = None
            st.session_state.recommendation_result = None
            st.session_state.last_health_condition = None
            st.session_state.last_nutrition_condition = None
            st.session_state.meal_saved = False

        if st.button("🔍 Analyze Meal"):

            st.session_state.meal_saved = False

            # Re-run nutrition analysis if image changed OR condition changed
            if (
                st.session_state.nutrition_result is None
                or st.session_state.last_nutrition_condition != health_condition
            ):
                try:
                    with st.spinner("🍽️ Analyzing food with your health profile in mind..."):

                        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                        file_type = uploaded_file.type

                        nutrition_prompt = f"""
You are a precise clinical nutrition AI analyzing a meal image for a patient with {health_condition}.

Your entire analysis must be filtered through the lens of {health_condition}.
Every number you estimate, every flag you raise, every comment you make must be relevant to {health_condition}.

CRITICAL ASSUMPTION RULES:
- If cooking method is unclear, assume traditional high-oil/ghee preparation — never assume healthy preparation.
- For South Asian dishes (karahi, biryani, curry, halwa, nihari, paratha, pulao): assume significant oil/ghee unless clearly visible otherwise.
- For processed or packaged-looking food: assume high sodium and preservatives.
- Never give benefit of the doubt on unknown ingredients — assume the less healthy option.
- A patient's health depends on accurate assessment, not optimistic assumptions.

Analyze this meal and provide:

# Food Items Identified
List every food item visible. Be specific about cooking method (fried, grilled, steamed, curry-based, etc).
If it is a South Asian dish, name it specifically (e.g. chicken karahi, dal makhani, biryani).

# Estimated Nutrition (per serving)
Estimate conservatively — assume realistic home/restaurant preparation.
- Calories: X kcal
- Protein: X g
- Carbohydrates: X g
- Fats: X g
- Saturated Fat: X g
- Fiber: X g
- Sugar: X g
- Sodium: X mg

# Glycemic Index Assessment
Low / Medium / High — explain specifically why in context of {health_condition}.

# Condition-Specific Red Flags for {health_condition}
List every ingredient or nutritional aspect that is directly problematic for {health_condition}.
Be medically specific — explain the mechanism (e.g. "white rice causes rapid glucose spike worsening insulin resistance in PCOS").

Condition guidance:
- Prediabetes: flag refined carbs, added sugars, high GI foods, low fiber
- PCOS: flag high GI foods, saturated fat, inflammatory ingredients, low fiber
- Fatty Liver: flag saturated fat, added sugars, high sodium, alcohol, processed foods, excessive oil/ghee
- Hypertension: flag high sodium, saturated fat, processed meats, excessive caffeine
- High Cholesterol: flag saturated fat, trans fat, dietary cholesterol, refined carbs
- Gluten Sensitivity: flag any gluten-containing ingredient (wheat, barley, rye, soy sauce, malt)
- IBS: flag high-FODMAP foods (onion, garlic, wheat, lactose, excess fructose)
- General: flag excess calories, low nutrients, processed ingredients

# Portion Assessment
Comment on portion sizes in context of {health_condition}.
Flag if any component is oversized relative to what is safe for {health_condition}.

# Key Micronutrients
List 4-5 vitamins/minerals present and their relevance specifically to {health_condition} management.

Be specific, clinical, and concise. Use markdown formatting.
"""

                        nutrition_messages = [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": nutrition_prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{file_type};base64,{image_base64}"
                                        }
                                    }
                                ]
                            }
                        ]

                        st.session_state.nutrition_result = call_groq(nutrition_messages)
                        st.session_state.last_nutrition_condition = health_condition
                        # Reset recommendation so it re-runs with new nutrition
                        st.session_state.recommendation_result = None

                except Exception as e:
                    st.error(f"❌ Nutrition Analysis Error: {str(e)}")
                    st.stop()

            if (
                st.session_state.recommendation_result is None
                or st.session_state.last_health_condition != health_condition
            ):
                try:
                    with st.spinner("🩺 Generating clinical assessment..."):

                        recommendation_prompt = f"""
You are a strict, evidence-based clinical nutritionist AI. A patient with {health_condition} has uploaded their meal.

Your job is to evaluate this meal with medical accuracy. Do NOT be encouraging at the expense of clinical truth.
A bad meal for {health_condition} must be scored and described as bad — even if it looks tasty or culturally common.

CRITICAL: This entire assessment is specifically for {health_condition}. Every sentence must reference {health_condition}.
If cooking method or ingredients are unclear, always assume the less healthy preparation.
For South Asian dishes, always assume high oil, ghee, and sodium.

---

# Health Score (X/100)

Score this meal strictly. START at 100. Deduct for every issue:

DEDUCTIONS:
- Refined carbohydrates (white rice, naan, white bread, pasta): -20 for Prediabetes/PCOS, -10 for others
- Fried food or oil/ghee-heavy cooking: -20 for Fatty Liver, -15 for High Cholesterol, -10 for others
- High saturated fat (ghee, cream, fatty meat, skin-on chicken): -20 for Fatty Liver/High Cholesterol, -10 for others
- Low fiber (under 5g): -15 for Prediabetes/PCOS/IBS, -8 for others
- High sugar (over 8g): -20 for Prediabetes, -15 for PCOS/Fatty Liver, -5 for others
- High sodium (over 600mg): -20 for Hypertension, -10 for Fatty Liver, -5 for others
- Gluten present: -30 for Gluten Sensitivity, 0 for others
- No vegetables: -10 for all
- Processed/ultra-processed ingredients: -12 for all
- Oversized portions: -10 for all
- Inflammatory spice overload or heavy sauce: -10 for IBS/Fatty Liver

ADDITIONS (only add if genuinely present):
- Lean protein (chicken breast, fish, eggs, legumes): +5
- Fiber-rich vegetables clearly visible: +8
- Whole grains confirmed: +8
- Anti-inflammatory ingredients (turmeric, olive oil, leafy greens): +5 for PCOS/Fatty Liver
- Low GI meal overall: +8 for Prediabetes/PCOS
- Balanced macros: +5

HARD CAPS — never exceed these regardless of additions:
- Biryani/fried rice/pilaf (white rice base): max 40/100 for Prediabetes/PCOS
- Karahi/curry with visible oil/ghee: max 45/100 for Fatty Liver/High Cholesterol
- Fried fast food: max 30/100 for any condition
- Sugary desserts/drinks: max 25/100 for Prediabetes/PCOS
- Gluten meal for Gluten Sensitivity: max 15/100
- Processed meat heavy meal: max 40/100 for Hypertension
- High FODMAP meal for IBS: max 45/100

Show score as: **Health Score: X/100**

---

# Clinical Verdict
One sentence. Brutally honest. A doctor reviewing this patient's food diary would say:

---

# Top Strengths ✅
Maximum 3. Only list real strengths. Do not invent positives that do not exist.
If the meal has no genuine strengths for {health_condition}, say so directly.

---

# Top Concerns 🚨
The 3 most clinically dangerous aspects for {health_condition}.
Format: [Ingredient/issue] — [exact medical mechanism for {health_condition}]

---

# Specific Improvements
3 swaps. Format:
❌ [Current] → ✅ [Better] — [one sentence medical reason for {health_condition}]

---

# Clinical Reasoning
4-5 sentences. Use clinical language. Reference specific ingredients.
Explain the exact metabolic/physiological impact on {health_condition}.
Do not generalize — be condition-specific in every sentence.

---

ABSOLUTE RULES:
- Never use words like "balanced", "moderate", "not bad" for a meal with clear red flags for {health_condition}.
- Never exceed the hard caps above.
- If the meal is bad for {health_condition}, the score must reflect that — below 50 means below 50.
- Do NOT change any calorie or macro numbers from the nutritional analysis.
- Mention {health_condition} by name in every section.

NUTRITIONAL ANALYSIS:
{st.session_state.nutrition_result}
"""

                        recommendation_messages = [
                            {
                                "role": "user",
                                "content": recommendation_prompt
                            }
                        ]

                        st.session_state.recommendation_result = call_groq(recommendation_messages)
                        st.session_state.last_health_condition = health_condition

                except Exception as e:
                    st.error(f"❌ Recommendation Error: {str(e)}")
                    st.stop()

            if not st.session_state.meal_saved:
                score = extract_score_from_result(st.session_state.recommendation_result)
                save_meal(
                    st.session_state.nutrition_result,
                    st.session_state.recommendation_result,
                    health_condition,
                    score
                )
                st.session_state.meal_saved = True

    if st.session_state.nutrition_result:
        st.subheader("🍽️ Nutritional Analysis")
        st.markdown(st.session_state.nutrition_result)

    if st.session_state.recommendation_result:
        st.subheader(f"🩺 Clinical Assessment for {health_condition}")
        st.markdown(st.session_state.recommendation_result)
        st.success("✅ Analysis Complete! Meal saved to history.")

    show_dashboard(st.session_state.nutrition_result)

    daily_challenge(health_condition)

    meal_grade(
        call_groq,
        st.session_state.nutrition_result,
        health_condition
    )

with tab2:

    show_history_dashboard()

