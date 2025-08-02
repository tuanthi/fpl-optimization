#!/bin/bash
# Compile the FPL optimization paper to PDF

echo "Compiling LaTeX document..."

# Check if pdflatex is available
if ! command -v pdflatex &> /dev/null; then
    echo "pdflatex not found. Please install a LaTeX distribution (e.g., MacTeX, TeX Live)"
    echo "For macOS: brew install --cask mactex"
    echo "For Ubuntu: sudo apt-get install texlive-full"
    exit 1
fi

# Compile the document (run twice for references)
pdflatex -interaction=nonstopmode fpl_optimization_paper.tex
pdflatex -interaction=nonstopmode fpl_optimization_paper.tex

# Clean up auxiliary files
rm -f *.aux *.log *.out *.toc

echo "Done! Paper compiled to fpl_optimization_paper.pdf"