#!/bin/bash
# Compile all LaTeX documents in the directory to PDF

echo "Compiling all LaTeX documents..."

# Check if pdflatex is available
if ! command -v pdflatex &> /dev/null; then
    echo "pdflatex not found. Please install a LaTeX distribution (e.g., MacTeX, TeX Live)"
    echo "For macOS: brew install --cask mactex"
    echo "For Ubuntu: sudo apt-get install texlive-full"
    exit 1
fi

# Create figures directory if it doesn't exist
mkdir -p figures

# Counter for compiled documents
compiled_count=0

# Find all .tex files and compile them
for texfile in *.tex; do
    if [ -f "$texfile" ]; then
        echo "----------------------------------------"
        echo "Compiling: $texfile"
        filename="${texfile%.tex}"
        
        # Compile the document (run twice for references)
        pdflatex -interaction=nonstopmode "$texfile" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            pdflatex -interaction=nonstopmode "$texfile" > /dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo "✓ Successfully compiled: $filename.pdf"
                compiled_count=$((compiled_count + 1))
            else
                echo "✗ Error during second pass for: $texfile"
            fi
        else
            echo "✗ Error during first pass for: $texfile"
        fi
    fi
done

# Clean up auxiliary files
echo "----------------------------------------"
echo "Cleaning up auxiliary files..."
rm -f *.aux *.log *.out *.toc *.lof *.lot *.fls *.fdb_latexmk *.synctex.gz

echo "----------------------------------------"
echo "Done! Compiled $compiled_count LaTeX documents."
echo ""
echo "PDF files generated:"
ls -la *.pdf 2>/dev/null || echo "No PDF files found."