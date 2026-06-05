import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from meal_history import load_history, clear_history


def extract_macros(text):
    protein = 0
    carbs = 0
    fats = 0

    protein_match = re.search(
        r"Protein.*?(\d+)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    carbs_match = re.search(
        r"Carb(?:ohydrates?)?.*?(\d+)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    fats_match = re.search(
        r"Fat(?:s)?.*?(\d+)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if protein_match:
        protein = int(protein_match.group(1))

    if carbs_match:
        carbs = int(carbs_match.group(1))

    if fats_match:
        fats = int(fats_match.group(1))

    return protein, carbs, fats


def show_dashboard(nutrition_text):

    if not nutrition_text:
        return

    st.subheader("📊 Nutrition Dashboard")

    protein, carbs, fats = extract_macros(nutrition_text)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("💪 Protein", f"{protein} g")

    with col2:
        st.metric("🍞 Carbs", f"{carbs} g")

    with col3:
        st.metric("🥑 Fats", f"{fats} g")

    total = protein + carbs + fats

    if total > 0:
        df = pd.DataFrame({
            "Nutrient": ["Protein", "Carbs", "Fats"],
            "Amount": [protein, carbs, fats]
        })

        fig = px.pie(
            df,
            values="Amount",
            names="Nutrient",
            title="Macronutrient Distribution",
            color_discrete_sequence=["#4CAF50", "#FF9800", "#2196F3"]
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("⚠️ Could not extract macros from the analysis. Try re-analyzing.")


def show_history_dashboard():

    st.subheader("📈 Your Meal History & Progress")

    history = load_history()

    if not history:
        st.info("No meal history yet. Analyze a meal to start tracking!")
        return

    df = pd.DataFrame(history)
    df["datetime"] = df["date"] + " " + df["time"]
    df["meal_number"] = range(1, len(df) + 1)

    scored = df[df["score"].notna()].copy()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("🍽️ Total Meals", len(df))

    with col2:
        if not scored.empty:
            avg = round(scored["score"].mean(), 1)
            st.metric("⭐ Avg Score", f"{avg}/100")
        else:
            st.metric("⭐ Avg Score", "N/A")

    with col3:
        if not scored.empty:
            best = int(scored["score"].max())
            st.metric("🏆 Best Score", f"{best}/100")
        else:
            st.metric("🏆 Best Score", "N/A")

    with col4:
        if not scored.empty and len(scored) >= 2:
            first = scored["score"].iloc[0]
            last = scored["score"].iloc[-1]
            delta = round(last - first, 1)
            sign = "+" if delta > 0 else ""
            st.metric("📉 Trend", f"{sign}{delta} pts")
        else:
            st.metric("📉 Trend", "Need 2+ meals")

    st.divider()

    if not scored.empty:
        st.markdown("### 🎯 Health Score Over Time")

        fig_line = go.Figure()

        fig_line.add_trace(go.Scatter(
            x=scored["meal_number"],
            y=scored["score"],
            mode="lines+markers+text",
            text=scored["score"].astype(int).astype(str),
            textposition="top center",
            line=dict(color="#4CAF50", width=3),
            marker=dict(size=10, color="#4CAF50"),
            name="Meal Score"
        ))

        fig_line.add_hline(
            y=70,
            line_dash="dash",
            line_color="orange",
            annotation_text="Good threshold (70)",
            annotation_position="bottom right"
        )

        fig_line.add_hline(
            y=50,
            line_dash="dash",
            line_color="red",
            annotation_text="Poor threshold (50)",
            annotation_position="bottom right"
        )

        fig_line.update_layout(
            xaxis_title="Meal #",
            yaxis_title="Score /100",
            yaxis=dict(range=[0, 105]),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False
        )

        st.plotly_chart(fig_line, use_container_width=True)

    if len(df) >= 2:
        st.markdown("### 🩺 Meals by Health Condition")

        condition_counts = df["health_condition"].value_counts().reset_index()
        condition_counts.columns = ["Condition", "Count"]

        fig_bar = px.bar(
            condition_counts,
            x="Condition",
            y="Count",
            color="Condition",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )

        fig_bar.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### 🗂️ Recent Meals")

    display_df = df[["date", "time", "health_condition", "score"]].copy()
    display_df.columns = ["Date", "Time", "Condition", "Score"]
    display_df["Score"] = display_df["Score"].apply(
        lambda x: f"{int(x)}/100" if pd.notna(x) else "N/A"
    )

    st.dataframe(
        display_df.iloc[::-1].reset_index(drop=True),
        use_container_width=True
    )

    st.divider()

    if st.button("🗑️ Clear All History"):
        clear_history()
        st.success("History cleared!")
        st.rerun()


def daily_challenge(health_condition):

    st.subheader("🎯 Personalized Daily Challenge")

    challenges = {
        "PCOS":
        "Include one anti-inflammatory food today (salmon, walnuts, chia seeds, turmeric).",
        "Prediabetes":
        "Replace one refined carbohydrate with a whole grain or vegetable today.",
        "Gluten Sensitivity":
        "Check every food label today for hidden gluten (soy sauce, malt, modified starch).",
        "Fatty Liver":
        "Eliminate one source of added sugar or alcohol today.",
        "Hypertension":
        "Keep sodium under 1500mg today — avoid processed, canned, or restaurant food.",
        "High Cholesterol":
        "Add one source of soluble fiber today (oats, flaxseed, beans, apples).",
        "IBS":
        "Identify and avoid one high-FODMAP food today (onion, garlic, wheat, lactose).",
        "General":
        "Add two servings of vegetables to your meals today."
    }

    challenge = challenges.get(
        health_condition,
        f"Research one evidence-based dietary habit that supports {health_condition} management today."
    )

    st.info(f"💡 {challenge}")


def meal_grade(call_groq, nutrition_result, health_condition):

    if not nutrition_result:
        return

    if st.button("🏆 Generate Meal Grade"):

        prompt = f"""
You are a strict clinical nutrition grading system. Your evaluations must reflect medical reality, not be encouraging or diplomatic.

Grade this meal for a patient with {health_condition} across 4 clinical categories:

---

1. PROTEIN QUALITY (0-25)
Evaluate source, completeness, and amount:
- 22-25: Lean complete protein (grilled chicken breast, fish, eggs, legumes) in adequate portion
- 15-21: Adequate protein but source is fatty, processed, or portion is small
- 8-14: Some protein present but insufficient or low quality
- 0-7: Negligible or no quality protein

2. CARBOHYDRATE QUALITY (0-25)
Evaluate glycemic impact, fiber content, and source:
- 22-25: Whole grains, legumes, vegetables — high fiber, low glycemic
- 15-21: Mixed refined and complex carbs, moderate fiber
- 8-14: Mostly refined carbs, low fiber
- 0-7: Pure refined carbs (white rice, white bread, pastry, sugary foods) — MANDATORY for Prediabetes/PCOS if white rice or refined starch is the main carb source

HARD RULE: White rice, naan, white bread as primary carb = max 7/25 for Prediabetes and PCOS. No exceptions.

3. FAT QUALITY (0-25)
Evaluate fat type and cooking method:
- 22-25: Unsaturated fats (olive oil, avocado, nuts, fatty fish)
- 15-21: Mixed fats, moderate saturated fat
- 8-14: High saturated fat (ghee, cream, fatty cuts of meat)
- 0-7: Fried food, trans fats, excessive oil, heavily ghee-based

HARD RULE: Fried food or ghee-heavy cooking = max 7/25 for High Cholesterol and Fatty Liver.

4. CONDITION SUITABILITY FOR {health_condition} (0-25)
How well does this meal support management of {health_condition}?
- 22-25: Meal actively supports {health_condition} management — correct macros, anti-inflammatory, low glycemic
- 15-21: Partially suitable — some good elements but notable concerns
- 8-14: Mostly unsuitable — several ingredients worsen {health_condition}
- 0-7: Clinically inappropriate — meal contains multiple ingredients that directly worsen {health_condition}

CONDITION-SPECIFIC HARD RULES:
- Prediabetes: high glycemic meal = max 8/25 suitability
- PCOS: high glycemic + inflammatory meal = max 8/25 suitability
- Gluten Sensitivity: gluten present = max 3/25 suitability
- Hypertension: high sodium meal = max 8/25 suitability
- High Cholesterol: high saturated fat = max 8/25 suitability
- Fatty Liver: high fat + high sugar = max 8/25 suitability
- IBS: high FODMAP ingredients = max 8/25 suitability

---

TOTAL SCORE = sum of all 4 categories /100

GRADE:
90-100 = A+ (Excellent)
80-89 = A  (Very Good)
70-79 = B+ (Good)
60-69 = B  (Acceptable)
50-59 = C  (Poor)
30-49 = D  (Bad)
Below 30 = F (Clinically Harmful for this condition)

---

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

## 📊 Detailed Scoring

| Category | Score | Reason |
|---|---|---|
| Protein Quality | X/25 | one sentence |
| Carbohydrate Quality | X/25 | one sentence |
| Fat Quality | X/25 | one sentence |
| Condition Suitability ({health_condition}) | X/25 | one sentence |
| **TOTAL** | **X/100** | |

## 🎓 Grade: [LETTER]

## 👨‍⚕️ Doctor's Verdict
One honest sentence a doctor would say to this patient about this meal.

## ⚠️ What to Fix Next Time
3 bullet points — specific ingredient swaps with medical reasoning.

---

Meal Analysis:
{nutrition_result}
"""

        result = call_groq([{"role": "user", "content": prompt}])

        st.subheader("🏆 Meal Grade Report")
        st.markdown(result)


def nutritionist_opinion(call_groq, nutrition_result, health_condition):

    if not nutrition_result:
        return

    if st.button("👨‍⚕️ Nutritionist Opinion"):

        prompt = f"""
Act as a registered dietitian giving a frank clinical opinion.

Would you approve this meal for a patient with {health_condition}?

Be direct. If the meal is bad for the condition, say so clearly.
Reference specific ingredients and their medical impact on {health_condition}.

Condition: {health_condition}
Meal Analysis: {nutrition_result}
"""

        result = call_groq([{"role": "user", "content": prompt}])

        st.subheader("👨‍⚕️ Nutritionist Opinion")
        st.markdown(result)


def healthier_alternative(call_groq, nutrition_result, health_condition):

    if not nutrition_result:
        return

    if st.button("✨ Healthier Alternative"):

        prompt = f"""
Create a clinically improved version of this meal for someone with {health_condition}.

Rules:
- Keep the cuisine style and general flavor profile similar
- Replace every ingredient that is problematic for {health_condition}
- Explain each swap with a one-line medical reason
- Provide estimated improved macros

Condition: {health_condition}
Meal Analysis: {nutrition_result}
"""

        result = call_groq([{"role": "user", "content": prompt}])

        st.subheader("✨ Healthier Alternative")
        st.markdown(result)


def grocery_list(call_groq, nutrition_result, health_condition):

    if not nutrition_result:
        return

    if st.button("🛒 Grocery List"):

        prompt = f"""
Create a weekly grocery list for someone with {health_condition}.

Base it on replacing the problematic elements in this meal analysis.

Sections:
- Proteins
- Vegetables & Fiber
- Healthy Fats
- Whole Grains
- Snacks
- Avoid List (ingredients this condition should eliminate)

Condition: {health_condition}
Meal Analysis: {nutrition_result}
"""

        result = call_groq([{"role": "user", "content": prompt}])

        st.subheader("🛒 Smart Grocery List")
        st.markdown(result)


def meal_plan(call_groq, nutrition_result, health_condition):

    if not nutrition_result:
        return

    if st.button("📅 One-Day Meal Plan"):

        prompt = f"""
Create a clinically appropriate one-day meal plan for someone with {health_condition}.

Requirements:
- Every meal must be suitable for {health_condition}
- Include macros for each meal
- Explain in one sentence why each meal is appropriate for {health_condition}
- Include: Breakfast, Lunch, Dinner, Snack

Condition: {health_condition}
Based on nutritional context: {nutrition_result}
"""

        result = call_groq([{"role": "user", "content": prompt}])

        st.subheader("📅 Personalized Meal Plan")
        st.markdown(result)


def healthy_swaps(call_groq, nutrition_result, health_condition):

    if not nutrition_result:
        return

    if st.button("🔄 Healthy Swaps"):

        prompt = f"""
Suggest clinically justified food swaps for someone with {health_condition}.

Format each swap as:
❌ [Current food] → ✅ [Better alternative]
📋 Why: [One sentence medical reason specific to {health_condition}]

Provide at least 5 swaps based on the meal analysis.

Condition: {health_condition}
Meal: {nutrition_result}
"""

        result = call_groq([{"role": "user", "content": prompt}])

        st.subheader("🔄 Healthy Swaps")
        st.markdown(result)


def future_risk_assessment(call_groq, nutrition_result, health_condition):

    if not nutrition_result:
        return

    if st.button("⚠️ Future Health Risks"):

        prompt = f"""
You are a clinical dietitian. Based on this meal, assess the long-term health risks
if a patient with {health_condition} eats meals like this regularly (5+ times per week).

Structure your response as:
## Short-Term Risks (days-weeks)
## Long-Term Risks (months-years)
## Lab Values Likely to Worsen
## When to See a Doctor

Be medically accurate and specific. Do not soften the risks.

Condition: {health_condition}
Meal: {nutrition_result}
"""

        result = call_groq([{"role": "user", "content": prompt}])

        st.subheader("⚠️ Future Health Risks")
        st.markdown(result)