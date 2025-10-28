import streamlit as st
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from notifications import create_notification

# Database file paths
HELP_REQUESTS_FILE = "help_requests.json"
KNOWLEDGE_BASE_FILE = "knowledge_base.json"

# Initialize session state
if 'refresh_trigger' not in st.session_state:
    st.session_state.refresh_trigger = 0

def load_json_file(filepath, default=None):
    """Load JSON file with error handling"""
    try:
        file_path = Path(filepath)
        if file_path.exists():
            # Check if file is empty
            if file_path.stat().st_size == 0:
                print(f"ℹ️ {filepath} is empty, using default value")
                return default if default is not None else {}
            
            with open(filepath, 'r') as f:
                content = f.read().strip()
                # Double-check content isn't empty string
                if not content:
                    return default if default is not None else {}
                return json.loads(content)
    except json.JSONDecodeError as e:
        st.warning(f"JSON decode error in {filepath}: {e}. Using default value.")
        return default if default is not None else {}
    except Exception as e:
        st.error(f"Error loading {filepath}: {e}")
    return default if default is not None else {}

def save_json_file(filepath, data):
    """Save JSON file with error handling"""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving {filepath}: {e}")
        return False

def get_help_requests():
    """Get all help requests"""
    return load_json_file(HELP_REQUESTS_FILE, default=[])

def save_help_requests(requests):
    """Save help requests"""
    return save_json_file(HELP_REQUESTS_FILE, requests)

def get_knowledge_base():
    """Get knowledge base"""
    return load_json_file(KNOWLEDGE_BASE_FILE, default={})

def save_knowledge_base(kb):
    """Save knowledge base"""
    return save_json_file(KNOWLEDGE_BASE_FILE, kb)

def create_help_request(caller_id, question, audio_transcript=None):
    """Create a new help request"""
    requests = get_help_requests()
    
    timeout_time = datetime.now() + timedelta(hours=2)
    
    request = {
        "id": f"REQ_{int(time.time())}_{len(requests)}",
        "caller_id": caller_id,
        "question": question,
        "audio_transcript": audio_transcript,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
        "supervisor_answer": None,
        "timeout_at": timeout_time.isoformat()
    }
    
    requests.append(request)
    save_help_requests(requests)
    
    # Log to console (simulated supervisor notification)
    print(f"🚨 SUPERVISOR ALERT: New help request from {caller_id}")
    print(f"   Question: {question}")
    print(f"   Request ID: {request['id']}")
    
    return request

def resolve_request(request_id, answer, add_to_kb=True):
    """Resolve a help request, create notification, and optionally add to knowledge base"""
    requests = get_help_requests()
    
    for req in requests:
        if req['id'] == request_id:
            req['status'] = 'resolved'
            req['resolved_at'] = datetime.now().isoformat()
            req['supervisor_answer'] = answer
            
            # CREATE NOTIFICATION FOR AGENT TO FOLLOW UP
            notification = create_notification(
                request_id=request_id,
                caller_id=req['caller_id'],
                answer=answer
            )
            
            print(f"📢 NOTIFICATION CREATED: {notification['id']}")
            print(f"   Agent will follow up with caller: {req['caller_id']}")
            print(f"   Answer: {answer}")
            
            # Update knowledge base
            if add_to_kb and req['question']:
                kb = get_knowledge_base()
                kb[req['question'].lower().strip()] = answer
                save_knowledge_base(kb)
                print(f"📚 KNOWLEDGE BASE UPDATED: Added answer for '{req['question']}'")
            
            save_help_requests(requests)
            return True
    
    return False

def mark_unresolved(request_id, reason="Timeout"):
    """Mark a request as unresolved"""
    requests = get_help_requests()
    
    for req in requests:
        if req['id'] == request_id:
            req['status'] = 'unresolved'
            req['resolved_at'] = datetime.now().isoformat()
            req['supervisor_answer'] = f"[Unresolved: {reason}]"
            save_help_requests(requests)
            
            print(f"⏰ REQUEST TIMEOUT: {request_id} marked as unresolved")
            return True
    
    return False

# Streamlit UI
st.set_page_config(
    page_title="AI Supervisor Dashboard",
    page_icon="🎧",
    layout="wide"
)

st.title("🎧 AI Receptionist Supervisor Dashboard")
st.markdown("*Human-in-the-Loop System for Frontdesk AI*")
st.info("💡 When you resolve a request, the AI agent will automatically follow up with the caller within 5 seconds!")

