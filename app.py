import os
import pandas as pd
import streamlit as st
from sarvamai import SarvamAI

st.set_page_config(
    page_title="TRACE | Student Safety",
    page_icon="🛡️",
    layout="wide",
)

# -------------------- Styling --------------------

st.markdown("""
<style>
.stApp { background-color: #f4f7fb; }
.hero {
    background: linear-gradient(120deg, #102a43, #176b87);
    color: white;
    padding: 30px;
    border-radius: 16px;
}
.hero h1 { color: white; font-size: 44px; }
.hero p { color: #e5f4ff; }
div[data-testid="stMetric"] {
    background: white;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid #dce5ee;
}
</style>
""", unsafe_allow_html=True)

# -------------------- Sarvam AI --------------------

def get_ai_response(question):
    api_key = os.getenv("SARVAM_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets.get("SARVAM_API_KEY", "")
        except Exception:
            api_key = ""

    if not api_key:
        return "Sarvam AI is not configured. Set your SARVAM_API_KEY to enable AI responses."

    try:
        client = SarvamAI(api_subscription_key=api_key)

        response = client.chat.completions(
            model="sarvam-105b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are TRACE, a supportive educational assistant "
                        "for students. Provide simple, non-judgmental advice "
                        "about drug-harm prevention, peer pressure, recognising "
                        "exploitation, and finding trusted help. Never encourage "
                        "drug use, criminal investigation, or confrontation. "
                        "Do not ask for personal information. You are not an "
                        "emergency service or medical professional. If someone "
                        "is in immediate danger in India, advise contacting "
                        "emergency number 112 and a trusted adult. For children "
                        "needing care or protection, Child Helpline 1098 may help."
                    ),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=600,
        )

        return response.choices[0].message.content

    except Exception:
        return (
            "The AI service is currently unavailable. Please try again later "
            "or contact a trusted adult or school counsellor."
        )


# -------------------- Fictional Demo Data --------------------

impact_data = pd.DataFrame({
    "Category": [
        "Drug-harm awareness",
        "Knowledge of support",
        "Peer-pressure confidence",
        "Exploitation awareness",
    ],
    "Before (%)": [45, 35, 40, 38],
    "After (%)": [68, 72, 65, 70],
})

# -------------------- Sidebar --------------------

st.sidebar.title("🛡️ TRACE")
st.sidebar.caption("Tracking Risks And Combating Exploitation")

page = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "Awareness Hub",
        "Sarvam AI Assistant",
        "Safe Support",
        "Impact Dashboard",
        "Demo Report",
        "About",
    ],
)

st.sidebar.info(
    "Student safety first. This prototype is not an emergency service."
)

# -------------------- Home --------------------

