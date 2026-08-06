PAPER = main

.PHONY: all clean

all: $(PAPER).pdf

$(PAPER).pdf: $(PAPER).tex references.bib tables/leaderboard.tex
	pdflatex -interaction=nonstopmode $(PAPER).tex
	bibtex $(PAPER)
	pdflatex -interaction=nonstopmode $(PAPER).tex
	pdflatex -interaction=nonstopmode $(PAPER).tex

clean:
	rm -f $(PAPER).aux $(PAPER).log $(PAPER).bbl $(PAPER).blg \
	      $(PAPER).out $(PAPER).toc $(PAPER).fls $(PAPER).fdb_latexmk \
	      $(PAPER).synctex.gz

distclean: clean
	rm -f $(PAPER).pdf
