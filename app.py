"""TRACE — student safety awareness and private report-draft prototype.

This demonstration provides no monitored incident intake or emergency response.
Report drafts stay in the active session until voluntarily downloaded; they are
not submitted to a school, police, or any third party by this application.
AI questions are sent to Sarvam AI only when a user submits a chat message.
"""

import io
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageOps, UnidentifiedImageError

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
# Sarvam informed TRACE that sarvam-m is deprecated.
# Keep this default aligned with a model named in Sarvam's API response.
DEFAULT_SARVAM_MODEL = "sarvam-105b-conversations"
DEPRECATED_SARVAM_MODELS = {"sarvam-m"}


def get_setting(name: str, default: str = "") -> str:
    """Read Streamlit Cloud secrets first, then local environment variables."""
    try:
        from_cloud = st.secrets.get(name, "")
        if from_cloud and str(from_cloud).strip():
            return str(from_cloud).strip()
    except (Exception,):  # No secrets.toml is normal on a local installation.
        pass
    return os.getenv(name, default).strip()


def get_sarvam_model() -> tuple[str, bool]:
    """Resolve Sarvam model, including stale secrets from older deployments.

    Returns (resolved_model, replaced_deprecated_model). A stale SARVAM_MODEL
    in Streamlit Secrets or .env must not force the discontinued sarvam-m model.
    """
    configured = get_setting("SARVAM_MODEL", DEFAULT_SARVAM_MODEL).strip()
    if not configured or configured.lower() in DEPRECATED_SARVAM_MODELS:
        return DEFAULT_SARVAM_MODEL, bool(configured)
    return configured, False


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


def safe_api_error(response: requests.Response, api_key: str) -> str:
    """Read a short diagnostic from Sarvam without showing private credentials."""
    try:
        payload = response.json()
        detail = payload.get("error", payload) if isinstance(payload, dict) else payload
        if isinstance(detail, dict):
            reason = str(detail.get("message") or detail.get("detail") or detail.get("code") or detail)
        else:
            reason = str(detail)
    except (ValueError, TypeError):
        reason = "The provider did not return a readable error message."

    # This is a basic defensive filter, not a universal private-data scrubber.
    reason = reason.replace(api_key, "[secret removed]")
    reason = re.sub(r"\bsk[_-][A-Za-z0-9_-]{8,}\b", "[secret removed]", reason)
    reason = scrub_obvious_contact_details(reason)
    return reason[:280]


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
            # Start with the minimum required fields. Some Sarvam models or API
            # versions reject optional sampling/token parameters with HTTP 400.
            json={
                "model": model,
                "messages": messages,
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
        if code in (400, 404, 422):
            reason = safe_api_error(response, api_key)
            # No key or message history is logged; admins can use Cloud logs.
            print(f"TRACE Sarvam HTTP {code}: {reason}")
            return (
                f"Sarvam returned HTTP {code} for model '{model}'. "
                f"Provider reason: {reason} "
                "If the provider rejects this model, try 'sarvam-105b' in "
                "Streamlit Secrets. If it mentions a request field, check the "
                "provider's current chat API requirements."
            )
        return f"Sarvam AI returned HTTP {code}. Check the Sarvam service and account settings."

    try:
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, str) and content.strip():
            return content.strip()
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return "Sarvam AI responded, but its message format was unexpected. Check the provider's current API format."




# Call links open a phone dialer on supported devices. The app does not
# initiate a call or monitor emergencies itself.
EMERGENCY_CALL_HTML = """
<a href="tel:112" style="display:inline-block;background:#c51f37;color:white;
text-decoration:none;font-weight:750;padding:0.85rem 1.3rem;
border-radius:0.65rem;font-size:1.03rem;" aria-label="Call 112 emergency services">
📞 Call 112 — Emergency (India)</a>
"""


