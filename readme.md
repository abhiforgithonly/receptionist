# 🎧 AI Receptionist - Human-in-the-Loop Voice Agent

An intelligent voice receptionist system built with LiveKit that combines AI automation with human supervision. When the AI encounters questions it can't answer, it escalates to a human supervisor who can provide answers that are automatically relayed back to the caller and added to the system's knowledge base.

## 🌟 Features

### Core Capabilities
- **Real-time Voice Interaction**: Voice-to-voice conversations using LiveKit, Deepgram STT/TTS
- **Knowledge Base Learning**: Automatically learns from supervisor responses
- **Smart Escalation**: Routes complex questions to human supervisors
- **Automatic Follow-up**: Calls back customers within 5 seconds when supervisor answers
- **Timeout Management**: Tracks pending requests with 2-hour timeout windows
- **Dashboard Monitoring**: Web-based supervisor interface with real-time stats

### Intelligent Response System
1. **Knowledge Base Priority**: Checks learned answers first
2. **AI Fallback**: Uses local Hugging Face model (distilgpt2) for unknown queries
3. **Human Escalation**: Routes to supervisor when AI responses are inadequate
4. **Quality Control**: Validates AI responses before delivering to caller

## 📋 System Architecture

```
Caller (LiveKit) 
    ↓
Agent (agent.py)
    ├─→ Knowledge Base (knowledge_base.json)
    ├─→ AI Model (distilgpt2)
    └─→ Escalate to Supervisor
            ↓
    Supervisor Dashboard (supervisor_dashboard.py)
            ↓
    Notification System (notifications.py)
            ↓
    Follow-up to Caller (within 5 seconds)
```

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.8+
LiveKit server access
Deepgram API key
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/abhiforgithonly/receptionist.git7y8
cd ai-receptionist
```

2. **Install dependencies**
```bash
pip install livekit livekit-agents livekit-plugins-deepgram
pip install transformers torch
pip install streamlit python-dotenv
pip install numpy
```

3. **Set up environment variables**
Create a `.env` file:
```env
DEEPGRAM_API_KEY=your_deepgram_api_key
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
```

4. **Initialize data files**
```bash
# Create empty JSON files if they don't exist
echo "[]" > help_requests.json
echo "[]" > pending_notifications.json
```

### Running the System

1. **Start the AI Agent**
```bash
python agent.py dev
```

2. **Launch Supervisor Dashboard** (in separate terminal)
```bash
streamlit run supervisor_dashboard.py
```

3. **Access the dashboard**
```
http://localhost:8501
```

4. **Connect via LiveKit**
- Use LiveKit Playground or custom client
- Connect to your LiveKit room
- Start speaking!

## ⚠️ Known Issues & Troubleshooting

### Critical Warning
```
AttributeError: 'MessageFactory' object has no attribute 'GetPrototype'
```

**Cause**: This error occurs due to a protobuf version mismatch between different dependencies (particularly between `livekit` and `transformers` packages).

**Solutions**:
1. **Downgrade protobuf** (recommended):
   ```bash
   pip install protobuf==3.20.3
   ```

2. **Upgrade to compatible versions**:
   ```bash
   pip install --upgrade protobuf livekit livekit-agents
   ```

3. **Use virtual environment** to isolate dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Other Common Issues

**Audio not capturing**
- Check microphone permissions
- Verify LiveKit connection is established
- Ensure audio track is published correctly

**TTS not working**
- Verify Deepgram API key is valid
- Check API quota limits
- Ensure network connectivity

**Knowledge base not updating**
- Check file permissions for JSON files
- Verify `knowledge_base.json` is not corrupted
- Restart agent after manual edits

**Notifications not delivering**
- Ensure both agent and dashboard are running
- Check `pending_notifications.json` for entries
- Verify `caller_id` matches the room name

## 📁 File Structure

```
├── agent.py                      # Main AI agent with LiveKit integration
├── supervisor_dashboard.py       # Streamlit web interface for supervisors
├── notifications.py              # Notification system for follow-ups
├── knowledge_base.json           # Learned Q&A pairs
├── help_requests.json            # Escalated questions tracking
├── pending_notifications.json    # Queue of supervisor answers
├── test_followup.py             # Comprehensive test suite
├── check_plugin.py              # Plugin verification utility
└── .env                         # Environment configuration
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python test_followup.py

