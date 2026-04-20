# Contributing to Executive Narrative & Sentiment Factor Extractor

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🎯 Ways to Contribute

### 1. 🐛 Report Bugs

Found a bug? Please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Relevant logs or error messages

### 2. 💡 Suggest Features

Have an idea? Open an issue with:
- Use case description
- Proposed solution
- Alternative approaches considered
- Impact on existing functionality

### 3. 📝 Improve Documentation

- Fix typos or clarify explanations
- Add examples or tutorials
- Translate documentation
- Update outdated information

### 4. 🔧 Submit Code

See the development workflow below.

---

## 🚀 Development Workflow

### 1. Fork & Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/quant-NPL.git
cd quant-NPL

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/quant-NPL.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# Install pre-commit hooks
pre-commit install
```

### 3. Create a Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

**Branch naming conventions**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 4. Make Changes

**Code Style**:
- Follow PEP 8
- Use type hints
- Add docstrings (Google style)
- Keep functions focused and small

**Example**:
```python
def extract_sentiment(text: str, model: str = "claude-sonnet-4-6") -> Dict[str, float]:
    """
    Extract sentiment factors from text.

    Args:
        text: Input text to analyze
        model: LLM model name

    Returns:
        Dictionary with factor scores

    Raises:
        ValueError: If text is empty
    """
    pass
```

### 5. Write Tests

```bash
# Run tests
pytest tests/ -v

# Check coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_pipeline.py::TestParagraphChunker -v
```

**Test requirements**:
- All new features must have tests
- Maintain >80% code coverage
- Tests should be fast (<1s each)

### 6. Format & Lint

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

### 7. Commit Changes

```bash
git add .
git commit -m "feat: add new sentiment factor"
```

**Commit message format**:
```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Test additions
- `chore`: Maintenance

**Example**:
```
feat: add forward guidance factor

- Implement ForwardGuidanceFactor class
- Add prompt template for guidance extraction
- Update factor analysis to include new factor

Closes #123
```

### 8. Push & Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

**PR checklist**:
- [ ] Tests pass locally
- [ ] Code is formatted (black, isort)
- [ ] Type hints added
- [ ] Docstrings added
- [ ] Tests added for new features
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

---

## 📋 Code Review Process

1. **Automated Checks**: CI runs tests, linting, type checking
2. **Maintainer Review**: Code quality, design, documentation
3. **Feedback**: Address comments and suggestions
4. **Approval**: Maintainer approves and merges

**Review criteria**:
- Code quality and readability
- Test coverage
- Documentation completeness
- Performance impact
- Backward compatibility

---

## 🎨 Style Guide

### Python Code

```python
# Good
def calculate_factor_score(
    text: str,
    factor_type: Literal["confidence", "risk", "shift"]
) -> float:
    """Calculate sentiment factor score."""
    pass

# Bad
def calc(t, f):
    pass
```

### Documentation

```python
# Good
"""
Extract sentiment factors from earnings call transcripts.

This module provides a pipeline for extracting quantitative sentiment
factors using LLM-based analysis. It supports multiple providers and
includes retry mechanisms for robustness.

Example:
    >>> pipeline = SentimentExtractorPipeline(provider="openai")
    >>> df = pipeline.run(limit=10)
"""

# Bad
"""Sentiment stuff."""
```

### Tests

```python
# Good
def test_confidence_score_high_conviction():
    """Test that high conviction language produces high confidence scores."""
    text = "We are confident that revenue will grow 20% next quarter."
    score = extract_confidence(text)
    assert score >= 7, "High conviction should yield score >= 7"

# Bad
def test1():
    assert extract_confidence("test") > 5
```

---

## 🏗️ Architecture Guidelines

### Adding a New Data Source

1. Create subclass of `BaseTranscriptSource`
2. Implement `fetch()` method
3. Add to source factory in `transcript_scraper.py`
4. Write tests
5. Update documentation

**Example**:
```python
class SeekingAlphaSource(BaseTranscriptSource):
    """SeekingAlpha transcript source."""

    def fetch(self, ticker: str) -> Optional[TranscriptData]:
        """Fetch transcript from SeekingAlpha."""
        # Implementation
        pass
```

### Adding a New Factor

1. Update `SYSTEM_PROMPT` in `sentiment_extractor.py`
2. Add factor to `SentimentFactors` dataclass
3. Update validation logic
4. Add to analysis pipeline
5. Update dashboard
6. Write tests
7. Document factor definition

### Adding a New Visualization

1. Add function to `factor_analysis.py`
2. Call in `run_full_analysis()`
3. Add to dashboard if interactive
4. Update documentation

---

## 🧪 Testing Guidelines

### Unit Tests

Test individual functions in isolation:

```python
def test_text_cleaning():
    """Test that non-ASCII characters are removed."""
    cleaner = StandardTextCleaner()
    text = "Hello 世界"
    cleaned = cleaner.clean(text)
    assert "世界" not in cleaned
```

### Integration Tests

Test component interactions:

```python
def test_full_pipeline():
    """Test complete pipeline from raw text to factors."""
    # Create test transcript
    # Run pipeline
    # Verify output format and values
```

### Fixtures

Use pytest fixtures for common test data:

```python
@pytest.fixture
def sample_transcript():
    return TranscriptData(
        ticker="TEST",
        year=2024,
        quarter="Q1",
        content="Sample earnings call text..."
    )
```

---

## 📚 Documentation Guidelines

### Code Documentation

- All public functions/classes need docstrings
- Use Google-style docstrings
- Include examples for complex functions
- Document exceptions

### User Documentation

- Keep README.md up to date
- Add tutorials for new features
- Include screenshots for UI changes
- Provide migration guides for breaking changes

---

## 🐛 Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Use Breakpoints

```python
import pdb; pdb.set_trace()
```

### Check Test Output

```bash
pytest tests/ -v -s  # -s shows print statements
```

---

## 🤝 Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, showcase
- **Pull Requests**: Code contributions

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Focus on what's best for the project

---

## 📝 Release Process

1. Update version in `__init__.py`
2. Update CHANGELOG.md
3. Create release branch
4. Run full test suite
5. Create GitHub release
6. Tag version
7. Announce in discussions

---

## ❓ Questions?

- Check [FAQ](docs/faq.md)
- Search [existing issues](https://github.com/yourusername/quant-NPL/issues)
- Ask in [Discussions](https://github.com/yourusername/quant-NPL/discussions)

---

Thank you for contributing! 🎉