if page == "Home":
    st.markdown("""
    <div class="hero">
        <h1>TRACE</h1>
        <h3>Tracking Risks And Combating Exploitation</h3>
        <p>Awareness into action. Safer schools, stronger support.</p>
        <p><i>“It won't happen in one day, but it will happen one day.”</i></p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.subheader("Welcome to TRACE")

    st.write(
        "A student-centred initiative designed to prevent drug-related "
        "harm, help young people recognise exploitation, and make trusted "
        "support easier to access."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("01", "Learn")
    col1.write("Understand risks and make safer choices.")

    col2.metric("02", "Seek help")
    col2.write("Find trusted adults and appropriate services.")

    col3.metric("03", "Measure")
    col3.write("Evaluate a school pilot using privacy-conscious data.")

    st.divider()
    st.subheader("Our objectives")

    st.markdown("""
    - Improve awareness of drug-related risks.
    - Help students recognise manipulation and exploitation.
    - Encourage safe help-seeking.
    - Connect students with trusted adults and qualified professionals.
    - Evaluate programme effectiveness using aggregated data.
    """)

    st.warning(
        "If you are in immediate danger, seek a safe place if possible, "
        "contact a trusted adult, and call an appropriate emergency service. "
        "In India, dial 112 for emergencies."
    )

# -------------------- Awareness Hub --------------------

elif page == "Awareness Hub":
    st.title("📚 Awareness Hub")
    st.write("Learn, recognise risks, and practise safer decisions.")

    topic = st.selectbox(
        "Select a learning topic",
        [
            "Drug-related harm",
            "Peer pressure",
            "Recognising exploitation",
            "Online safety",
            "Asking for help",
        ],
    )

    content = {
        "Drug-related harm": [
            "Unknown substances can cause serious harm.",
            "Never feel obliged to accept a substance offered under pressure.",
            "Seek urgent medical help if someone becomes seriously unwell.",
        ],
        "Peer pressure": [
            "You have the right to say no.",
            "Use a clear response such as: 'No, I am not comfortable with that.'",
            "Move away safely and contact someone you trust.",
        ],
        "Recognising exploitation": [
            "Threats, coercion, debt, gifts, or secrecy can be used to manipulate people.",
            "You are not responsible for another person's exploitation of you.",
            "Do not confront or investigate suspected offenders yourself.",
        ],
        "Online safety": [
            "Avoid sharing private information with people you do not trust.",
            "Be cautious about threats, coercion, and demands for secrecy.",
            "Seek help if someone threatens or manipulates you online.",
        ],
        "Asking for help": [
            "Approach a trusted teacher, parent, guardian, or counsellor.",
            "Share only what you feel safe sharing.",
            "If one adult does not help, consider approaching another trusted adult.",
        ],
    }

    st.subheader(topic)
    for item in content[topic]:
        st.markdown(f"- {item}")

    st.divider()
    st.subheader("Scenario practice")

    scenario = st.selectbox(
        "What would you do?",
        [
            "Someone pressures me to try an unknown substance.",
            "Someone asks me to keep a frightening secret.",
            "A friend becomes seriously unwell after taking something.",
        ],
    )

    if st.button("Show suggested response", type="primary"):
        advice = {
            "Someone pressures me to try an unknown substance.":
                "Say no if possible, move away safely, and contact a trusted adult.",
            "Someone asks me to keep a frightening secret.":
                "You do not have to keep a secret that makes you feel unsafe. Tell a trusted adult.",
            "A friend becomes seriously unwell after taking something.":
                "Get emergency medical help immediately. Follow the emergency operator's instructions.",
        }
        st.success(advice[scenario])

# -------------------- Sarvam AI Assistant --------------------

elif page == "Sarvam AI Assistant":
    st.title("🤖 TRACE AI Support Assistant")

    st.write(
        "Ask general questions about prevention, peer pressure, "
        "exploitation awareness, or finding help."
    )

    st.info(
        "Do not enter names, addresses, school IDs, allegations, or "
        "other sensitive personal information. AI answers may be inaccurate."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a general safety question...")

    if question:
        st.session_state.messages.append({
            "role": "user",
            "content": question,
        })

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Getting guidance..."):
                answer = get_ai_response(question)
            st.markdown(answer)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
        })

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

# -------------------- Safe Support --------------------

elif page == "Safe Support":
    st.title("🤝 Trusted Support Pathways")

    st.write(
        "You do not have to handle an unsafe situation alone. "
        "Reach out to a trusted adult or qualified professional."
    )

    st.subheader("Who can help?")
    st.markdown("""
    - A trusted parent, guardian, or family member
    - A teacher or school safeguarding staff member
    - A school counsellor
    - A qualified healthcare professional
    - Appropriate child-protection or law-enforcement services
    """)

    st.subheader("Important numbers in India")
    st.markdown("""
    - **112:** Emergency response number.
    - **1098:** Child Helpline for children needing care, protection, or assistance.
    """)

    st.warning(
        "This prototype is not monitored. Using TRACE does not alert "
        "a teacher, counsellor, police officer, or emergency responder."
    )

    st.subheader("Example help request")

    st.code(
        "I am concerned about a situation affecting my safety or "
        "someone else's wellbeing. Could I speak with you privately "
        "about how to get help?"
    )

# -------------------- Impact Dashboard --------------------

elif page == "Impact Dashboard":
    st.title("📊 Impact Dashboard")

    st.warning(
        "DEMONSTRATION DATA ONLY. These figures are fictional, not real "
        "student measurements or official Delhi statistics."
    )

    col1, col2, col3 = st.columns(3)

    before_avg = impact_data["Before (%)"].mean()
    after_avg = impact_data["After (%)"].mean()

    col1.metric("Topics measured", len(impact_data))
    col2.metric("Illustrative baseline", f"{before_avg:.1f}%")
    col3.metric(
        "Illustrative follow-up",
        f"{after_avg:.1f}%",
        delta=f"{after_avg - before_avg:.1f} percentage points",
    )

    st.subheader("Before-and-after comparison")
    st.bar_chart(impact_data.set_index("Category"))

    st.subheader("Demo dataset")
    st.dataframe(impact_data, use_container_width=True, hide_index=True)

    st.subheader("Potential pilot evaluation measures")
    st.markdown("""
    - Changes in prevention knowledge.
    - Awareness of trusted support channels.
    - Student feedback on educational activities.
    - Accessibility and safeguarding quality.
    """)

    st.caption(
        "Improved awareness does not by itself prove that trafficking "
        "or exploitation has decreased."
    )

    st.download_button(
        "Download demo data as CSV",
        data=impact_data.to_csv(index=False).encode("utf-8"),
        file_name="trace_demo_impact.csv",
        mime="text/csv",
    )

# -------------------- Demo Report --------------------

elif page == "Demo Report":
    st.title("📝 Safe Reporting Workflow — Demo")

    st.warning(
        "Demonstration only. Do not enter real incidents, names, "
        "accusations, contact details, or identifying information. "
        "Nothing entered here is saved or sent."
    )

    st.write(
        "A real reporting service must be approved by the school, "
        "managed by authorised adults, and supported by clear privacy "
        "and safeguarding procedures."
    )

    with st.form("demo_report_form"):
        category = st.selectbox(
            "Choose a fictional demo category",
            [
                "General safety concern",
                "Peer pressure",
                "Possible exploitation",
                "Request for support information",
            ],
        )

        confirmed = st.checkbox(
            "I understand this is a demonstration, not a real reporting service."
        )

        submitted = st.form_submit_button("Preview workflow")

    if submitted:
        if confirmed:
            st.success(
                f"Demo workflow previewed: {category}. "
                "No report was saved or transmitted."
            )
            st.write(
                "In a properly approved school system, an authorised "
                "safeguarding professional would follow established "
                "procedures to review a genuine concern."
            )
        else:
            st.error("Please confirm that you understand this is a demo.")

# -------------------- About --------------------

elif page == "About":
    st.title("🛡️ About TRACE")

    st.markdown("""
    **TRACE** means Tracking Risks And Combating Exploitation.

    ### Our mission
    Turn awareness into action by helping young people recognise risks
    and find appropriate support.

    ### Key features
    - Prevention education.
    - Sarvam AI-powered general guidance.
    - Trusted support information.
    - A fictional impact dashboard.
    - A demonstration of a proposed school referral workflow.

    ### Implementation roadmap
    1. Consult school staff and safeguarding professionals.
    2. Test the prototype with fictional data.
    3. Review accessibility, privacy, and safety.
    4. Obtain appropriate approval before any real-world pilot.
    5. Evaluate outcomes before considering expansion.

    ### Privacy notice
    This prototype does not implement a live reporting system.
    AI questions are sent to Sarvam AI when the API key is configured.
    Do not share personal or sensitive information with the AI assistant.

    A production version would require secure infrastructure, appropriate
    consent, data minimisation, authorised reviewers, and approved
    child-safeguarding and escalation procedures.
    """)

    st.divider()
    st.markdown("### TRACE")
    st.write("Awareness into action. One step at a time.")