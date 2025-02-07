# Artist Manager Agent

An AI-powered agent for managing music artists, handling everything from scheduling and team management to release planning and health tracking.

## Features

- **Team Management**
  - Collaborator profiles and roles
  - Payment tracking and management
  - Project coordination
  - Team availability tracking
  - Professional communication templates

- **Release Planning**
  - Gamified release process
  - Task tracking and milestones
  - Progress visualization
  - Reward system
  - Automated reminders

- **Music Distribution**
  - Multi-platform distribution
  - Release packaging
  - AI mastering integration
  - Analytics tracking
  - Metadata management

- **Health Tracking**
  - Daily wellness checks
  - Personalized feedback
  - Vocal health monitoring
  - Stress management
  - Smart reminders

- **Social Media Management**
  - Multi-platform posting
  - Content scheduling
  - Campaign management
  - Analytics tracking
  - Content idea generation

- **Schedule Management**
  - Calendar integration
  - Conflict detection
  - Smart scheduling
  - iCalendar export
  - Availability management

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/artist-manager-agent.git
cd artist-manager-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token

# Distribution Service
DISTRIBUTION_API_KEY=your_api_key

# AI Mastering Service
MASTERING_API_KEY=your_api_key

# Social Media APIs
INSTAGRAM_API_KEY=your_api_key
TWITTER_API_KEY=your_api_key
FACEBOOK_API_KEY=your_api_key
TIKTOK_API_KEY=your_api_key
YOUTUBE_API_KEY=your_api_key
LINKEDIN_API_KEY=your_api_key

# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

5. Initialize the database:
```bash
python scripts/init_db.py
```

6. Start the bot:
```bash
python main.py
```

## Usage

### Telegram Bot Commands

- `/start` - Begin interaction with the agent
- `/help` - Show available commands
- `/tasks` - View and manage tasks
- `/schedule` - Manage calendar
- `/health` - Track health metrics
- `/team` - Manage team members
- `/release` - Plan and track releases
- `/social` - Manage social media
- `/master` - Submit tracks for AI mastering
- `/distribute` - Manage music distribution

### API Integration

The agent integrates with various services through their APIs:

- Music Distribution Services
- AI Mastering Services
- Social Media Platforms
- Calendar Services
- Payment Processing
- Team Communication

## Development

### Project Structure

```
artist-manager-agent/
├── artist_manager_agent/
│   ├── __init__.py
│   ├── bot_commands.py
│   ├── health_tracking.py
│   ├── music_services.py
│   ├── release_planning.py
│   ├── schedule.py
│   ├── social_media.py
│   └── team_management.py
├── tests/
│   └── ...
├── scripts/
│   └── init_db.py
├── .env
├── main.py
├── requirements.txt
└── README.md
```

### Running Tests

```bash
pytest tests/
```

### Code Style

The project uses:
- Black for code formatting
- isort for import sorting
- mypy for type checking

Run formatting:
```bash
black .
isort .
```

Check types:
```bash
mypy .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers. 