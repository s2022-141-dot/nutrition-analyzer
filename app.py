import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import requests
import base64
import os
import hashlib

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("GROQ_API_KEY not found in .env file")
    st.stop()

st.set_page_config(
    page_title="AI Nutrition Plate Analyzer",
    page_icon="🥗",
    layout="centered"
)

st.title("🥗 AI-Powered Nutrition Plate Analyzer")
st.write("Upload a food image and get personalized healthcare recommendations.")

health_condition = st.selectbox(
    "🩺 Select Your Health Profile",
    [
        "General",
        "Prediabetes",
        "PCOS",
        "Gluten Sensitivity"
    ]
)

uploaded_file = st.file_uploader(
    "📸 Upload Your Meal Image",
    type=["jpg", "jpeg", "png"]
)

if "image_hash" not in st.session_state:
    st.session_state.image_hash = None

if "nutrition_result" not in st.session_state:
    st.session_state.nutrition_result = None

if "recommendation_result" not in st.session_state:
    st.session_state.recommendation_result = None

if "last_health_condition" not in st.session_state:
    st.session_state.last_health_condition = None


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


if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Meal", use_container_width=True)

    uploaded_file.seek(0)
    image_bytes = uploaded_file.read()
    current_hash = hashlib.md5(image_bytes).hexdigest()

    if st.session_state.image_hash != current_hash:
        st.session_state.image_hash = current_hash
        st.session_state.nutrition_result = None
        st.session_state.recommendation_result = None
        st.session_state.last_health_condition = None

    if st.button("🔍 Analyze Meal"):

        if st.session_state.nutrition_result is None:
            try:
                with st.spinner("🍽️ Analyzing food and estimating nutrition..."):

                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    file_type = uploaded_file.type

                    nutrition_prompt = """
You are a professional nutrition analysis AI.

Analyze this food image and provide EXACTLY the following sections in plain text (NOT JSON):

## Detected Food Items
- List all visible food items.

## Estimated Calories
- Total calories in kcal.

## Protein
- Total protein in grams.

## Carbohydrates
- Total carbohydrates in grams.

## Fats
- Total fats in grams.

IMPORTANT:
- Do NOT return JSON.
- Do NOT use code blocks.
- Always provide numeric estimates.
- Always include all five sections above.
- Use markdown headings and bullet points only.
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

            except Exception as e:
                st.error(f"❌ Nutrition Analysis Error: {str(e)}")
                st.stop()

        if (
            st.session_state.recommendation_result is None
            or st.session_state.last_health_condition != health_condition
        ):
            try:
                with st.spinner("🩺 Generating personalized recommendations..."):

                    recommendation_prompt = f"""
You are a clinical nutritionist AI. A patient with {health_condition} has uploaded their meal photo.

Analyze this meal specifically for someone with {health_condition}. Do NOT give general advice.

Provide:

1. Health Score (out of 100) — scored specifically for {health_condition}
2. Is this meal suitable for {health_condition}? Explain WHY based on this condition's dietary needs.
3. Foods to Replace — specific to {health_condition}
4. Foods to Add — specific to {health_condition}
5. Personalized Recommendation for {health_condition}

IMPORTANT:
- Your entire response must be tailored to {health_condition}.
- Never say "General" in your response.
- Mention {health_condition} by name multiple times.
- Do NOT change the calorie or macronutrient estimates.
- Only interpret the meal according to the selected health condition.

Condition-specific guidance:
- For Prediabetes: focus on blood sugar control, glycemic index, added sugars, and fiber.
- For PCOS: focus on insulin resistance, inflammation, hormonal balance, and anti-inflammatory foods.
- For Gluten Sensitivity: identify gluten-containing ingredients and recommend gluten-free alternatives.
- For General: provide balanced healthy eating advice.

NUTRITIONAL ANALYSIS:
{st.session_state.nutrition_result}

Format the response clearly using markdown headings and bullet points.
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

    if st.session_state.nutrition_result:
        st.subheader("🍽️ Nutritional Analysis")
        st.markdown(st.session_state.nutrition_result)

    if st.session_state.recommendation_result:
        st.subheader(f"🩺 Recommendations for {health_condition}")
        st.markdown(st.session_state.recommendation_result)
        st.success("✅ Analysis Complete!")