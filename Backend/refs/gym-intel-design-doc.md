# GymIntel: AI-Powered Workout Intelligence Platform

## Design Document

---

## 1. Executive Summary

### Project Name
**GymIntel** — Your AI Workout Coach

### One-Liner
Upload your workout videos, get instant form feedback and muscle tracking, then talk to your AI coach to optimize your training.

### Target Tracks
- **Primary:** Health & Wellness
- **Sponsors:** TwelveLabs, MongoDB, Gemini, Deepgram, Snowflake, ElevenLabs

### Core Value Propositions
1. **Automated workout logging** — No more manual tracking, just record and upload
2. **Form analysis** — Catch injuries before they happen
3. **Muscle balance tracking** — Visualize training distribution over time
4. **Social benchmarking** — See how you compare to similar lifters
5. **Voice-first coaching** — Hands-free interaction perfect for the gym

---

## 2. Problem & Solution

### Problem Statement
Fitness enthusiasts face three persistent challenges:
1. **Manual logging is tedious** — Most people abandon workout tracking within weeks
2. **Form feedback requires expensive trainers** — Bad form leads to injury
3. **Training blind spots** — Without data, muscle imbalances develop over months

### Solution
GymIntel transforms passive workout recordings into actionable intelligence:
- Record your workout (phone on tripod, gym mirror, etc.)
- Upload the video post-workout
- Receive instant breakdown: exercises detected, muscles worked, form notes
- Track progress over time with muscle activation curves
- Get personalized recommendations based on your patterns and similar users
- Chat with an AI coach anytime via voice

### Target Users
- Intermediate gym-goers (6+ months experience)
- Self-coached athletes
- People returning to fitness after a break
- Anyone curious about optimizing their training

---

