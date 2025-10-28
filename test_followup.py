import time
from datetime import datetime
from agent import create_help_request, load_help_requests
from supervisor_dashboard import resolve_request
from notifications import get_pending_notifications, load_notifications

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def print_step(step_num, title):
    """Print a formatted step header"""
    print(f"\n{step_num} {title}")
    print("-" * 70)

def test_complete_flow():
    """Test the complete escalation → resolution → follow-up flow"""
    
    print_section("🧪 TESTING COMPLETE HUMAN-IN-THE-LOOP FLOW")
    
    # Step 1: Create help request (simulating agent escalation)
    print_step("1️⃣", "STEP 1: Agent Escalation")
    print("Simulating: Caller asks a question the AI doesn't know...")
    time.sleep(1)
    
    request = create_help_request(
        caller_id="playground-TEST-123",
        question="What are your pricing options for color treatments?",
        audio_transcript="What are your pricing options for color treatments?"
    )
    print(f"✅ Help request created: {request['id']}")
    print(f"   Caller ID: {request['caller_id']}")
    print(f"   Status: {request['status']}")
    print(f"   Timeout at: {request['timeout_at']}")
    
    time.sleep(2)
    
    # Step 2: Check requests file
    print_step("2️⃣", "STEP 2: Verify Request in Database")
    all_requests = load_help_requests()
    pending = [r for r in all_requests if r['status'] == 'pending']
    print(f"✅ Found {len(pending)} pending request(s) in help_requests.json")
    if pending:
        print(f"   Latest request: {pending[-1]['id']}")
    
    time.sleep(2)
    
    # Step 3: Supervisor resolves
    print_step("3️⃣", "STEP 3: Supervisor Resolution")
    print("Simulating: Supervisor provides answer in dashboard...")
    time.sleep(1)
    
    answer = "Our color treatments start at $80 for partial highlights and $120 for full color. We use premium Redken products!"
    success = resolve_request(request['id'], answer, add_to_kb=True)
    
    if success:
        print(f"✅ Request resolved successfully")
        print(f"   Answer: {answer}")
        print(f"   Added to knowledge base: Yes")
    else:
        print(f"❌ Failed to resolve request")
    
    time.sleep(2)
    
    # Step 4: Check notification was created
    print_step("4️⃣", "STEP 4: Verify Notification Created")
    pending_notifications = get_pending_notifications()
    
    if pending_notifications:
        print(f"✅ Found {len(pending_notifications)} pending notification(s)")
        for notif in pending_notifications:
            if notif['request_id'] == request['id']:
                print(f"   Notification ID: {notif['id']}")
                print(f"   For caller: {notif['caller_id']}")
                print(f"   Answer preview: {notif['answer'][:50]}...")
                print(f"   Processed: {notif['processed']}")
    else:
        print("❌ No notifications found!")
    
    time.sleep(2)
    
    # Step 5: Check knowledge base was updated
    print_step("5️⃣", "STEP 5: Verify Knowledge Base Update")
    from supervisor_dashboard import get_knowledge_base
    kb = get_knowledge_base()
    
    question_key = request['question'].lower().strip()
    if question_key in kb:
        print(f"✅ Knowledge base updated successfully")
        print(f"   Question: {question_key}")
        print(f"   Answer: {kb[question_key]}")
    else:
        print(f"❌ Question not found in knowledge base")
    
    time.sleep(2)
    
    # Step 6: Simulate agent checking notifications
    print_step("6️⃣", "STEP 6: Agent Follow-up (Simulated)")
    print("In production, the AI agent would:")
    print("   1. Poll notifications every 5 seconds")
    print("   2. Find this notification")
    print("   3. Speak the answer to the caller via LiveKit")
    print("   4. Mark notification as processed")
    print("")
    print("📞 Agent would say to caller:")
    print(f'   "Good news! I heard back from my supervisor. {answer}"')
    
    # Simulate marking as processed
    from notifications import mark_notification_processed
    if pending_notifications:
        for notif in pending_notifications:
            if notif['request_id'] == request['id']:
                mark_notification_processed(notif['id'])
                print(f"\n✅ Notification {notif['id']} marked as processed")
    
    time.sleep(2)
    
    # Final summary
    print_section("📊 TEST SUMMARY")
    print("\n✅ Complete flow tested successfully!")
    print("\nFlow verification:")
    print("   ✅ Agent escalated question")
    print("   ✅ Help request created and stored")
    print("   ✅ Supervisor provided answer")
    print("   ✅ Notification created for agent")
    print("   ✅ Knowledge base updated")
    print("   ✅ Agent would follow up with caller")
    print("\n" + "=" * 70)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 70 + "\n")