# Sidebar
with st.sidebar:
    st.header("📊 Quick Stats")
    
    requests = get_help_requests()
    pending_count = len([r for r in requests if r['status'] == 'pending'])
    resolved_count = len([r for r in requests if r['status'] == 'resolved'])
    unresolved_count = len([r for r in requests if r['status'] == 'unresolved'])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pending", pending_count)
    with col2:
        st.metric("Resolved", resolved_count)
    with col3:
        st.metric("Unresolved", unresolved_count)
    
    st.divider()
    
    # Check notification status
    from notifications import get_pending_notifications
    pending_notifications = get_pending_notifications()
    
    st.header("📢 Notifications")
    st.metric("Pending Follow-ups", len(pending_notifications))
    
    if pending_notifications:
        st.caption("Agents will deliver these within 5 seconds")
        for notif in pending_notifications[:3]:  # Show first 3
            st.caption(f"• {notif['caller_id'][:20]}...")
    
    st.divider()
    
    # Test request creator
    with st.expander("🧪 Create Test Request"):
        test_caller = st.text_input("Caller ID", "test_caller_001")
        test_question = st.text_area("Question", "What are your pricing options?")
        if st.button("Create Test Request"):
            create_help_request(test_caller, test_question, test_question)
            st.success("Test request created!")
            st.session_state.refresh_trigger += 1
            st.rerun()
    
    st.divider()
    
    if st.button("🔄 Refresh Dashboard"):
        st.session_state.refresh_trigger += 1
        st.rerun()

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs(["📋 Pending Requests", "✅ Resolved", "❌ Unresolved", "📚 Knowledge Base"])

# Tab 1: Pending Requests
with tab1:
    st.header("Pending Help Requests")
    
    pending_requests = [r for r in requests if r['status'] == 'pending']
    
    if not pending_requests:
        st.info("🎉 No pending requests! All caught up.")
    else:
        for req in pending_requests:
            # Check if request is about to timeout
            try:
                created_time = datetime.fromisoformat(req['created_at'])
                
                # Handle missing or invalid timeout_at field safely
                if req.get('timeout_at'):
                    try:
                        timeout_time = datetime.fromisoformat(req['timeout_at'])
                    except (ValueError, TypeError):
                        # If timeout_at is invalid, default to 2 hours from creation
                        timeout_time = created_time + timedelta(hours=2)
                        req['timeout_at'] = timeout_time.isoformat()
                        save_help_requests(requests)
                else:
                    # If no timeout set, default to 2 hours from creation
                    timeout_time = created_time + timedelta(hours=2)
                    req['timeout_at'] = timeout_time.isoformat()
                    save_help_requests(requests)
                
                time_remaining = timeout_time - datetime.now()
                
                # Color code based on urgency
                if time_remaining.total_seconds() < 0:
                    urgency_color = "⚫"
                    urgency_text = "OVERDUE - Already timed out"
                elif time_remaining.total_seconds() < 1800:  # Less than 30 minutes
                    urgency_color = "🔴"
                    urgency_text = f"URGENT - {int(time_remaining.total_seconds() / 60)} minutes left"
                elif time_remaining.total_seconds() < 3600:  # Less than 1 hour
                    urgency_color = "🟡"
                    urgency_text = f"{int(time_remaining.total_seconds() / 60)} minutes remaining"
                else:
                    urgency_color = "🟢"
                    urgency_text = f"{round(time_remaining.total_seconds() / 3600, 1)} hours remaining"
            
            except Exception as e:
                # Fallback if any datetime parsing fails
                urgency_color = "⚪"
                urgency_text = "Unknown timeout"
                st.caption(f"⚠️ Error calculating timeout: {e}")
            
            with st.expander(f"{urgency_color} {req['id']} - {req['caller_id']}", expanded=(urgency_color in ["🔴", "⚫"])):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Question:** {req['question']}")
                    st.caption(f"Created: {req['created_at']}")
                    st.caption(f"⏰ Timeout: {urgency_text}")
                    
                    if req.get('audio_transcript'):
                        st.text_area("Audio Transcript", req['audio_transcript'], height=100, key=f"transcript_{req['id']}")
                
                with col2:
                    st.markdown("**Actions:**")
                    
                    answer = st.text_area(
                        "Your Answer",
                        key=f"answer_{req['id']}",
                        placeholder="Type your answer here...",
                        height=100
                    )
                    
                    add_to_kb = st.checkbox("Add to Knowledge Base", value=True, key=f"kb_{req['id']}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✅ Resolve", key=f"resolve_{req['id']}", type="primary"):
                            if answer.strip():
                                if resolve_request(req['id'], answer, add_to_kb):
                                    st.success("✅ Request resolved! Agent will follow up with caller in 5 seconds.")
                                    time.sleep(2)
                                    st.rerun()
                            else:
                                st.error("Please provide an answer")
                    
                    with col_b:
                        if st.button("❌ Mark Unresolved", key=f"unresolved_{req['id']}"):
                            if mark_unresolved(req['id'], "Marked as unresolved by supervisor"):
                                st.warning("Request marked as unresolved")
                                time.sleep(1)
                                st.rerun()

