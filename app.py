"""TRACE — student safety education prototype.

This demonstration does not accept incident reports or provide emergency response.
AI questions are sent to Sarvam AI only when a user submits a chat message.
"""

import os
import re
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


# Load the local .env when running on a computer. Community Cloud uses st.secrets.
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

st.set_page_config(
    page_title="TRACE | Student Safety",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"


def get_setting(name: str, default: str = "") -> str:
    """Read Streamlit Cloud secrets first, then local environment variables."""
    try:
        from_cloud = st.secrets.get(name, "")
        if from_cloud and str(from_cloud).strip():
            return str(from_cloud).strip()
    except (Exception,):  # No secrets.toml is normal on a local installation.
        pass
    return os.getenv(name, default).strip()


def scrub_obvious_contact_details(text: str) -> str:
    """Basic precaution, not a guarantee of anonymity or de-identification."""
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email removed]", text)
    text = re.sub(r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)", "[phone removed]", text)
    return text


SYSTEM_GUIDANCE = """You are TRACE, a supportive, age-appropriate educational assistant
for school students in Delhi, India. Your job is drug-harm prevention, understanding
peer pressure and exploitation risks, and safely getting help. Keep answers short,
practical and non-judgmental. Follow the student's language preference. Explain
that students should never investigate suspects, confront potential traffickers,
share accusations publicly, or put themselves in danger. Do not request names,
phone numbers, addresses, school identifiers, or allegations about individuals.
Do not provide instructions for buying drugs, making drugs, hiding drug use,
evading law enforcement, or investigating criminal activity. Encourage speaking
to trusted adults, the designated school safeguarding lead, or a counsellor.
If someone might be in immediate danger, tell them to contact local emergency
services (112 in India) and a trusted adult now. You are not an emergency or
formal reporting service. Avoid diagnosing medical or mental-health conditions.
If unsure, say so and suggest appropriate qualified support.
"""


def sarvam_reply(api_key: str, model: str, history: list, language: str) -> str:
    """Call Sarvam's Chat Completions API without relying on SDK versions."""
    preference = {
        "English": "Reply in plain English.",
        "हिन्दी": "Reply in simple Hindi (Devanagari).",
        "Auto": "Reply in the same language as the user's most recent message.",
    }[language]

    messages = [{"role": "system", "content": SYSTEM_GUIDANCE + "\n" + preference}]
    messages.extend(history[-8:])

    try:
        response = requests.post(
            SARVAM_CHAT_URL,
            headers={
                "api-subscription-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 450,
            },
            timeout=35,
        )
    except requests.exceptions.Timeout:
        return "Sarvam AI took too long to respond. Please try again shortly."
    except requests.exceptions.RequestException:
        return "Could not reach Sarvam AI. Check the internet connection or try again."

    if not response.ok:
        code = response.status_code
        if code in (401, 403):
            return "Sarvam rejected the API key (401/403). Check the key in Streamlit Cloud → App settings → Secrets, and check that the key is active."
        if code == 429:
            return "Sarvam AI is rate-limiting requests (429). Try again later or check your account limits."
        if code == 402:
            return "Sarvam AI indicates a billing/credit issue (402). Check your Sarvam account."
        if code in (400, 404):
            return (f"Sarvam returned HTTP {code}. Check that the configured model "
                    f"'{model}' is available to your Sarvam account, and that the API endpoint is current.")
        return f"Sarvam AI returned HTTP {code}. Check the Sarvam service and account settings."

    try:
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, str) and content.strip():
            return content.strip()
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return "Sarvam AI responded, but its message format was unexpected. Check the provider's current API format."


