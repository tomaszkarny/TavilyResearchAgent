# TavilyResearchAgent (Wavily Integration)

A powerful research agent that leverages Tavily's API for web search combined with GPT-4o-mini for content processing, summarization, and blog post generation. This tool automates the research process by gathering relevant articles, extracting key insights, and generating comprehensive blog posts from search results.

## Features

- **Advanced Search**: Uses Tavily API for high-quality search results with optional Cohere re-ranking
- **Article Processing**: Analyzes articles with GPT-4o-mini to extract main points and insights
- **Content Summarization**: Automatically generates summaries of multiple articles
- **Blog Post Generation**: Creates well-structured blog posts based on processed articles
- **Parallel Processing**: Efficiently processes multiple articles concurrently
- **MongoDB Integration**: Stores session data, search results, and processed content
- **Command-line Interface**: Easy-to-use CLI for research queries

## Installation

### Prerequisites

- Python 3.9+
- MongoDB Atlas account (for database operations)
- Tavily API key
- OpenAI API key (for GPT-4o-mini access)

### Setup

1. **Clone the repository**

```bash
git clone https://github.com/tomaszkarny/TavilyResearchAgent.git
cd TavilyResearchAgent
```

2. **Set up environment**

Using pip:
```bash
pip install -r requirements.txt
```

Or using conda:
```bash
conda env create -f environment.yml
conda activate tavily-research
```

3. **Configure environment variables**

Create a `.env` file in the project root with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
MONGODB_URI=your_mongodb_connection_string
```

## Usage

### Basic Research Query

```bash
python -m src.research.cli
```
Follow the prompts to enter your research query and wait for the results.

### Generate Blog Post from Session

```bash
python src/research/generate_blog_post_workflow.py --session_id YOUR_SESSION_ID
```

### Display Research Results

```bash
python show_results.py --session_id YOUR_SESSION_ID
```

## Project Structure

```
├── src/
│   ├── research/
│   │   ├── database/           # MongoDB operations and models
│   │   ├── data_processor.py   # GPT-4o-mini article processing
│   │   ├── tavily_client.py    # Tavily API integration
│   │   ├── tavily_hybrid.py    # Enhanced search with Cohere
│   │   ├── manager.py          # Research flow orchestration
│   │   ├── cli.py              # Command-line interface
│   │   └── generate_blog_post_workflow.py  # Blog post generation
├── tests/                     # Test suite
├── requirements.txt           # Python dependencies
└── environment.yml            # Conda environment
```

## Key Workflows

### Research Process

1. User inputs a research query via CLI
2. The Manager initiates the research process using Tavily's API
3. Search results are deduplicated and stored in MongoDB
4. Articles are processed in parallel using GPT-4o-mini
5. Processed results are saved to the database

### Blog Post Generation

1. Retrieve processed articles for a specific session
2. Build context by extracting key insights from articles
3. Generate a blog post using GPT-4o-mini with proper content chunking for large inputs
4. Save and display the generated blog post

## Testing

Run the test suite with:

```bash
python -m pytest tests/
```

Specific test categories include:
- Database operations: `tests/test_db_saving.py`
- Article processing: `tests/test_mini_processor.py`
- Parallel processing: `tests/test_parallel_processing.py`
- Tavily integration: `tests/test_tavily.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Tavily API](https://tavily.com/) for providing the search capabilities
- OpenAI for GPT-4o-mini model access