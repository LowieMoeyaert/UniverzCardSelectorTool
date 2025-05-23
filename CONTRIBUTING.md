# Internal Development Guidelines for Credit Card Selector Tool

This document provides guidelines and instructions for Univerz employees and authorized contractors working on the Credit Card Selector Tool.

## Proprietary Notice

This software is proprietary to Univerz. It is not open source and is not available for public distribution. All rights are reserved by Univerz.

## Getting Started

1. **Request access** to the internal repository from the IT department
2. **Set up the development environment** by following the installation instructions in the README.md
3. **Create a new branch** in the internal repository for your feature or bug fix

## Development Workflow

1. Make your changes in your feature branch
2. Add or update tests as necessary
3. Run tests to ensure they pass
4. Update documentation to reflect your changes
5. Commit your changes with clear, descriptive commit messages
6. Submit your changes for internal code review

## Code Style Guidelines

- Follow PEP 8 style guidelines for Python code
- Use meaningful variable and function names
- Add docstrings to all functions, classes, and modules
- Keep functions focused on a single responsibility
- Comment complex code sections

## Documentation

- Update the README.md if you change functionality
- Add docstrings to all new functions and classes
- Update component-specific documentation as needed
- If you add a new component, create appropriate documentation for it

## Testing

- Write tests for all new functionality
- Ensure all tests pass before submitting for review
- Test your changes with different inputs and edge cases

## Adding a New Bank Scraper

If you're adding support for a new bank:

1. Create a new directory under `Data_Handler/Scrape_Data/Scrapers` with the bank name
2. Implement the following files:
   - BenefitExtractor.py
   - CreditCardScraper.py
   - RequirementsExtractor.py
   - Scraper_[BankName].py
3. Ensure the scraper saves data to a `credit_cards.csv` file in the bank's directory
4. Update documentation to include the new bank

## Adding a New API Endpoint

If you're adding a new API endpoint:

1. Add the endpoint to `Credit_Card_Selector/Server/Server.py`
2. Add appropriate error handling
3. Update the Swagger documentation in `swagger_utils.py`
4. Add tests for the new endpoint
5. Update the Server component documentation

## Code Review Process

1. Ensure your code follows the style guidelines
2. Update documentation as necessary
3. Include a clear description of the changes in your submission
4. Be responsive to feedback and be willing to make changes if requested

## Confidentiality

- Do not share code, documentation, or any project-related information outside of Univerz
- Do not discuss project details in public forums or social media
- Report any security concerns immediately to the IT security team

## Questions?

If you have any questions or need help, please contact the project manager or the IT department.

This document is confidential and proprietary to Univerz.