st.markdown(
    """
    <style>
      .trace-banner { background: linear-gradient(120deg,#102c45,#15637b);
        padding: 1.6rem 2rem; border-radius: 18px; color: white; margin-bottom: 1rem; }
      .trace-banner h1 { color: white; margin: 0; letter-spacing: 0.04em; }
      .trace-banner p { color: #e2f3f7; margin: 0.5rem 0 0; }
      .small-note { color: #54677a; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

api_key = get_setting("SARVAM_API_KEY") or get_setting("SARVAM_API_SUBSCRIPTION_KEY")
model = get_setting("SARVAM_MODEL", "sarvam-m")

with st.sidebar:
    st.title("🛡️ TRACE")
    st.caption("Tracking Risks And Combating Exploitation")
    st.divider()
    st.markdown("**Prototype status**")
    if api_key:
        st.success("Sarvam API key loaded ✅")
    else:
        st.error("Sarvam API key not found")
        st.caption("On Community Cloud, add SARVAM_API_KEY in App settings → Secrets.")
    st.caption(f"AI model: `{model}`")
    st.divider()
    st.info("Student-led prototype. No live reporting system, case management, or emergency monitoring.")
    st.caption("If someone is in immediate danger in India, contact 112 and a trusted adult.")

st.markdown(
    """
    <div class="trace-banner">
      <h1>TRACE</h1>
      <p><strong>Tracking Risks And Combating Exploitation</strong></p>
      <p>Turning awareness into action — safer choices, trusted adults, and clear support pathways.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("GAME CHANGERS · SOCIAL IMPACT INNOVATION · DEMONSTRATION PROTOTYPE")

home, awareness, chatbot, help_tab, impact = st.tabs(
    ["🏠 Home", "📚 Awareness", "🤖 Ask TRACE AI", "🤝 Get Help Safely", "📊 Demo Impact"]
)

with home:
    st.subheader("Recognise risks. Reach support. Stay safe.")
    st.write(
        "TRACE is a proposed school-centred prevention initiative for Delhi. "
        "It brings together practical safety education, guidance for seeking help, "
        "and responsible referrals through approved school procedures."
    )
    a, b, c = st.columns(3)
    with a:
        st.markdown("#### 🧠 Learn")
        st.write("Understand peer pressure, manipulation, and safer decisions through scenarios.")
    with b:
        st.markdown("#### 🤝 Seek support")
        st.write("Know when and how to approach a teacher, counsellor, or trusted adult.")
    with c:
        st.markdown("#### 📈 Measure progress")
        st.write("See how awareness could be evaluated without identifying students.")
    st.warning(
        "This prototype does not receive confidential reports, alert police, or "
        "monitor threats. Do not submit real allegations or personal details here."
    )
    st.markdown("*“It won't happen in one day, but it will happen one day.”*")

with awareness:
    st.subheader("Interactive awareness hub")
    with st.expander("How can I recognise unsafe pressure?", expanded=True):
        st.write(
            "Watch for requests to keep risky secrets, carry unknown packages, "
            "go to isolated locations, or do something that makes you uncomfortable. "
            "You have the right to say no, leave the situation, and ask for help."
        )
    with st.expander("What if a friend may need help?"):
        st.write(
            "Listen without judgement. Encourage them to speak with a school "
            "counsellor, parent, safeguarding teacher, or qualified healthcare professional. "
            "Do not attempt to investigate, punish, or publicly expose anyone."
        )
    with st.expander("What if someone asks me to keep a dangerous secret?"):
        st.write(
            "Your safety matters more than a promise of secrecy. If there is a "
            "threat, coercion, or exploitation, speak privately to a trusted adult."
        )

    st.markdown("#### Mini safety quiz")
    questions = [
        {
            "q": "Someone asks you to carry a sealed package for a stranger. What is safest?",
            "options": ["Carry it as a favour", "Refuse, leave, and tell a trusted adult", "Post an accusation online"],
            "answer": 1,
            "why": "Do not handle unknown packages or investigate. Seek help from a trusted adult.",
        },
        {
            "q": "A classmate says they are being pressured to do something unsafe. You should…",
            "options": ["Listen and help them reach a trusted adult", "Confront the person yourself", "Spread the story"],
            "answer": 0,
            "why": "Support a safe referral. Avoid confrontation, rumours, and public allegations.",
        },
        {
            "q": "Someone is in immediate danger. Which response is appropriate?",
            "options": ["Wait for the app to reply", "Investigate on your own", "Contact emergency services and a trusted adult"],
            "answer": 2,
            "why": "TRACE is not an emergency service. In India, call 112 for immediate danger.",
        },
    ]
    for i, item in enumerate(questions):
        st.markdown(f"**{i + 1}. {item['q']}**")
        choice = st.radio("Choose an answer", item["options"], key=f"quiz_{i}", label_visibility="collapsed")
        if st.button("Check answer", key=f"check_{i}"):
            if item["options"].index(choice) == item["answer"]:
                st.success("Correct! " + item["why"])
            else:
                st.info("Safer choice: " + item["options"][item["answer"]] + ". " + item["why"])

with chatbot:
    st.subheader("Ask TRACE AI")
    st.write("Ask general questions about pressure, prevention, staying safe, or seeking help.")
    st.warning(
        "Do not type names, contact details, school addresses, allegations, or "
        "details of an actual incident. Messages are sent to the Sarvam AI service "
        "for processing. This is educational AI, not a private reporting or emergency channel."
    )
    language = st.selectbox("Response language", ["Auto", "English", "हिन्दी"])
    if not api_key:
        st.error(
            "AI is unavailable because SARVAM_API_KEY is missing. "
            "Add it to Streamlit Community Cloud → your app → Settings → Secrets."
        )
    if "trace_history" not in st.session_state:
        st.session_state.trace_history = []

    for entry in st.session_state.trace_history:
        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])

    if st.button("Clear chat history"):
        st.session_state.trace_history = []
        st.rerun()

    question = st.chat_input(
        "Example: How do I say no to peer pressure?",
        disabled=not bool(api_key),
        max_chars=700,
    )
    if question:
        safe_question = scrub_obvious_contact_details(question.strip())
        st.session_state.trace_history.append({"role": "user", "content": safe_question})
        with st.spinner("TRACE AI is responding…"):
            answer = sarvam_reply(api_key, model, st.session_state.trace_history, language)
        st.session_state.trace_history.append({"role": "assistant", "content": answer})
        st.rerun()

