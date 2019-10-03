# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = ESSArch
SOURCEDIR     = .
BUILDDIR      = _build
LANGUAGE      = en

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: clean help Makefile

clean:
	-rm -rf $(BUILDDIR)/*

html: Makefile
	@$(SPHINXBUILD) -b $@ -n "$(SOURCEDIR)" "$(BUILDDIR)/$(LANGUAGE)/html" -D language=$(LANGUAGE) $(SPHINXOPTS) $(O)

pdf: Makefile
	@$(SPHINXBUILD) -M latexpdf "$(SOURCEDIR)" "$(BUILDDIR)/$(LANGUAGE)" -D language=$(LANGUAGE) $(SPHINXOPTS) $(O)

gettext: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -b $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
