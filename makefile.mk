SOURCE=$(realpath ./)
VERSION=X.X.X


# Basic top level options can name the main object and use this generic rule to export them
%_${VERSION}.step: ${SOURCE}/%.FCStd
	-freecad_export export-object --path $@ --fname $< --object $*


# Drawing must be named %{FILENAME}-Drawing to use
%_Drawing_${VERSION}.pdf: ${SOURCE}/%.FCStd
	-freecad_export export-object --path $@ --fname $< --object $*-Drawing

