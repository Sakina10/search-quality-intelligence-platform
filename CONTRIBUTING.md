# Contributing to Google Search Quality Intelligence Platform

Thank you for your interest in contributing to the Google Search Quality Intelligence Platform! We welcome contributions from the community to help make this platform more robust, scalable, and secure.

---

## 1. Code of Conduct
By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to the project maintainers.

---

## 2. Getting Started
To get started as a contributor:

1. **Fork the Repository**: Create a fork of this repository under your own GitHub account.
2. **Clone Locally**: Clone your fork onto your development machine:
   ```bash
   git clone https://github.com/your-username/google-search-quality-platform.git
   cd google-search-quality-platform
   ```
3. **Verify the Environment**: Run the bootstrap verifier to validate directories and packages:
   ```bash
   make bootstrap
   ```

---

## 3. Development Workflow

We use a standard branching workflow for all contributions:

1. **Create a Branch**: Create a feature or bugfix branch off `main`:
   ```bash
   git checkout -b feat/your-feature-name
   # Or for bug fixes:
   git checkout -b fix/bug-description
   ```
2. **Write Code**: Follow our coding guidelines (strict PEP8 compliance, type hints, docstrings).
3. **Format & Lint**: Check code styling and types prior to committing:
   ```bash
   make lint
   make type-check
   ```
4. **Run Tests**: Ensure all automated Pytest validation checks pass:
   ```bash
   pytest
   ```
5. **Commit Changes**: Use Conventional Commits formatting:
   ```bash
   git commit -m "feat(module): add centralized metrics aggregation logic"
   ```

---

## 4. Submitting a Pull Request
When your branch is ready for review:

1. **Push Changes**: Push your branch to your GitHub fork:
   ```bash
   git push origin feat/your-feature-name
   ```
2. **Open a PR**: Open a Pull Request from your branch to the upstream `main` branch.
3. **Fill Out the Template**: Standardize your description using the Pull Request template provided.
4. **Address Feedback**: Work with project maintainers to address any code review comments.
