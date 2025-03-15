SOURCE=$(realpath ./src)
VERSION=0.1.0
FILES = \
	PartDesignExample_${VERSION}.step \
	PartDesignExample_Drawing_${VERSION}.pdf \


.PHONY: all


all: ${FILES}

.PHONY: clean

clean:
	-rm ${FILES}

# Basic top level options can name the main object and use this generic rule to export them
%_${VERSION}.step: ${SOURCE}/%.FCStd
	-freecad_export export-object --path $@ --fname $< --object $*


# Drawing must be named %{FILENAME}-Drawing to use
%_Drawing_${VERSION}.pdf: ${SOURCE}/%.FCStd
	-freecad_export export-object --path $@ --fname $< --object $*-Drawing


