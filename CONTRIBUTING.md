# 🤝 Contributing Guide

We welcome contributions to the HA Text AI project! This document will help you contribute to the project's development.

## 🌟 How to Contribute

### 1. Preparation

1. Fork the Repository
   - Go to the repository page on GitHub
   - Click the "Fork" button in the top right corner

2. Clone Your Fork
   ```bash
   git clone https://github.com/YOUR_USERNAME/ha-text-ai.git
   cd ha-text-ai
   ```

3. Set Up Remote Repositories
   ```bash
   git remote add upstream https://github.com/smkrv/ha-text-ai.git
   ```

### 2. Creating a Development Branch

```bash
# Update the main branch
git checkout main
git pull upstream main

# Create a new branch for your feature
git checkout -b feature/short-description-of-changes
```

### 3. Development

- Follow the project's coding standards
- Write clean and understandable code
- Add comments when necessary
- Create unit tests for new functionality

### 4. Committing Changes

```bash
# Add modified files
git add .

# Create a meaningful commit
git commit -m "Feat: Add [short feature description]"
```

### 5. Commit Message Style

Use the following prefixes:
- `Feat:` - new feature
- `Fix:` - bug fixes
- `Docs:` - documentation updates
- `Style:` - formatting changes
- `Refactor:` - code refactoring
- `Test:` - adding tests
- `Chore:` - project maintenance

### 6. Pushing Changes

```bash
# Push changes to your fork
git push origin feature/short-description-of-changes
```

### 7. Creating a Pull Request (PR)

1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Select the base branch `main` of the original repository
4. Fill out the PR description:
   - Brief description of changes
   - Motivation for changes
   - Screenshots (if applicable)

### 8. Review Process

- Project maintainers will review your PR
- There may be comments and requests for changes
- After approval, the PR will be merged

## 🛠 Code Requirements

- Follow PEP 8 for Python
- Write clear and self-documenting code
- Add type hints
- Cover code with tests

## 🐛 Found a Bug?

1. Check existing Issues
2. Create a new Issue with:
   - Bug description
   - Reproduction steps
   - Home Assistant version
   - Plugin version

## 📜 License

By contributing to the project, you agree to the [project's license](LICENSE).

## 🤔 Questions?

If you have any questions, create an Issue or contact the project maintainers.

**Thank you for your contribution!** 🎉