SAFETY_QUESTIONS = [
    {
        "q": "A friend pressures you to try an unknown substance. What is safest?",
        "options": ["Try it once to avoid conflict", "Say no and move away",
                    "Agree to keep the friendship", "Ask another student to try it first"],
        "correct": 1,
        "why": "You can refuse, leave, and ask a trusted adult for help if needed.",
    },
    {
        "q": "Someone asks you to deliver a sealed packet to a stranger. What should you do?",
        "options": ["Deliver it quickly", "Open it to investigate",
                    "Refuse and tell a trusted adult", "Photograph the stranger secretly"],
        "correct": 2,
        "why": "Do not carry unknown items or investigate suspected activity yourself.",
    },
    {
        "q": "Your friend says an older person is threatening them. What should you do?",
        "options": ["Help them speak to a trusted adult", "Confront the person",
                    "Share the story online", "Promise to keep it secret forever"],
        "correct": 0,
        "why": "Offer calm support and help them reach an adult or safeguarding professional.",
    },
    {
        "q": "Someone online asks for your school address and a private meeting. What is safest?",
        "options": ["Share the address", "Meet them with another student",
                    "Send a photo of your ID", "Do not share details; tell a trusted adult"],
        "correct": 3,
        "why": "Protect your identity and location; seek help with concerning contact.",
    },
    {
        "q": "You hear a rumour accusing another student of selling drugs. What should you do?",
        "options": ["Post the name publicly", "Avoid sharing rumours; privately tell safeguarding staff if worried",
                    "Follow the student", "Question classmates publicly"],
        "correct": 1,
        "why": "Public accusations can cause harm. Do not investigate or spread rumours.",
    },
    {
        "q": "A person appears to be in immediate physical danger. What should you do?",
        "options": ["Wait for TRACE AI", "Film the incident",
                    "Call 112 in India and seek a trusted adult", "Ask an online group"],
        "correct": 2,
        "why": "Emergency services, not TRACE, handle immediate danger.",
    },
    {
        "q": "A classmate wants to share their live location for safety. What matters most?",
        "options": ["They choose a trusted recipient and consent", "Everyone can see it",
                    "The app sends it automatically", "They post it publicly"],
        "correct": 0,
        "why": "Location sharing should be voluntary, limited, and directed to trusted contacts.",
    },
    {
        "q": "You notice a concerning situation. What is the safest way to take a picture?",
        "options": ["Get closer to capture faces", "Confront the people in the scene",
                    "Upload the photo publicly", "Only take one if already safe; never put yourself at risk"],
        "correct": 3,
        "why": "Your safety matters more than evidence. Do not photograph in danger.",
    },
    {
        "q": "Which person is an appropriate first contact about a school safety concern?",
        "options": ["An unknown social-media follower", "A designated safeguarding teacher or counsellor",
                    "A stranger offering advice", "A public comments section"],
        "correct": 1,
        "why": "Use known, appropriate school and family support pathways.",
    },
    {
        "q": "You are unsure whether an AI chatbot's safety advice is correct. What should you do?",
        "options": ["Rely on the AI alone", "Forward it as verified fact",
                    "Check with a trusted adult or qualified professional", "Ignore immediate danger"],
        "correct": 2,
        "why": "AI can make mistakes and cannot replace trained people or emergency help.",
    },
]


def valid_map_link(value: str) -> bool:
    """Allow known map-sharing hosts. The URL is never fetched server-side."""
    try:
        url = urlsplit(value.strip())
        host = (url.hostname or "").lower()
        return (
            url.scheme == "https"
            and (
                (host in {"www.google.com", "google.com", "maps.google.com"} and url.path.startswith("/maps"))
                or host == "maps.app.goo.gl"
                or (host == "maps.apple.com" and bool(url.query))
                or (host == "goo.gl" and url.path.startswith("/maps/"))
            )
        )
    except ValueError:
        return False


