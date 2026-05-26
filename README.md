# GST Appeal Research & Drafting Toolkit

A comprehensive toolkit for researching and drafting Goods and Services Tax (GST) appeals in India, designed to work with AI agent platforms like Codex, Claude Code, Gemini CLI, and OpenCode CLI.

## 📋 Overview

This repository provides:
1. **GST Appeal Drafting Skill** - An AI agent skill for drafting/reviewing/researching Indian GST appeals
2. **Case Law Research CLI** (`caselaws-cli`) - A CLI tool for researching GST case laws and judicial precedents
3. **Integration Guide** - Instructions for connecting with NotebookLM knowledge bank via `notebooklm-py`

## 🤖 AI Agent Platform Installation

### For Codex (OpenCode)
```bash
# Clone this repository
git clone https://github.com/Wadhawnaiya/gst-appeal.git
cd gst-appeal

# The skill is automatically available at .agents/skills/gst-appeal-drafting/
# No additional installation needed - Codex will discover it automatically
```

### For Claude Code
```bash
# Clone this repository
git clone https://github.com/Wadhawnaiya/gst-appeal.git
cd gst-appeal

# Install the skill for Claude Code
# The skill will be available at .agents/skills/gst-appeal-drafting/
```

### For Gemini CLI
```bash
# Clone this repository
git clone https://github.com/Wadhawnaiya/gst-appeal.git
cd gst-appeal

# Activate the skill in Gemini CLI
# The skill content is available at .agents/skills/gst-appeal-drafting/SKILL.md
```

### For OpenCode CLI
```bash
# Clone this repository
git clone https://github.com/Wadhawnaiya/gst-appeal.git
cd gst-appeal

# The skill is available in .agents/skills/gst-appeal-drafting/
# OpenCode will automatically discover and load it
```

## 🔧 Installing caselaws-cli

The caselaws-cli tool is included in this repository under the `caselaws-cli/` directory.

### Method 1: Using the bundled virtual environment (Recommended)
```bash
# From the repository root
cd caselaws-cli

# Use the bundled CLI directly
./.venv/bin/caselaws-cli --help

# Or use the module form
./.venv/bin/python -m cli_anything.caselaws.main --help
```

### Method 2: Install in your environment
```bash
# From the caselaws-cli directory
cd caselaws-cli

# Install in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt
```

### Method 3: Expose in PATH (for current shell)
```bash
export PATH="$HOME/.local/bin:/full/path/to/gst-appeal/caselaws-cli/.venv/bin:$PATH"

# Now you can use caselaws-cli directly
caselaws-cli --help
```

## 📚 Installing notebooklm-py

The `notebooklm-py` package is required for NotebookLM knowledge bank integration. It's available from this GitHub repository:

**GitHub Repository:** https://github.com/teng-lin/notebooklm-py

### Installation
```bash
# Install from GitHub
pip install git+https://github.com/teng-lin/notebooklm-py.git

# Or clone and install manually
git clone https://github.com/teng-lin/notebooklm-py.git
cd notebooklm-py
pip install -e .
```

### Authentication
After installation, you need to authenticate with your Google account:
```bash
notebooklm login
```

This will open a browser window for you to sign in with your Google account.

## 🚀 Quick Start Guide

### 1. Basic Case Law Search
```bash
# Search for GST cases
caselaws-cli search "Input Tax Credit GSTR-2A mismatch section 16(4)"

# Get JSON output for AI agent integration
caselaws-cli search "Section 50 interest on gross tax" --json

# Get full text of a result by index
caselaws-cli get 1 --json
```

### 2. Using with NotebookLM Knowledge Bank
```bash
# Set your NotebookLM notebook ID (get this from your NotebookLM URL)
export NOTEBOOKLM_NOTEBOOK="your-notebook-id-here"

# Or persist it in caselaws-cli config
caselaws-cli config set notebooklm_notebook_id "your-notebook-id-here"

# Search using the notebooklm provider
caselaws-cli search "GST section 107 appeal limitation" --provider notebooklm --json
```

### 3. Using with AI Agents
Once installed, you can use natural language with your AI agent:

**Codex/OpenCode Example:**
```
Use gst-appeal-drafting. Draft APL-01 grounds from this GST order demanding tax under section 74 without considering reply evidence.
```

**Claude Code/Gemini CLI Example:**
```
@gst-appeal-drafting Research GST natural justice non-speaking order under section 74 using my GST appeal drafting skill.
```

## 📁 Repository Structure