## 3. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                │
│  Web App (React/Next.js)                                                │
│  ├─ Video Upload Interface                                              │
│  ├─ Workout Dashboard                                                   │
│  ├─ Muscle Heatmap Visualization                                        │
│  ├─ History & Trends                                                    │
│  └─ Voice Coach Interface                                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                   │
│  Backend (Python FastAPI)                                               │
│  ├─ Video upload and analysis orchestration                             │
│  ├─ Workout history and insights endpoints                              │
│  ├─ Recommendations engine                                              │
│  └─ Voice coach WebSocket                                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌───────────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│   ANALYSIS PIPELINE   │ │   DATA LAYER    │ │   INTELLIGENCE LAYER    │
├───────────────────────┤ ├─────────────────┤ ├─────────────────────────┤
│                       │ │                 │ │                         │
│ TwelveLabs            │ │ MongoDB         │ │ Gemini                  │
│ └─ Exercise detection │ │ └─ User data    │ │ └─ Insights & coaching  │
│    and segmentation   │ │    and history  │ │                         │
│                       │ │                 │ │ Snowflake               │
│ MediaPipe             │ │                 │ │ └─ Collaborative        │
│ └─ Pose estimation    │ │                 │ │    filtering            │
│                       │ │                 │ │                         │
│ Muscle Mapper         │ │                 │ │ Deepgram                │
│ └─ Exercise → muscle  │ │                 │ │ └─ Voice STT            │
│    activation lookup  │ │                 │ │                         │
│                       │ │                 │ │ ElevenLabs              │
│                       │ │                 │ │ └─ Voice TTS            │
└───────────────────────┘ └─────────────────┘ └─────────────────────────┘
```

### Component Responsibilities

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Frontend | Next.js, TailwindCSS, Recharts | UI, visualizations, voice interface |
| Backend | Python, FastAPI | API routing, orchestration, business logic |
| Video Analysis | TwelveLabs API | Exercise detection, segmentation, visual understanding |
| Pose Analysis | MediaPipe | Keypoint extraction, joint angle calculation |
| Muscle Mapping | Custom lookup table | Exercise → muscle activation mapping |
| Primary Database | MongoDB Atlas | User data, workout history, form issues |
| Analytics DB | Snowflake | Aggregate patterns, collaborative filtering |
| LLM | Google Gemini | Insights, recommendations, coach reasoning |
| Voice STT | Deepgram | Real-time speech-to-text |
| Voice TTS | ElevenLabs | Natural speech synthesis |

---

## 4. Core Features

### Feature 1: Video Upload & Exercise Detection

**Flow:** User uploads workout video → TwelveLabs segments and identifies exercises → System extracts pose data → Muscle activation calculated → Results displayed

**What the user sees:**
- Timeline of detected exercises with timestamps
- Rep counts per exercise
- Muscle activation breakdown per exercise
- Form notes and warnings

### Feature 2: Muscle Balance Tracking

**Flow:** Workout data stored in MongoDB → Aggregated over time → Visualized as muscle heatmap and trends

**What the user sees:**
- Body heatmap showing which muscles are trained most/least
- Push/pull balance indicators
- Week-over-week comparison
- Imbalance warnings (e.g., "You've hit chest 6x but back only 2x this month")

### Feature 3: Form Feedback

**Flow:** TwelveLabs identifies form issues → MediaPipe provides joint angle data → Gemini generates plain-English feedback

**What the user sees:**
- Timestamped form notes ("0:34 - knees caving inward on squat")
- Severity indicators (info / warning / critical)
- Suggestions for improvement
- Option to view frame capture of the issue

### Feature 4: Social Benchmarking & Recommendations

**Flow:** User patterns synced to Snowflake (anonymized) → Collaborative filtering finds similar users → Recommendations generated

**What the user sees:**
- "Users like you also enjoy: face pulls, Romanian deadlifts"
- "You're in the top 30% for squat frequency"
- "Similar lifters train back 2x more than you"

### Feature 5: Voice Coach

**Flow:** User speaks → Deepgram STT → Gemini reasons + calls functions → Response generated → ElevenLabs TTS

**Available voice commands:**
- "How's my training balance this month?"
- "What should I focus on today?"
- "How's my squat form been lately?"
- "What exercises am I missing?"
- "Compare me to other lifters"

**Coach capabilities (via function calling):**
- Query workout history
- Analyze muscle balance
- Retrieve form feedback
- Get recommendations from Snowflake
- Compare to peer benchmarks

---

## 5. Data Models

### MongoDB Collections

**Users**
- Profile information
- Settings and preferences
- TwelveLabs index reference

**Workouts**
- Video reference
- Date and duration
- List of exercises detected
- Overall muscle activation summary
- Generated insights

**Exercises (embedded in Workouts)**
- Exercise name and variation
- Timestamps (start/end)
- Reps and sets detected
- Muscle activation breakdown
- Pose metrics (joint angles, ROM)
- Form feedback notes

### Snowflake Tables

**User Workout Patterns (anonymized)**
- Hashed user ID
- Muscle distribution over last 30 days
- Favorite exercises
- Workout frequency
- Experience level

**Exercise Popularity**
- Exercise name
- Total users performing it
- Common exercise pairings

---

## 6. Sponsor Integration Summary

| Sponsor | Role in Project | Integration Point |
|---------|-----------------|-------------------|
| **TwelveLabs** | Core video understanding | Exercise detection, segmentation, form analysis |
| **MongoDB** | Primary data store | User profiles, workout history, form issues |
| **Gemini** | Intelligence layer | Insight generation, form feedback, coach reasoning |
| **Deepgram** | Voice input | Streaming STT for voice coach |
| **Snowflake** | Social analytics | Collaborative filtering, peer benchmarks |
| **ElevenLabs** | Voice output | TTS for coach responses |

---

## 7. User Flows

### Flow 1: Upload Workout

1. User selects video from device
2. Video uploads to backend
3. Backend sends to TwelveLabs for indexing
4. Once indexed, backend queries for exercise segments
5. For each segment: extract pose data, calculate muscle activation, generate form notes
6. Store complete workout in MongoDB
7. Return results to frontend
8. User sees exercise breakdown, muscle heatmap, form feedback

### Flow 2: View Dashboard

1. User opens dashboard
2. Frontend fetches workout history from backend
3. Backend aggregates muscle activation over time
4. Frontend renders muscle heatmap, trends, and insights
5. User can drill into individual workouts

### Flow 3: Voice Coach Interaction

1. User activates microphone
2. Audio streams to backend via WebSocket
3. Backend streams to Deepgram for real-time transcription
4. Complete utterance sent to Gemini with function definitions
5. Gemini reasons and calls appropriate functions (query history, get recommendations, etc.)
6. Function results fed back to Gemini for final response
7. Response sent to ElevenLabs for TTS
8. Audio streamed back to user

---

## 8. Demo Narrative

**Opening Hook:**
> "Every gym-goer has the same problem: you work out hard, but have no idea if you're actually balanced. Are you hitting legs enough? Is your form getting worse? Let me show you GymIntel."

**Demo Points:**

1. **Upload & Analysis**
   - Show video upload
   - Display detected exercises with timestamps and rep counts
   - Highlight form issue detection with specific timestamp

2. **Dashboard & Insights**
   - Show muscle heatmap revealing training imbalance
   - Display week-over-week trends
   - Show recommendation: "Users like you enjoy face pulls"

3. **Voice Coach**
   - Ask: "Hey coach, what should I focus on this week?"
   - Coach responds with personalized advice based on actual workout data
   - Ask: "How's my squat depth been?"
   - Coach pulls specific form data and responds

**Closing:**
> "GymIntel turns your phone into a personal trainer. It watches your form, tracks your balance, and coaches you through voice—all from videos you're probably already taking."