def make_private_report(category: str, note: str, requested_support: str, photo) -> bytes:
    """Create a local-download ZIP. No case is created or sent anywhere."""
    output = io.BytesIO()
    report = (
        "TRACE — PRIVATE CONCERN DRAFT (NOT SUBMITTED)\n"
        "For a trusted adult / approved safeguarding professional only.\n"
        "The TRACE prototype has NOT notified anyone or created a case.\n\n"
        f"Created (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}\n"
        f"General context: {category}\n"
        f"Support requested: {requested_support}\n\n"
        f"What I want to tell a trusted adult:\n{note.strip() or '(No written description)'}\n\n"
        "If anyone is in immediate danger in India, call 112.\n"
        "Do not publish allegations or investigate anyone yourself.\n"
    )
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("TRACE_private_concern.txt", report)
        if photo is not None:
            if photo.size > 5 * 1024 * 1024:
                raise ValueError("Photo is larger than 5 MB. Please choose a smaller file.")
            try:
                with Image.open(photo) as img:
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((1600, 1600))
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    clean_photo = io.BytesIO()
                    # Re-encode without EXIF/geolocation metadata. Image contents
                    # such as faces or identifiers are NOT automatically blurred.
                    img.save(clean_photo, format="JPEG", quality=86)
                    bundle.writestr("attached_photo_without_exif.jpg", clean_photo.getvalue())
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                raise ValueError("This image could not be processed. Use a valid JPG/PNG/WebP image.") from exc
    return output.getvalue()

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
model, outdated_model_overridden = get_sarvam_model()

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
    if outdated_model_overridden:
        st.info(
            "The old model 'sarvam-m' was detected in your settings and "
            "automatically changed to 'sarvam-105b-conversations'. "
            "Update SARVAM_MODEL in Streamlit Secrets when convenient."
        )
    st.divider()
    st.info("Student-led prototype. No live reporting, case management, or emergency monitoring.")
    st.markdown(EMERGENCY_CALL_HTML, unsafe_allow_html=True)
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