with help_tab:
    st.subheader("Get help safely")
    st.write(
        "TRACE does not accept or store real incident reports. "
        "Use your school's approved safeguarding process to share a concern privately."
    )
    st.markdown("**Suggested safer steps**")
    st.write("1. Move somewhere safe. Do not confront or follow anyone.")
    st.write("2. Contact a trusted parent/guardian, teacher, or designated safeguarding staff member.")
    st.write("3. Share your concern directly through approved school or professional channels.")
    st.write("4. If there is immediate danger, call **112 in India** and seek adult help.")
    st.info(
        "For a school pilot, reporting and referral processes must be approved, "
        "staffed by trained adults, and designed with clear privacy and escalation rules."
    )

with impact:
    st.subheader("Illustrative impact dashboard")
    st.warning("All numbers below are fictional sample data — not results from a real school pilot.")
    x, y, z = st.columns(3)
    x.metric("Demo student participants", "120")
    y.metric("Demo completion rate", "85%")
    z.metric("Demo help-channel awareness", "78%")
    sample = pd.DataFrame(
        {
            "Before (demo)": [42, 35, 30],
            "After (demo)": [84, 78, 74],
        },
        index=["Recognising pressure", "Knowing help channels", "Confidence asking for help"],
    )
    st.bar_chart(sample)
    st.caption(
        "A real evaluation would use approved, anonymous aggregate measures "
        "and assess safeguarding quality, not collect student identities in this dashboard."
    )

st.divider()
st.caption("TRACE · Game Changers · Prototype for awareness and responsible referral · Not an emergency service")