# Run specific test
python test_followup.py flow      # Test escalation → resolution → follow-up
python test_followup.py timeout   # Test timeout handling
python test_followup.py kb        # Test knowledge base lookup
```

## 🎯 Use Cases

- **Small Business Reception**: Handle calls when staff is busy
- **Medical Offices**: Manage appointment inquiries
- **Retail Stores**: Answer common questions about hours, location, services
- **Service Businesses**: Route complex queries to appropriate staff
- **Call Centers**: First-line automated response with human backup

## 🔧 Configuration

### Adjusting Timeouts
In `agent.py`, modify:
```python
timeout_time = datetime.now() + timedelta(hours=2)  # Change hours value
```

### Voice Activity Detection (VAD) Settings
Fine-tune in `agent.py`:
```python
SILENCE_THRESHOLD = 50      # Frames of silence before processing
SPEECH_THRESHOLD = 3        # Frames of speech to start recording
ENERGY_THRESHOLD = 300      # Audio energy level for speech detection
MIN_AUDIO_FRAMES = 15       # Minimum frames for valid audio
```

### AI Model Configuration
In `agent.py`:
```python
response = chatbot(
    prompt,
    max_new_tokens=25,        # Adjust response length
    temperature=0.7,          # Creativity (0.1-1.0)
    repetition_penalty=1.5,   # Reduce repetition
)
```

## 🚀 Future Improvements

### 1. **Enhanced Speech Recognition**
- **Upgrade to Whisper**: Replace Deepgram with OpenAI's Whisper for better accuracy
  ```python
  from livekit.plugins import openai
  stt = openai.STT(model="whisper-1")
  ```
- **Multi-language Support**: Add language detection and multi-language transcription
- **Custom Acoustic Models**: Train on domain-specific vocabulary

### 2. **Better Language Models**
- **Replace distilgpt2** with more capable models:
  - **GPT-3.5/GPT-4**: For production-quality responses
  - **Claude**: For nuanced, context-aware answers
  - **Llama 2/3**: Open-source alternative with better reasoning
  - **Mistral**: Fast, efficient, and accurate
- **Fine-tuning**: Train on business-specific conversations
- **RAG Integration**: Combine with vector database for semantic search

### 3. **Voice Quality Improvements**
- **Neural TTS**: Upgrade to ElevenLabs or Azure Neural TTS for natural voices
- **Voice Cloning**: Create custom brand voices
- **Emotion Recognition**: Detect caller sentiment and adjust tone
- **Background Noise Suppression**: Implement Krisp or similar

### 4. **Advanced Features**
- **Multi-turn Conversations**: Context-aware dialogue management
- **Appointment Booking**: Direct calendar integration
- **Payment Processing**: Handle transactions via voice
- **Call Analytics**: Track metrics, sentiment, resolution rates
- **A/B Testing**: Test different prompts and models
- **Voice Biometrics**: Caller identification and authentication

### 5. **Scalability & Production**
- **Database Migration**: Move from JSON to PostgreSQL/MongoDB
- **Redis Caching**: Fast knowledge base lookup
- **Load Balancing**: Handle multiple simultaneous calls
- **Docker Deployment**: Containerize for easy scaling
- **Kubernetes**: Orchestrate multiple agent instances
- **Monitoring**: Add Prometheus, Grafana dashboards
- **Error Tracking**: Integrate Sentry for bug reporting

### 6. **UX Enhancements**
- **Mobile Dashboard**: React Native supervisor app
- **Push Notifications**: Alert supervisors via Twilio/Firebase
- **Voice Commands**: "Transfer to supervisor" trigger
- **Call Recording**: Store conversations for training
- **Transcription Export**: Download conversation logs
- **Analytics Dashboard**: Visualize trends, peak times, common questions

### 7. **Security & Compliance**
- **End-to-End Encryption**: Secure voice data
- **HIPAA Compliance**: For healthcare applications
- **GDPR Tools**: Data deletion, export, consent management
- **PCI DSS**: For payment card handling
- **Audit Logs**: Track all supervisor actions

### 8. **Integration Capabilities**
- **CRM Integration**: Sync with Salesforce, HubSpot
- **Calendar Apps**: Google Calendar, Outlook
- **Ticketing Systems**: Jira, Zendesk
- **Slack/Teams**: Notify supervisors in chat
- **SMS Follow-up**: Text customers after calls
- **Email Reports**: Daily summaries to managers

## 📊 Performance Benchmarks

Current system performance (on typical hardware):
- **Response Time**: 2-4 seconds from speech end to reply start
- **Transcription Accuracy**: ~85% (Deepgram dependent)
- **Knowledge Base Lookup**: <100ms
- **Follow-up Latency**: 5-10 seconds after supervisor response
- **Concurrent Calls**: Limited to 1 (scale with multiple instances)

## 🤝 Contributing

Contributions are welcome! Areas for contribution:
- Model improvements and fine-tuning
- Additional language support
- UI/UX enhancements for dashboard
- Integration connectors
- Test coverage expansion
- Documentation improvements

## 🎓 Project Context

This project was developed as part of an academic assessment to demonstrate:
- Real-time voice AI implementation
- Human-in-the-loop system design
- Full-stack integration (agent + dashboard)
- Production-ready error handling
- Scalable architecture patterns

## 🙏 Acknowledgments

- **LiveKit**: Real-time communication infrastructure
- **Deepgram**: Speech recognition and synthesis
- **Hugging Face**: Transformer models and pipeline
- **Streamlit**: Rapid dashboard development

## 📞 Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section above

---

**Built with ❤️ for better customer service automation**