home, awareness, chatbot, location_tab, draft_tab, help_tab, impact = st.tabs(
    ["🏠 Home", "🧠 Safety Quiz", "🤖 Ask TRACE AI", "📍 Share Location",
     "📷 Concern Draft", "🆘 Get Help", "📊 Demo Impact"]
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
        "This prototype does not alert police, submit reports, or monitor threats. "
        "The concern-draft tool only prepares a file you can choose to share with a trusted adult."
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

    st.markdown("#### Test your safety skills — 10 MCQs + 1 fill in the blank")
    st.caption("Answers stay in this browser session. No names, addresses, or incident details needed.")
    with st.form("trace_11_question_safety_quiz"):
        answers = []
        for i, item in enumerate(SAFETY_QUESTIONS, 1):
            st.markdown(f"**Q{i}. {item['q']}**")
            answer = st.radio(
                f"Question {i}", item["options"], index=None,
                key=f"safety_mcq_{i}", label_visibility="collapsed"
            )
            answers.append(answer)
        st.markdown("**Q11. Fill in the blank:** If you feel unsafe, ask a trusted ______ for help.")
        blank_answer = st.text_input("Your answer for Q11", placeholder="One word", max_chars=45)
        submitted = st.form_submit_button("Check all 11 answers", type="primary")
    if submitted:
        score = sum(
            a == q["options"][q["correct"]]
            for a, q in zip(answers, SAFETY_QUESTIONS)
        )
        blank_correct = blank_answer.strip().lower() in {"adult", "grown-up", "grown up"}
        score += int(blank_correct)
        st.success(f"Your score: {score}/11")
        if score == 11:
            st.balloons()
        for i, (answer, q) in enumerate(zip(answers, SAFETY_QUESTIONS), 1):
            is_right = answer == q["options"][q["correct"]]
            with st.expander(f"Q{i} — {'✅ Correct' if is_right else '📘 Review'}"):
                st.write(f"Safer answer: **{q['options'][q['correct']]}**")
                st.caption(q["why"])
        st.info("Q11: " + ("Correct — adult." if blank_correct else "The expected word is **adult** (or grown-up)."))

with chatbot:
    st.subheader("Ask TRACE AI")
    st.write("Ask general questions about pressure, prevention, staying safe, or seeking help.")
    st.caption("Connection uses the Sarvam chat API. If you see HTTP 400, the app now shows Sarvam's specific error reason, with basic redaction.")
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

with location_tab:
    st.subheader("Share your location with a trusted contact")
    st.info(
        "Location sharing is always optional. TRACE cannot see your device's live "
        "location and does not automatically share it. You choose the recipient "
        "and confirm the share in Google Maps, WhatsApp, or your phone."
    )
    st.markdown("**To share live location with a trusted contact:**")
    st.write(
        "1. Open Google Maps on your phone.\n"
        "2. Tap your profile picture → **Location sharing** → **New share**.\n"
        "3. Choose how long to share and select a trusted contact.\n"
        "4. Stop sharing in Google Maps when you no longer need it."
    )
    st.link_button("📍 Open Google Maps", "https://www.google.com/maps")
    st.markdown("**Or share a one-time location link on WhatsApp:**")
    st.caption("In Maps, select your location and use Share → Copy link; paste only that link below.")
    map_url = st.text_input(
        "Google Maps / Apple Maps link", key="trace_map_link",
        placeholder="https://maps.app.goo.gl/…", max_chars=700
    )
    if map_url.strip():
        if valid_map_link(map_url):
            share_message = (
                "I'm sharing this location with you by choice. "
                "Please check in with me: " + map_url.strip()
            )
            st.link_button(
                "🟢 Choose a WhatsApp contact to share with",
                "https://wa.me/?text=" + quote(share_message, safe="")
            )
            st.caption("You will choose the contact and send the message yourself in WhatsApp.")
        else:
            st.warning("Please paste a valid HTTPS Google Maps or Apple Maps sharing link.")
    st.warning("Do not post your location publicly. If you are in immediate danger, call 112.")

with draft_tab:
    st.subheader("Prepare a private concern note")
    st.warning(
        "This is NOT a live reporting service. Clicking 'Prepare draft' does not "
        "send anything to teachers, authorities, or police. Share the downloaded "
        "draft only with an appropriate trusted adult or approved safeguarding contact."
    )
    st.write(
        "If it is safe, you may attach a photo already on your device. "
        "Never approach, follow, confront, or secretly photograph someone to gather evidence. "
        "Avoid images of identifiable minors, faces, or personal documents."
    )
    with st.form("private_concern_form"):
        category = st.selectbox(
            "General area of concern (no exact address)",
            ["Around school (general)", "Online or social media", "Public place (general)", "Other / not sure"]
        )
        requested_support = st.selectbox(
            "What support would you like?",
            ["Talk privately to a trusted adult", "Speak to a school counsellor", "Ask about an approved reporting pathway"]
        )
        note = st.text_area(
            "Describe what you want to tell a trusted adult (optional)",
            placeholder="Write only a general concern. No names, accusations, exact addresses, or contact details.",
            max_chars=500, height=120
        )
        photo = st.file_uploader(
            "Add a photo already taken safely (optional; JPG/PNG/WebP, max 5 MB)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False
        )
        st.checkbox(
            "I understand TRACE does not send this report and I must share it myself with a trusted adult.",
            key="trace_report_ack"
        )
        create_draft = st.form_submit_button("📷 Prepare private report (NOT sent)", type="primary")
    if create_draft:
        if not st.session_state.get("trace_report_ack", False):
            st.error("Please confirm that you understand the report is not being sent.")
        else:
            try:
                st.session_state["trace_report_zip"] = make_private_report(category, note, requested_support, photo)
                st.success("Private draft prepared. No report has been sent.")
            except ValueError as error:
                st.session_state.pop("trace_report_zip", None)
                st.error(str(error))
    if st.session_state.get("trace_report_zip"):
        st.download_button(
            "⬇️ Download draft + optional photo (ZIP)",
            st.session_state["trace_report_zip"],
            file_name="TRACE_private_concern_draft.zip",
            mime="application/zip",
            type="primary"
        )
        st.caption(
            "The attached photo is re-encoded to remove embedded EXIF metadata, but "
            "visible faces or identifying details remain. Review it before sharing. "
            "The file is generated in your session, not saved to a TRACE database."
        )
        if st.button("Delete prepared draft from this session"):
            st.session_state.pop("trace_report_zip", None)
            st.rerun()
    st.info("If a school later adopts a reporting workflow, it needs permission, trained reviewers, and a secure case process first.")

with help_tab:
    st.subheader("Immediate help and trusted support")
    st.markdown(EMERGENCY_CALL_HTML, unsafe_allow_html=True)
    st.caption("On a phone, this opens your dialer; you must confirm the call. On a computer, dial 112 from a phone.")
    st.write(
        "If you feel unsafe: move to a safe place, contact a trusted adult, "
        "and use your school's approved safeguarding process. Do not confront suspects."
    )
    st.write(
        "**Emergency:** For immediate danger in India, dial **112**. "
        "TRACE is not monitored and cannot dispatch emergency help."
    )
    st.info(
        "For a school pilot, any reporting and referral process must be approved, "
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
st.caption("TRACE · Game Changers · Education, optional sharing and private drafts · Not a reporting or emergency service")
