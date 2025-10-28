import asyncio
import json
from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins import deepgram
from transformers import pipeline
from dotenv import load_dotenv
import numpy as np
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from notifications import get_pending_notifications, mark_notification_processed

load_dotenv()

# File paths
KNOWLEDGE_BASE_FILE = "knowledge_base.json"
HELP_REQUESTS_FILE = "help_requests.json"

# --- Load Knowledge Base ---
print("📚 Loading knowledge base...")
try:
    with open('knowledge_base.json', 'r') as f:
        knowledge_base = json.load(f)
    print(f"✅ Loaded {len(knowledge_base)} knowledge entries")
except Exception as e:
    print(f"⚠️ Could not load knowledge base: {e}")
    knowledge_base = {}

# --- Setup Hugging Face local chatbot ---
print("🚀 Loading local Hugging Face model (distilgpt2)...")
chatbot = pipeline("text-generation", model="distilgpt2")

# --- Supervisor Escalation Functions ---
def load_help_requests():
    """Load help requests from file"""
    try:
        if Path(HELP_REQUESTS_FILE).exists():
            with open(HELP_REQUESTS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading help requests: {e}")
    return []

def save_help_requests(requests):
    """Save help requests to file"""
    try:
        with open(HELP_REQUESTS_FILE, 'w') as f:
            json.dump(requests, f, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ Error saving help requests: {e}")
        return False

def create_help_request(caller_id, question, audio_transcript=None):
    """Create a new help request for supervisor"""
    requests = load_help_requests()
    
    # Set timeout to 2 hours from now
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
    
    # Log to console (supervisor notification)
    print(f"\n🚨 SUPERVISOR ALERT: New help request from {caller_id}")
    print(f"   Question: {question}")
    print(f"   Request ID: {request['id']}")
    print(f"   Timeout at: {timeout_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return request

def mark_unresolved(request_id, reason="Timeout"):
    """Mark a request as unresolved"""
    requests = load_help_requests()
    
    for req in requests:
        if req['id'] == request_id:
            req['status'] = 'unresolved'
            req['resolved_at'] = datetime.now().isoformat()
            req['supervisor_answer'] = f"[Unresolved: {reason}]"
            save_help_requests(requests)
            
            print(f"⏰ REQUEST TIMEOUT: {request_id} marked as unresolved")
            return True
    
    return False

def is_generic_response(reply: str) -> bool:
    """Check if AI response is too generic/unhelpful"""
    generic_phrases = [
        "i'm here to help",
        "could you please ask",
        "please ask about",
        "how can i assist",
        "what would you like",
        "is there anything"
    ]
    
    reply_lower = reply.lower()
    
    # Check for generic phrases
    if any(phrase in reply_lower for phrase in generic_phrases):
        return True
    
    # Check if response is too short or repetitive
    if len(reply) < 15:
        return True
    
    words = reply.split()
    if len(words) > 3:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.6:  # Too repetitive
            return True
    
    return False

def generate_reply(user_input: str, caller_id: str = "unknown") -> str:
    """Generate a response - check knowledge base first, then use model, then escalate"""
    
    user_lower = user_input.lower().strip()
    user_cleaned = re.sub(r'[^\w\s]', '', user_lower)
    
    print(f"🔍 Searching knowledge base for: '{user_cleaned}'")
    
    # Common stop words to ignore
    stop_words = {'i', 'you', 'do', 'the', 'a', 'an', 'is', 'are', 'am', 'we', 'me', 'my'}
    
    # Priority 1: Specific keyword patterns
    if ("walk" in user_cleaned and "in" in user_cleaned) or "appointment" in user_cleaned or "book" in user_cleaned:
        for question, answer in knowledge_base.items():
            if "walk" in question.lower() or "appointment" in question.lower():
                print(f"📚 Match: '{question}' (walk-ins)")
                return answer
    
    if "close" in user_cleaned or "closing" in user_cleaned:
        for question, answer in knowledge_base.items():
            if "close" in question.lower():
                print(f"📚 Match: '{question}' (closing)")
                return answer
    
    # Check for "open" questions - be more flexible
    if "open" in user_cleaned or ("when" in user_cleaned and ("hour" in user_cleaned or len(user_cleaned.split()) <= 4)):
        # Check if it's about being open (general) or opening time (specific)
        if "time" in user_cleaned:
            for question, answer in knowledge_base.items():
                if "time" in question.lower() and "open" in question.lower():
                    print(f"📚 Match: '{question}' (opening time)")
                    return answer
        else:
            # General "are you open" or "when are you open"
            for question, answer in knowledge_base.items():
                if ("open" in question.lower() or "hours" in question.lower()) and "time" not in user_cleaned:
                    print(f"📚 Match: '{question}' (open/hours)")
                    return answer
    
    if "hour" in user_cleaned and "open" not in user_cleaned and "close" not in user_cleaned:
        for question, answer in knowledge_base.items():
            if "hours" in question.lower():
                print(f"📚 Match: '{question}' (hours)")
                return answer
    
    if "locat" in user_cleaned or "where" in user_cleaned or "address" in user_cleaned or "find" in user_cleaned:
        for question, answer in knowledge_base.items():
            if "locat" in question.lower() or "where" in question.lower() or "address" in question.lower() or "find" in question.lower():
                print(f"📚 Match: '{question}' (location)")
                return answer
    
    # Priority 2: Word overlap matching
    best_match = None
    best_score = 0
    
    for question, answer in knowledge_base.items():
        question_cleaned = re.sub(r'[^\w\s]', '', question.lower())
        user_words = set(word for word in user_cleaned.split() if word not in stop_words and len(word) > 2)
        question_words = set(word for word in question_cleaned.split() if word not in stop_words and len(word) > 2)
        common_words = user_words & question_words
        
        if len(common_words) > 0:
            score = len(common_words)
            if score > best_score:
                best_score = score
                best_match = (question, answer, common_words)
    
    if best_match and best_score >= 2:
        question, answer, common_words = best_match
        print(f"📚 Match: '{question}' (words: {common_words})")
        return answer
    
    # Priority 3: Try AI model
    print(f"🤖 Using AI model")
    
    # Don't use the AI model for very generic incomplete queries
    incomplete_patterns = ["you open", "are you", "do you", "can you", "is your", "what is"]
    if any(pattern in user_cleaned and len(user_cleaned.split()) <= 3 for pattern in incomplete_patterns):
        # ESCALATE - question too vague
        print(f"🚨 ESCALATING: Question too incomplete")
        create_help_request(caller_id, user_input, user_input)
        return "That's a great question! I've forwarded it to my supervisor who will get back to you shortly with the answer."
    
    prompt = f"Customer question: {user_input}\nHelpful answer:"
    
    try:
        response = chatbot(
            prompt,
            max_new_tokens=25,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=chatbot.tokenizer.eos_token_id,
            repetition_penalty=1.5,
            top_p=0.9
        )
        reply = response[0]["generated_text"][len(prompt):].strip()
        
        # Clean up the response
        if '\n' in reply:
            reply = reply.split('\n')[0].strip()
        
        # Remove repetitive patterns
        words = reply.split()
        if len(words) > 5:
            # Check for repetition
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.6:  # Too much repetition
                reply = ""  # Force escalation
        
        # Check if response is generic or poor quality
        if not reply or len(reply) < 10 or is_generic_response(reply):
            # ESCALATE - AI couldn't generate good answer
            print(f"🚨 ESCALATING: AI response inadequate")
            create_help_request(caller_id, user_input, user_input)
            return "That's a great question! I've forwarded it to my supervisor who will get back to you shortly with the answer."
        
        # Check if response makes sense
        if len(reply) > 10 and len(reply) < 100:
            return reply
        else:
            # ESCALATE - response doesn't make sense
            print(f"🚨 ESCALATING: AI response out of bounds")
            create_help_request(caller_id, user_input, user_input)
            return "That's a great question! I've forwarded it to my supervisor who will get back to you shortly with the answer."
            
    except Exception as e:
        # ESCALATE - AI model error
        print(f"🚨 ESCALATING: AI model error - {e}")
        create_help_request(caller_id, user_input, user_input)
        return "That's a great question! I've forwarded it to my supervisor who will get back to you shortly with the answer."

async def check_timeouts_background():
    """Background task to check for timed out requests"""
    print("⏰ Timeout checker started")
    
    while True:
        try:
            requests = load_help_requests()
            now = datetime.now()
            
            for req in requests:
                if req['status'] == 'pending':
                    # Ensure timeout_at is set
                    if not req.get('timeout_at'):
                        created = datetime.fromisoformat(req['created_at'])
                        req['timeout_at'] = (created + timedelta(hours=2)).isoformat()
                    
                    # Check if timed out
                    timeout_time = datetime.fromisoformat(req['timeout_at'])
                    if now > timeout_time:
                        print(f"⏰ REQUEST TIMEOUT: {req['id']} (exceeded 2 hours)")
                        mark_unresolved(req['id'], "Supervisor did not respond within 2 hours")
            
            save_help_requests(requests)
            
        except Exception as e:
            print(f"⚠️ Error checking timeouts: {e}")
        
        await asyncio.sleep(60)  # Check every minute

async def check_notifications(tts, audio_source, room_name):
    """Background task to check for supervisor responses and follow up with caller"""
    print("🔔 Notification checker started - checking every 5 seconds")
    
    while True:
        try:
            pending = get_pending_notifications()
            
            for notification in pending:
                # Only process notifications for this caller
                # Match either by exact room name or if it's the general caller
                if notification['caller_id'] == room_name:
                    print(f"\n📞 FOLLOWING UP WITH CALLER: {notification['caller_id']}")
                    print(f"   Request: {notification['request_id']}")
                    print(f"   Answer from supervisor: {notification['answer']}")
                    
                    # Speak the answer back to the caller
                    follow_up_text = f"Good news! I heard back from my supervisor. {notification['answer']}"
                    
                    print(f"🤖 Saying: {follow_up_text}")
                    
                    try:
                        tts_stream = tts.synthesize(follow_up_text)
                        async for audio_event in tts_stream:
                            await audio_source.capture_frame(audio_event.frame)
                        
                        print("✅ Follow-up delivered to caller!")
                        
                    except Exception as e:
                        print(f"❌ TTS error during follow-up: {e}")
                    
                    # Mark as processed
                    mark_notification_processed(notification['id'])
                    print(f"✅ Notification {notification['id']} processed\n")
            
        except Exception as e:
            print(f"⚠️ Error checking notifications: {e}")
        
        await asyncio.sleep(5)  # Check every 5 seconds

async def entrypoint(ctx: JobContext):
    print(f"🎧 Connecting to room: {ctx.room.name}")
    
    await ctx.connect()
    print(f"✅ Connected to room: {ctx.room.name}")
    
    # Initialize Deepgram TTS and STT
    tts = deepgram.TTS()
    stt = deepgram.STT()
    
    # Create audio source for agent speech
    audio_source = rtc.AudioSource(sample_rate=24000, num_channels=1)
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent_voice", audio_source)
    
    # Publish the audio track
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await ctx.room.local_participant.publish_track(audio_track, options)
    
    print("🤖 Voice assistant is ready!")
    
    # Welcome message
    welcome_text = "Hello! I'm your AI assistant. Ask me about our hours, location, or walk-ins."
    print(f"🤖 Saying: {welcome_text}")
    
    try:
        tts_stream = tts.synthesize(welcome_text)
        async for audio_event in tts_stream:
            await audio_source.capture_frame(audio_event.frame)
    except Exception as e:
        print(f"TTS error: {e}")
    
    # State management
    audio_buffer = []
    is_speaking = False
    is_processing = False
    
    # START BACKGROUND TASKS
    print("🚀 Starting background tasks...")
    asyncio.create_task(check_notifications(tts, audio_source, ctx.room.name))
    asyncio.create_task(check_timeouts_background())
    print("✅ Background tasks running: notification checker + timeout monitor")
    
    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        print(f"📥 Track subscribed: {track.kind} from {participant.identity}")
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            asyncio.create_task(process_audio_track(track))
    
    async def process_audio_track(track: rtc.AudioTrack):
        """Process incoming audio from user"""
        nonlocal audio_buffer, is_speaking, is_processing
        
        print("👂 Listening for speech...")
        audio_stream = rtc.AudioStream(track)
        
        # Optimized VAD settings
        silence_frames = 0
        speech_frames = 0
        SILENCE_THRESHOLD = 50  # Even longer wait for complete sentences
        SPEECH_THRESHOLD = 3    
        ENERGY_THRESHOLD = 300  # Less sensitive to reduce false positives
        MIN_AUDIO_FRAMES = 15   # Longer minimum for quality audio
        
        async for event in audio_stream:
            if is_processing:
                continue
                
            frame = event.frame
            
            try:
                samples = np.frombuffer(frame.data, dtype=np.int16)
                energy = np.abs(samples).mean()
                
                if energy > ENERGY_THRESHOLD:
                    speech_frames += 1
                    silence_frames = 0
                    
                    if speech_frames > SPEECH_THRESHOLD:
                        if not is_speaking:
                            print("🎤 Recording...")
                            is_speaking = True
                            audio_buffer = []
                        audio_buffer.append(frame)
                else:
                    if is_speaking:
                        silence_frames += 1
                        audio_buffer.append(frame)
                        
                        if silence_frames > SILENCE_THRESHOLD:
                            print("🎤 Processing...")
                            is_speaking = False
                            speech_frames = 0
                            
                            if len(audio_buffer) >= MIN_AUDIO_FRAMES:
                                is_processing = True
                                await process_speech()
                                audio_buffer = []
                                is_processing = False
                            else:
                                print("⚠️ Audio too short")
                                audio_buffer = []
                        
            except Exception as e:
                print(f"Frame error: {e}")
    
    async def process_speech():
        """Process the collected audio chunks"""
        if not audio_buffer:
            return
        
        print(f"🎤 Transcribing {len(audio_buffer)} frames...")
        
        try:
            stt_stream = stt.stream()
            
            for frame in audio_buffer:
                stt_stream.push_frame(frame)
            
            stt_stream.end_input()
            
            # Collect all transcripts and select the best one
            transcripts = []
            final_transcript = ""
            
            async for event in stt_stream:
                if hasattr(event, 'alternatives') and event.alternatives:
                    text = event.alternatives[0].text
                    if text and len(text) > 1:
                        transcripts.append(text)
                        print(f"📝 '{text}'")
                        # Keep track of the longest transcript
                        if len(text) > len(final_transcript):
                            final_transcript = text
            
            # Use the final/longest transcript
            if not transcripts:
                print("⚠️ No speech detected")
                return
            
            user_text = final_transcript if final_transcript else max(transcripts, key=len)
            
            # Skip very incomplete sentences (but be more lenient)
            if len(user_text) < 3:
                print(f"⚠️ Too short: '{user_text}'")
                return
            
            print(f"✅ User: '{user_text}'")
            
            # Generate response with caller context (use room name as caller ID)
            caller_id = ctx.room.name or "unknown_caller"
            reply = generate_reply(user_text, caller_id=caller_id)
            print(f"🤖 Reply: '{reply}'")
            
            # Speak response
            tts_stream = tts.synthesize(reply)
            async for audio_event in tts_stream:
                await audio_source.capture_frame(audio_event.frame)
            
            print("✅ Done\n")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("⏳ Ready for input...\n")
    await asyncio.Future()

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )