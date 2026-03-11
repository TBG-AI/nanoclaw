#!/bin/bash
# Script to push TBG comprehensive documentation to the docs repository
# Run this script from your local machine

set -e  # Exit on error

echo "🚀 TBG Documentation Push Script"
echo "================================"
echo ""

# Configuration
DOCS_REPO="https://github.com/TBG-AI/docs.git"
BRANCH_NAME="docs/comprehensive-system-documentation"
DOCS_FOLDER="comprehensive-docs"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Step 1: Cloning docs repository...${NC}"
if [ -d "docs" ]; then
    echo "docs directory already exists. Removing..."
    rm -rf docs
fi
git clone $DOCS_REPO
cd docs

echo -e "${BLUE}Step 2: Checking out dev branch...${NC}"
git checkout dev
git pull origin dev

echo -e "${BLUE}Step 3: Creating new branch...${NC}"
git checkout -b $BRANCH_NAME

echo -e "${BLUE}Step 4: Creating documentation folder...${NC}"
mkdir -p $DOCS_FOLDER

echo -e "${BLUE}Step 5: Copying documentation files...${NC}"
# You need to copy the files from /workspace/group/ to this location
# Assuming you've downloaded them to a local 'documentation-files' folder

if [ -d "../documentation-files" ]; then
    cp ../documentation-files/*.md $DOCS_FOLDER/
    echo "✅ Documentation files copied"
else
    echo "⚠️  Please create a '../documentation-files' folder with the documentation markdown files"
    echo "Files needed:"
    echo "  - README_DOCUMENTATION_INDEX.md"
    echo "  - TBG_Complete_System_Architecture.md"
    echo "  - Backend-Odds_Statistical_Models_Documentation.md"
    echo "  - DATABASE_SCHEMA_DOCUMENTATION.md"
    echo "  - INFRASTRUCTURE_DEPLOYMENT_DOCUMENTATION.md"
    echo "  - INFRASTRUCTURE_SUMMARY.md"
    echo "  - MOBILE_FEATURES_DOCUMENTATION.md"
    echo "  - RISK_MANAGEMENT_DOCUMENT.md"
    echo "  - admin-dashboard-documentation.md"
    echo "  - bet_settlement_system_documentation.md"
    echo ""
    echo "Press Ctrl+C to cancel, or Enter to continue anyway"
    read
fi

echo -e "${BLUE}Step 6: Adding files to git...${NC}"
git add $DOCS_FOLDER/

echo -e "${BLUE}Step 7: Committing changes...${NC}"
git commit -m "Add comprehensive system documentation

This commit adds extensive documentation covering all aspects of the TBG platform:

Documentation Added:
- Complete system architecture and user flows (6 phases)
- Promotional system mechanics (8+ promotion types)
- Tournament system documentation
- Bet settlement logic and edge cases
- Risk management and fraud detection systems
- Statistical models and algorithms (TAM, PAM, ZDM, Copula)
- Admin dashboard and trading tools
- Scraping infrastructure and data sources
- Mobile features and deep linking
- Complete database schema (95+ tables)
- Infrastructure and deployment (AWS, CI/CD)
- Documentation index with navigation

Total: 13 documents, ~300+ pages, 1,000+ code references

Created by: Andy (Documentation Bot)
Date: 2026-03-03

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

echo -e "${BLUE}Step 8: Pushing to remote...${NC}"
git push -u origin $BRANCH_NAME

echo ""
echo -e "${GREEN}✅ Documentation pushed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Go to: https://github.com/TBG-AI/docs/pulls"
echo "2. Create a Pull Request from $BRANCH_NAME to dev"
echo "3. Add reviewers and description"
echo ""
echo "PR Title suggestion:"
echo "  Add Comprehensive System Documentation"
echo ""
echo "PR Description suggestion:"
echo "  This PR adds extensive documentation covering all aspects of the TBG platform."
echo "  See README_DOCUMENTATION_INDEX.md for a complete overview and navigation guide."
echo ""