```
gst-appeal/
├── .agents/skills/gst-appeal-drafting/     # GST appeal drafting skill for AI agents
│   ├── SKILL.md                            # Skill definition
│   ├── scripts/                            # Utility scripts
│   │   ├── check_environment.py            # Environment checker
│   │   ├── install_dependencies.py         # Dependency installer
│   │   └── gst_appeal_research.py          # Research packet generator
│   └── references/                         # Reference materials
├── caselaws-cli/                           # GST case law research CLI
│   ├── cli_anything/caselaws/              # Main CLI source
│   │   ├── main.py                         # CLI entrypoint
│   │   └── providers/                      # Data providers (search, kanoon, cbic, notebooklm)
│   ├── README.md                           # CLI-specific documentation
│   └── SKILL.md                            # CLI skill definition for AI agents
├── demo/                                   # Demo files
│   ├── first-run.sh                        # Demo script
│   ├── first-run-facts.md                  # Sample facts
│   └── output/                             # Generated outputs
├── GST_APPEAL_SETUP_AND_FIRST_RUN_GUIDE.md # Detailed setup guide
└── README.md                               # This file
```

## 🛠️ Utility Scripts

Several utility scripts are provided in `.agents/skills/gst-appeal-drafting/scripts/`:

1. **check_environment.py** - Verifies all required tools are installed
   ```bash
   python3 .agents/skills/gst-appeal-drafting/scripts/check_environment.py --json
   ```

2. **install_dependencies.py** - Installs missing dependencies
   ```bash
   # Install all dependencies
   python3 .agents/skills/gst-appeal-drafting/scripts/install_dependencies.py --only all
   
   # Install specific components
   python3 .agents/skills/gst-appeal-drafting/scripts/install_dependencies.py --only caselaws
   python3 .agents/skills/gst-appeal-drafting/scripts/install_dependencies.py --only notebooklm
   ```

3. **gst_appeal_research.py** - Generates comprehensive research packets
   ```bash
   python3 .agents/skills/gst-appeal-drafting/scripts/gst_appeal_research.py \
     --issue "your legal issue" \
     --facts-file your-facts.md \
     --jurisdiction "State/High Court" \
     --output research-packet.md
   ```

## 📖 Documentation

- **[Detailed Setup Guide](GST_APPEAL_SETUP_AND_FIRST_RUN_GUIDE.md)** - Step-by-step installation and usage instructions
- **[caselaws-cli README](caselaws-cli/README.md)** - Specific documentation for the case law research CLI
- **[GST Appeal Drafting Skill](.agents/skills/gst-appeal-drafting/SKILL.md)** - Skill definition for AI agents

## 💡 Usage Tips

1. **For Best Results**: Use the NotebookLM knowledge bank provider to get source-backed legal propositions before searching for case laws.

2. **JSON Output**: Use `--json` flag with caselaws-cli for easy parsing by AI agents and scripts.

3. **Citation Verification**: Always fetch full text using `caselaws-cli get <index>` before citing any case in legal documents.

4. **Configuration**: Use `caselaws-cli config` to set persistent preferences like default search limits and NotebookLM notebook ID.

## 🐛 Troubleshooting

### Common Issues

**NotebookLM Authentication Missing**
```bash
# Run this to authenticate
notebooklm login
# Then verify
notebooklm auth check --test --json
```

**caselaws-cli Not Found**
```bash
# Use the full path or add to PATH
~/gst-appeal/caselaws-cli/.venv/bin/caselaws-cli --help
# Or
export PATH="$HOME/.local/bin:/full/path/to/gst-appeal/caselaws-cli/.venv/bin:$PATH"
```

**Skill Not Loading in AI Agent**
Ensure you're running the AI agent from within the repository directory or that the agent can access the `.agents/skills/gst-appeal-drafting/` directory.

### Getting Help

For caselaws-cli specific help:
```bash
caselaws-cli --help
caselaws-cli search --help
caselaws-cli get --help
```

For notebooklm-py help:
```bash
notebooklm --help
notebooklm login --help
notebooklm ask --help
```

## 📜 License

This toolkit is provided for research and drafting assistance only. Always verify current law, full judgment text, limitation, pre-deposit requirements, and portal procedures before filing any legal documents. Consult with a qualified chartered accountant or advocate for legal advice.

## 🙏 Acknowledgments

- Built using the rich Python library for premium terminal visuals
- Integrates with various GST law data sources including Indian Kanoon and CBIC portals
- Designed for seamless integration with AI agent platforms

---

**Ready to research and draft GST appeals?** Clone this repository, install the components, and start using natural language with your preferred AI agent platform!