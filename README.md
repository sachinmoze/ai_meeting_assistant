# 🎙️ AI Meeting Assistant

AI Meeting Assistant is a Windows desktop application that captures system audio, transcribes speech in real-time, summarizes meetings, and organizes meeting notes. It works with any audio source including Zoom, Microsoft Teams, Google Meet, and Skype.
![image](https://github.com/user-attachments/assets/ee2120ea-96be-4dcb-bdce-ffb42f251a78)

![image](https://github.com/user-attachments/assets/f518068a-a1a4-4e7c-84d3-a32648f536b3)


## ✨ Features

### 🔹 Core Features
- **System Audio Capture**: Records the audio played on your computer in real-time
- **Real-time Transcription**: Converts speech into text using OpenAI's Whisper AI
- **AI Summarization**: Uses GPT-4 to generate concise meeting summaries and action points
- **Meeting Organization**: Saves and organizes transcripts & summaries
- **Live Captions Overlay**: Shows subtitles on screen for accessibility
- **Analytics Dashboard**: Tracks meeting stats and action item completion

### 🔹 Additional Features
- **Export & Sharing**: Save notes in PDF, Markdown, or Word formats
- **Multi-Language Support**: Automatically processes meetings in different languages
- **Offline Mode**: Optional local Whisper model for transcription without internet
- **Action Item Tracking**: Extracts and tracks tasks from meetings
- **Meeting Analytics**: Visualizes meeting frequency and action item status

## 🚀 Getting Started

### Prerequisites
- Windows 10 or 11
- Python 3.9 or higher
- OpenAI API key (for Whisper and GPT-4)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/cloudtribe-ai/ai-meeting-assistant.git
cd ai-meeting-assistant
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Set up your OpenAI API key:
   - Launch the application
   - Go to Settings > AI Models
   - Enter your OpenAI API key

### Running the Application

Run the application with:
```bash
python main.py
```

## 📝 Usage

### Recording a Meeting
1. Click "Start Recording" to begin capturing audio
2. The application will transcribe speech in real-time
3. Click "Stop & Process" when the meeting is finished
4. The app will automatically generate a summary and extract action items

### Managing Meetings
- Previous meetings are shown in the left panel
- Click on a meeting to view its summary and transcript
- Use the dashboard to analyze meeting statistics

### Exporting
You can export meetings to:
- Markdown (.md)
- PDF (.pdf)
- Word document (.docx)

## ⚙️ Configuration

### Audio Settings
- Choose input device (system audio or microphone)
- Configure audio quality and processing options

### AI Models
- Choose between OpenAI API or local Whisper model
- Select GPT model for summarization

### Storage Settings
- Configure database location
- Set default export formats and locations

## 📊 Dashboard

The dashboard provides analytics on your meetings:
- Meeting frequency over time
- Action item completion rates
- Average meeting duration
- Top assignees for action items

## 🛠️ Tech Stack

- **Backend**: Python with SQLite database
- **Frontend**: PyQt5 for Windows GUI
- **AI Models**: OpenAI Whisper API, GPT-4, faster-whisper for local processing
- **Audio Processing**: PyAudio and Sounddevice

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- [OpenAI](https://openai.com/) for Whisper and GPT-4 APIs
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) for local transcription
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework

---

Made with ❤️ by Sachin M