# Tab 2: Resolved Requests
with tab2:
    st.header("Resolved Requests History")
    
    resolved_requests = [r for r in requests if r['status'] == 'resolved']
    
    if not resolved_requests:
        st.info("No resolved requests yet.")
    else:
        # Sort by resolved date (newest first)
        resolved_requests.sort(key=lambda x: x.get('resolved_at', ''), reverse=True)
        
        for req in resolved_requests:
            with st.expander(f"✅ {req['id']} - {req['caller_id']}"):
                st.markdown(f"**Question:** {req['question']}")
                st.markdown(f"**Answer:** {req['supervisor_answer']}")
                st.caption(f"Created: {req['created_at']}")
                st.caption(f"Resolved: {req['resolved_at']}")
                
                # Calculate response time
                try:
                    created = datetime.fromisoformat(req['created_at'])
                    resolved = datetime.fromisoformat(req['resolved_at'])
                    response_time = resolved - created
                    minutes = int(response_time.total_seconds() / 60)
                    st.caption(f"⏱️ Response time: {minutes} minutes")
                except:
                    pass

# Tab 3: Unresolved Requests
with tab3:
    st.header("Unresolved Requests")
    
    unresolved_requests = [r for r in requests if r['status'] == 'unresolved']
    
    if not unresolved_requests:
        st.info("No unresolved requests.")
    else:
        for req in unresolved_requests:
            with st.expander(f"❌ {req['id']} - {req['caller_id']}"):
                st.markdown(f"**Question:** {req['question']}")
                st.markdown(f"**Reason:** {req['supervisor_answer']}")
                st.caption(f"Created: {req['created_at']}")
                st.caption(f"Marked unresolved: {req['resolved_at']}")
                
                # Allow re-opening
                if st.button("🔄 Re-open Request", key=f"reopen_{req['id']}"):
                    for r in requests:
                        if r['id'] == req['id']:
                            r['status'] = 'pending'
                            r['resolved_at'] = None
                            r['supervisor_answer'] = None
                            # Reset timeout to 2 hours from now
                            r['timeout_at'] = (datetime.now() + timedelta(hours=2)).isoformat()
                    save_help_requests(requests)
                    st.success("Request re-opened!")
                    time.sleep(1)
                    st.rerun()

# Tab 4: Knowledge Base
with tab4:
    st.header("Learned Answers")
    
    kb = get_knowledge_base()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📚 {len(kb)} Questions in Knowledge Base")
    with col2:
        if st.button("➕ Add New Entry"):
            st.session_state.show_add_form = True
    
    # Add new entry form
    if st.session_state.get('show_add_form', False):
        with st.form("add_kb_entry"):
            new_q = st.text_input("Question")
            new_a = st.text_area("Answer")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Add Entry", type="primary")
            with col2:
                cancelled = st.form_submit_button("Cancel")
            
            if submitted and new_q and new_a:
                kb[new_q.lower().strip()] = new_a
                save_knowledge_base(kb)
                st.success("Entry added to knowledge base!")
                st.session_state.show_add_form = False
                time.sleep(1)
                st.rerun()
            
            if cancelled:
                st.session_state.show_add_form = False
                st.rerun()
    
    st.divider()
    
    # Display knowledge base
    if not kb:
        st.info("Knowledge base is empty. Resolve some requests to populate it!")
    else:
        # Search functionality
        search = st.text_input("🔍 Search knowledge base", "")
        
        filtered_kb = {k: v for k, v in kb.items() if search.lower() in k.lower()} if search else kb
        
        st.caption(f"Showing {len(filtered_kb)} of {len(kb)} entries")
        
        for i, (question, answer) in enumerate(sorted(filtered_kb.items())):
            with st.expander(f"Q: {question}"):
                st.markdown(f"**A:** {answer}")
                
                # Edit/Delete options
                col1, col2 = st.columns([4, 1])
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{i}"):
                        del kb[question]
                        save_knowledge_base(kb)
                        st.success("Entry deleted!")
                        time.sleep(1)
                        st.rerun()

# Footer
st.divider()
st.caption("Human-in-the-Loop AI Supervisor System")
st.caption("💡 Real-time follow-up: Agent checks for responses every 5 seconds | Requests timeout after 2 hours")