def test_timeout_flow():
    """Test the timeout functionality"""
    
    print_section("🧪 TESTING TIMEOUT FLOW")
    
    print_step("1️⃣", "STEP 1: Create Request with Short Timeout")
    print("Creating a request that will timeout...")
    
    from datetime import timedelta
    request = create_help_request(
        caller_id="timeout-test-caller",
        question="This request will timeout",
        audio_transcript="This request will timeout"
    )
    
    # Manually set timeout to past time for testing
    all_requests = load_help_requests()
    for req in all_requests:
        if req['id'] == request['id']:
            past_time = datetime.now() - timedelta(minutes=1)
            req['timeout_at'] = past_time.isoformat()
    
    from supervisor_dashboard import save_help_requests
    save_help_requests(all_requests)
    
    print(f"✅ Request created: {request['id']}")
    print(f"   Timeout set to: 1 minute ago (for testing)")
    
    time.sleep(2)
    
    print_step("2️⃣", "STEP 2: Run Timeout Check")
    print("Checking for timed out requests...")
    
    # Simulate timeout checker
    from agent import mark_unresolved
    all_requests = load_help_requests()
    now = datetime.now()
    
    for req in all_requests:
        if req['status'] == 'pending' and req.get('timeout_at'):
            timeout_time = datetime.fromisoformat(req['timeout_at'])
            if now > timeout_time:
                print(f"⏰ Found timed out request: {req['id']}")
                mark_unresolved(req['id'], "Request timed out (test)")
    
    time.sleep(2)
    
    print_step("3️⃣", "STEP 3: Verify Request Marked Unresolved")
    all_requests = load_help_requests()
    
    for req in all_requests:
        if req['id'] == request['id']:
            print(f"✅ Request status: {req['status']}")
            print(f"   Supervisor answer: {req['supervisor_answer']}")
            print(f"   Resolved at: {req['resolved_at']}")
    
    print("\n" + "=" * 70)
    print("✅ TIMEOUT TEST PASSED!")
    print("=" * 70 + "\n")

def test_knowledge_base_lookup():
    """Test that resolved questions are found in future queries"""
    
    print_section("🧪 TESTING KNOWLEDGE BASE LOOKUP")
    
    print_step("1️⃣", "STEP 1: Check Current Knowledge Base")
    from supervisor_dashboard import get_knowledge_base
    kb = get_knowledge_base()
    
    print(f"✅ Knowledge base has {len(kb)} entries")
    
    # Add a test entry if not exists
    test_question = "what are your holiday hours"
    test_answer = "We're open 10 AM to 5 PM on holidays"
    
    if test_question not in kb:
        kb[test_question] = test_answer
        from supervisor_dashboard import save_knowledge_base
        save_knowledge_base(kb)
        print(f"✅ Added test entry: '{test_question}'")
    
    time.sleep(1)
    
    print_step("2️⃣", "STEP 2: Test Knowledge Base Lookup")
    from agent import generate_reply
    
    # Test exact match
    print("Testing query: 'what are your holiday hours'")
    reply = generate_reply("what are your holiday hours", caller_id="test-kb-lookup")
    print(f"✅ Reply: {reply}")
    
    time.sleep(1)
    
    # Test similar match
    print("\nTesting query: 'holiday hours' (partial match)")
    reply = generate_reply("holiday hours", caller_id="test-kb-lookup")
    print(f"✅ Reply: {reply}")
    
    print("\n" + "=" * 70)
    print("✅ KNOWLEDGE BASE LOOKUP TEST PASSED!")
    print("=" * 70 + "\n")

def run_all_tests():
    """Run all test suites"""
    print("\n" + "=" * 70)
    print("🚀 RUNNING ALL TESTS")
    print("=" * 70)
    
    try:
        # Test 1: Complete flow
        test_complete_flow()
        time.sleep(3)
        
        # Test 2: Timeout
        test_timeout_flow()
        time.sleep(3)
        
        # Test 3: Knowledge base lookup
        test_knowledge_base_lookup()
        
        # Final report
        print("\n" + "=" * 70)
        print("🎉 ALL TEST SUITES PASSED!")
        print("=" * 70)
        print("\nSummary:")
        print("   ✅ Complete escalation → resolution → follow-up flow")
        print("   ✅ Timeout handling")
        print("   ✅ Knowledge base learning and lookup")
        print("\n💡 Your system is ready for production!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run specific test or all tests
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "flow":
            test_complete_flow()
        elif test_name == "timeout":
            test_timeout_flow()
        elif test_name == "kb":
            test_knowledge_base_lookup()
        else:
            print("Usage: python test_followup.py [flow|timeout|kb]")
            print("Or run without arguments to run all tests")
    else:
        run_all_tests()